# BTC Analyzer — Chapter 20/22 DevOps & QA helpers

.PHONY: help fmt lint test test-unit test-int ci docker-build compose-up compose-down backup readiness qa-gates qa-report

help:
	@echo "Targets: fmt lint test test-unit test-int ci docker-build compose-up compose-down backup readiness qa-gates qa-report"

fmt:
	python3 -m ruff format src tests || true
	python3 -m black --check src tests 2>/dev/null || python3 -m black src tests 2>/dev/null || true

lint:
	python3 -m ruff check src tests || python3 -m compileall -q src

test:
	python3 -m pytest -q

test-unit:
	python3 -m pytest -q -m unit

test-int:
	python3 -m pytest -q -m "integration or e2e"

ci: lint test qa-gates

docker-build:
	docker build -t btc-analyzer:local .

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down

backup:
	bash deploy/scripts/backup.sh

readiness:
	python3 -c "from src.services.deploy import DeployService; import json; print(json.dumps(DeployService().checklist(), indent=2))"

qa-gates:
	python3 -c "from src.services.qa import QAService; import json; s=QAService().suite(); print(json.dumps(s['gates'], indent=2)); assert s['gates']['can_release']"

qa-report:
	python3 -c "from src.services.qa import QAService; import json; print(json.dumps(QAService().suite()['test_report'], indent=2))"
