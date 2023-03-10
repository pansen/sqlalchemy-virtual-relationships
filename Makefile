SHELL := /bin/bash
export PYTHONUNBUFFERED := 1
export SQLALCHEMY_WARN_20 := 1
export POETRY_VIRTUALENVS_IN_PROJECT=true
export PYTHONASYNCIODEBUG=1
# This is required to work around a bug in the Python distribution on Debian & Ubuntu 22.04
# https://github.com/pypa/setuptools/issues/3278#issuecomment-1116343912
export SETUPTOOLS_USE_DISTUTILS=stdlib

PYTHON_GLOBAL := $(shell /usr/bin/which python3)
PG_CONNECTION_PARAMS := --host=localhost --port=5445 --dbname=demo_dev
PSQL := psql -P pager=off $(PG_CONNECTION_PARAMS)

TOP_LEVEL_PACKAGE := pansen

# Put this line after the `uname` detections
POETRY := $(PYTHON_GLOBAL) -m poetry

.DEFAULT_GOAL := dev.build

.PHONY: bootstrap
bootstrap:
	$(PYTHON_GLOBAL) -m pip install --user --upgrade \
		pip==22.3.1 \
		setuptools==65.6.3 \
		wheel==0.37.1 \
		six==1.16.0 \
		poetry==1.2.2

.env:
	cp .env.example .env


# Development

.PHONY: dev.build
dev.build: .env var
	$(POETRY) install

.PHONY: dev.migrate
dev.migrate:
	echo 'create database demo_dev_test;' | make dev.psql
	@make migrate

.PHONY: migrate
migrate:
	echo


.PHONY: test
test:
	LOGGING_FORMAT_JSON=0 \
		.venv/bin/python -m pytest $(TOP_LEVEL_PACKAGE)


.PHONY: dev.psql
dev.psql:
	PGPASSWORD=demo_pass PGUSER=demo_user $(PSQL)

var:
	mkdir -p var

.PHONY: clean
clean: pyc-clean
	rm -rf \
		.env \
		.venv \
		.mypy_cache \
		./*".egg-info"

.PHONY: pyc-clean
pyc-clean:
	@find ./ -type d -name __pycache__ | xargs -P 20 rm -rf
	@find ./ -name '*.pyc'             | xargs -P 20 rm -rf

