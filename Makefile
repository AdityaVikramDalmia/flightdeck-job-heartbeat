PREFIX ?= $(HOME)/.local
.PHONY: test demo install

test:
	@PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v

demo:
	@bash examples/demo.sh

install:
	install -d "$(DESTDIR)$(PREFIX)/bin"
	install -m 0755 bin/job-heartbeat "$(DESTDIR)$(PREFIX)/bin/job-heartbeat"
