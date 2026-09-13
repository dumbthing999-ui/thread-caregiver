.PHONY: check test ui-check run

# One command for judges to reproduce the local evidence.
check: test ui-check

test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'

ui-check:
	node --check app/ui.js
	node tests/test_ui_flow.js

run:
	python3 run_app.py --port 8000
