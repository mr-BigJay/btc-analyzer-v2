# BTC Analyzer — Chapter 20 DevOps helpers

.PHONY: help fmt lint test ci docker-build compose-up compose-down backup readiness

help:
	@echo "Targets: fmt lint test ci docker-build compose-up compose-down backup readiness"

fmt:
	python3 -m ruff format src tests || true
	python3 -m black --check src tests 2>/dev/null || python3 -m black src tests 2>/dev/null || true

lint:
	python3 -m ruff check src tests || python3 -m compileall -q src

test:
	python3 -m pytest -q

ci: lint test

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
