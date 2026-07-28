.PHONY: check test selfcheck compile drift all

all: check

check: selfcheck drift test compile ## run everything CI runs

selfcheck: ## validate plugin integrity
	python3 plugins/praxis/scripts/selfcheck.py

test: ## run the test suite
	python3 -m unittest discover -s tests -v

drift: ## fail if the docs contradict the live config or a reference is stale
	python3 plugins/praxis/scripts/drift.py

compile: ## byte-compile all scripts
	python3 -m compileall -q plugins/praxis/scripts

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n",$$1,$$2}'
