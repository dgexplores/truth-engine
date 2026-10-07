PY=python3
.PHONY: test eval check run

test:
	$(PY) -m pytest tests/ -q

eval:
	PYTHONPATH=. $(PY) eval/run_eval.py

check: test eval
	@echo "gate green"

run:
	PYTHONPATH=. $(PY) -m uvicorn app.main:app --reload --port 8001
