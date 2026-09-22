import concurrent.futures
import fcntl
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "bin/job-heartbeat"
loader = importlib.machinery.SourceFileLoader("heartbeat", str(BIN))
spec = importlib.util.spec_from_loader(loader.name, loader)
heartbeat = importlib.util.module_from_spec(spec)
loader.exec_module(heartbeat)


class HeartbeatTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="job heartbeat ")
        self.root = Path(self.temporary.name)
        self.store = self.root / "state with spaces"

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, *args, code=0, binary=BIN, extra=()):
        result = subprocess.run([str(binary), "--dir", str(self.store), *extra, *args],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else None

    def start(self, name="build", **kwargs):
        return self.run_cli("start", name, **kwargs)["record"]

    def row_path(self, name="build"):
        return self.store / heartbeat.filename(name)

    def edit(self, **updates):
        path = self.row_path()
        row = json.loads(path.read_text())
        row.update(updates)
        path.write_text(json.dumps(row))

    def test_missing_reads_do_not_create_storage(self):
        self.assertEqual(self.run_cli("read", "build")["status"], "missing")
        self.assertEqual(self.run_cli("list"), [])
        self.assertFalse(self.store.exists())

    def test_lifecycle_and_exact_terminal_idempotence(self):
        row = self.start()
        touched = self.run_cli("touch", "build", row["generation"], "--note", "next step")
        self.assertEqual(touched["status"], "fresh")
        self.assertEqual(touched["record"]["revision"], 2)
        finished = self.run_cli("finish", "build", row["generation"], "--outcome", "failed")
        self.assertEqual(finished["status"], "finished")
        original = self.row_path().read_bytes()
        self.run_cli("finish", "build", row["generation"], "--outcome", "failed", "--note", "ignored retry")
        self.assertEqual(self.row_path().read_bytes(), original)
        self.run_cli("finish", "build", row["generation"], "--outcome", "succeeded", code=3)
        self.run_cli("touch", "build", row["generation"], code=3)
        self.assertEqual(self.row_path().read_bytes(), original)

    def test_restart_compare_and_replace_rejects_stale_writer(self):
        old = self.start()
        self.run_cli("start", "build", code=3)
        new = self.run_cli("start", "build", "--replace", old["generation"])["record"]
        self.assertNotEqual(old["generation"], new["generation"])
        for action in ("touch", "finish"):
            self.run_cli(action, "build", old["generation"], code=3)
        self.run_cli("start", "build", "--replace", old["generation"], code=3)
        self.assertEqual(self.run_cli("read", "build")["record"], new)

    def test_missing_mutations_refuse(self):
        self.run_cli("touch", "build", "a" * 32, code=3)
        self.run_cli("finish", "build", "a" * 32, code=3)
        self.run_cli("start", "build", "--replace", "a" * 32, code=3)
        self.assertFalse(self.row_path().exists())

    def test_concurrent_updates_have_no_lost_revisions(self):
        row = self.start()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.run_cli("touch", "build", row["generation"]), range(16)))
        self.assertEqual(sorted(result["record"]["revision"] for result in results), list(range(2, 18)))
        self.assertEqual(self.run_cli("read", "build")["record"]["revision"], 17)

    def test_concurrent_restarts_have_exactly_one_winner(self):
        old = self.start()
        def restart(_):
            return subprocess.run([str(BIN), "--dir", str(self.store), "start", "build", "--replace", old["generation"]],
                                  capture_output=True, timeout=10).returncode
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            codes = list(pool.map(restart, range(8)))
        self.assertEqual(codes.count(0), 1)
        self.assertEqual(codes.count(3), 7)

    def test_terminal_update_race_cannot_revive(self):
        row = self.start()
        def update(action):
            return subprocess.run([str(BIN), "--dir", str(self.store), action, "build", row["generation"]],
                                  capture_output=True, timeout=10).returncode
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            codes = list(pool.map(update, ["touch"] * 7 + ["finish"]))
        self.assertTrue(all(code in (0, 3) for code in codes))
        self.assertEqual(self.run_cli("read", "build")["status"], "finished")

    def test_ttl_boundary_and_future_clock_are_truthful(self):
        row = self.start()
        row.update(started_at=100, updated_at=110, ttl_seconds=10)
        self.assertEqual(heartbeat.report("build", row, 120)["status"], "fresh")
        self.assertEqual(heartbeat.report("build", row, 120.001)["status"], "late")
        self.assertEqual(heartbeat.report("build", row, 109)["status"], "unknown")
        self.edit(started_at=time.time() - 100, updated_at=time.time() - 90, ttl_seconds=1)
        self.assertEqual(self.run_cli("read", "build")["status"], "late")
        self.run_cli("finish", "build", row["generation"])
        self.edit(updated_at=time.time() - 80)
        self.assertEqual(self.run_cli("read", "build")["status"], "finished")
        self.edit(updated_at=time.time() + 100)
        self.assertEqual(self.run_cli("read", "build", code=1)["status"], "unknown")
        self.run_cli("touch", "build", row["generation"], code=1)
        self.run_cli("start", "build", "--replace", row["generation"], code=1)

    def test_corruption_is_unknown_and_blocks_writes(self):
        row = self.start()
        for content in ('{', '{"a":1,"a":2}', '[]', 'null'):
            self.row_path().write_text(content)
            result = self.run_cli("read", "build", code=1)
            self.assertEqual(result["status"], "unknown")
            self.assertIsNone(result["age_seconds"])
            self.run_cli("start", "build", "--replace", row["generation"], code=1)
            self.assertEqual(self.row_path().read_text(), content)

    def test_invalid_schema_values(self):
        valid = self.start()
        for field, value in (("schema_version", True), ("revision", False), ("revision", 0),
                             ("ttl_seconds", 0), ("ttl_seconds", float("nan")),
                             ("updated_at", float("inf")), ("updated_at", 10 ** 1000),
                             ("started_at", -1), ("job", "another"), ("generation", "../bad"),
                             ("state", "bogus"), ("outcome", "succeeded"), ("note", [])):
            with self.subTest(field=field, value=repr(value)[:50]):
                self.row_path().write_text(json.dumps(dict(valid, **{field: value})))
                self.assertEqual(self.run_cli("read", "build", code=1)["status"], "unknown")

    def test_bad_arguments_and_exact_names(self):
        for name in ("../escape", "/absolute", ".", "..", "two words", "x\ny", "é", "x" * 129):
            self.run_cli("start", name, code=2)
        for value in ("nan", "inf", "-1", "0"):
            self.run_cli("start", "build", "--ttl", value, code=2)
        self.run_cli("start", "build", "--note", "x" * 4097, code=2)
        first = self.start("Build.v1_a-b")
        second = self.start("build.v1_a-b")
        self.assertNotEqual(first["generation"], second["generation"])
        self.assertEqual(len(self.run_cli("list")), 2)

    def test_lock_timeout_and_release(self):
        self.start()
        with (self.store / ".lock").open("r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.run_cli("read", "build", extra=("--lock-timeout", "0.05"), code=75)
        self.assertEqual(self.run_cli("read", "build")["status"], "fresh")

    def test_symlink_and_special_storage_fail_closed(self):
        self.store.symlink_to(self.root, target_is_directory=True)
        self.run_cli("start", "build", code=1)
        self.assertEqual(self.run_cli("read", "build", code=1)["status"], "unknown")
        self.store.unlink()
        row = self.start()
        self.row_path().unlink()
        self.row_path().symlink_to(self.root / "missing")
        self.run_cli("touch", "build", row["generation"], code=1)
        self.row_path().unlink()
        os.mkfifo(self.row_path())
        self.assertEqual(self.run_cli("read", "build", code=1)["status"], "unknown")

    def test_list_preserves_good_rows_and_reports_bad_paths(self):
        self.start("one")
        self.start("two")
        self.row_path("two").write_text("broken")
        (self.store / "alien.json").write_text("{}")
        result = self.run_cli("list", code=1)
        self.assertEqual(len(result), 3)
        self.assertEqual(sum(row["status"] == "fresh" for row in result), 1)
        self.assertEqual(sum(row["status"] == "unknown" for row in result), 2)

    def test_atomic_publish_failure_preserves_previous_record(self):
        row = self.start()
        original = self.row_path().read_bytes()
        with heartbeat.store(self.store, 1, False) as directory:
            with mock.patch.object(heartbeat.os, "replace", side_effect=OSError("injected pre-publication failure")):
                with self.assertRaises(OSError):
                    heartbeat.publish(directory, self.row_path().name, dict(row, revision=2))
        self.assertEqual(self.row_path().read_bytes(), original)
        self.assertEqual(list(self.store.glob(".pending.*")), [])

    def test_real_signal_with_closed_stdin_preserves_state_and_lock_lifetime(self):
        row = self.start()
        original = self.row_path().read_bytes()
        marker = self.root / "ready"
        script = self.root / "interrupt.py"
        script.write_text("import runpy,os,time,sys\n"
                          "m=runpy.run_path(sys.argv[1])\n"
                          "real=os.replace\n"
                          "def pause(*a,**kw):\n"
                          " open(sys.argv[2],'w').close()\n"
                          " time.sleep(30)\n"
                          " return real(*a,**kw)\n"
                          "os.replace=pause\n"
                          "sys.exit(m['main'](sys.argv[3:]))\n")
        child = subprocess.Popen([sys.executable, str(script), str(BIN), str(marker),
                                  "--dir", str(self.store), "touch", "build", row["generation"]],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 preexec_fn=lambda: os.close(0))
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists())
            self.run_cli("touch", "build", row["generation"], extra=("--lock-timeout", "0"), code=75)
            child.send_signal(signal.SIGTERM)
            child.communicate(timeout=5)
            self.assertEqual(child.returncode, 1)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=5)
        self.assertEqual(self.row_path().read_bytes(), original)
        self.assertEqual(list(self.store.glob(".pending.*")), [])
        self.run_cli("touch", "build", row["generation"])

    def test_oversized_and_deeply_nested_json_are_unknown(self):
        self.start()
        for content in (" " * 65537, "[" * 1500 + "0" + "]" * 1500):
            self.row_path().write_text(content)
            self.assertEqual(self.run_cli("read", "build", code=1)["status"], "unknown")

    def test_hardlinked_record_and_lock_are_refused(self):
        self.start()
        record_link = self.root / "record alias"
        os.link(self.row_path(), record_link)
        self.assertEqual(self.run_cli("read", "build", code=1)["status"], "unknown")
        record_link.unlink()
        os.link(self.store / ".lock", self.root / "lock alias")
        self.assertEqual(self.run_cli("read", "build", code=1)["status"], "unknown")

    def test_lock_path_replacement_before_acquisition_is_refused(self):
        self.start()
        lock_path = self.store / ".lock"
        real_flock = heartbeat.fcntl.flock
        def replace_then_lock(descriptor, flags):
            lock_path.unlink()
            lock_path.touch()
            return real_flock(descriptor, flags)
        with mock.patch.object(heartbeat.fcntl, "flock", side_effect=replace_then_lock):
            with self.assertRaisesRegex(ValueError, "lock path changed"):
                with heartbeat.store(self.store, 1, False):
                    self.fail("replaced lock must not enter operation")

    def test_unknown_store_never_looks_missing(self):
        self.store.write_text("not a directory")
        self.assertEqual(self.run_cli("read", "build", code=1)["status"], "unknown")
        self.assertEqual(self.run_cli("list", code=1)[0]["status"], "unknown")

    def test_copied_and_installed_commands_are_independent(self):
        copy = self.root / "standalone heartbeat"
        shutil.copy2(BIN, copy)
        self.run_cli("start", "copied", binary=copy)
        prefix = self.root / "installed tools"
        subprocess.run(["make", "install", "PREFIX=" + str(prefix)], cwd=ROOT, check=True, capture_output=True)
        self.run_cli("start", "installed", binary=prefix / "bin/job-heartbeat")

    def test_closed_stdout_refuses_before_publishing(self):
        result = subprocess.run([str(BIN), "--dir", str(self.store), "start", "build"],
                                preexec_fn=lambda: os.close(1), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.store.exists())

    def test_closed_stderr_does_not_leak_diagnostics_into_json_stdout(self):
        result = subprocess.run([str(BIN), "--dir", str(self.store), "touch", "missing", "a" * 32],
                                preexec_fn=lambda: os.close(2), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, "")

    def test_closed_stdin_does_not_shorten_lock_lifetime(self):
        result = subprocess.run([str(BIN), "--dir", str(self.store), "start", "build"],
                                preexec_fn=lambda: os.close(0), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        row = json.loads(result.stdout)["record"]
        self.assertEqual(self.run_cli("touch", "build", row["generation"])["record"]["revision"], 2)

    def test_broken_receipt_pipe_returns_documented_error_and_releases_lock(self):
        child = subprocess.Popen([str(BIN), "--dir", str(self.store), "start", "build"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        child.stdout.close()
        child.stdout = None
        _, error = child.communicate(timeout=10)
        self.assertEqual(child.returncode, 1, error)
        self.assertNotIn("Traceback", error)
        row = self.run_cli("read", "build")["record"]
        self.assertIsNotNone(row)
        self.run_cli("touch", "build", row["generation"])


if __name__ == "__main__":
    unittest.main()
