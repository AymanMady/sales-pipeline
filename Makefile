# Project shortcuts. Run `make` to list them.
# PYTHON is overridable so CI can use its own interpreter: make test PYTHON=python
PYTHON ?= ./.venv/bin/python

.DEFAULT_GOAL := help
.PHONY: help install up down data run report test lint psql reset clean

help:  ## Show this help
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-9s\033[0m %s\n", $$1, $$2}'

install:  ## Create the virtualenv and install dependencies
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	@test -f .env || cp .env.example .env

up:  ## Start PostgreSQL and Adminer
	docker compose up -d
	@echo "PostgreSQL on localhost:5433  |  Adminer on http://localhost:8081"

down:  ## Stop the containers, keeping the data
	docker compose down

data:  ## Generate the raw CSV files
	$(PYTHON) scripts/generate_raw_data.py

run:  ## Run the full ETL pipeline
	$(PYTHON) -m src.pipeline

report:  ## Rebuild the report from the database only
	$(PYTHON) -m src.pipeline --report-only

test:  ## Run the unit tests
	$(PYTHON) -m pytest

lint:  ## Check style and imports
	$(PYTHON) -m ruff check .

psql:  ## Open a SQL console
	docker compose exec postgres psql -U sales -d sales

reset:  ## Wipe the database and start over
	docker compose down -v
	docker compose up -d

clean:  ## Delete generated files
	rm -rf data/raw/*.csv reports/*.csv reports/*.md reports/*.png
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache
