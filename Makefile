
lint:
	python3 -m ruff check .

lint-ci:
	python3 -m ruff check . --select E9,F63,F7,F82

test:
	PYTHONPATH=src python3 -m pytest -q

gate:
	WF_PREFER_FULL=1 bash scripts/gate_all.sh || true
