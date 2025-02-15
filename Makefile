SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

ifeq ($(origin .RECIPEPREFIX), undefined)
  $(error This Make does not support .RECIPEPREFIX. Please use GNU Make 4.0 or later)
endif
.RECIPEPREFIX = >

PROJECT_NAME = "dravik"

.DEFAULT_GOAL := help
help:
>	@echo Select a target.
.PHONY: help

install:
>	uv sync
.PHONY: install

shell:
>	uv run python
.PHONY: shell

run:
>	uv run -m $(PROJECT_NAME)
.PHONY: run

dev:
>	uv run textual run --dev $(PROJECT_NAME).__main__
.PHONY: dev

console:
>	uv run textual console
.PHONY: console

console-x:
>	uv run textual console -x SYSTEM -x EVENT -x DEBUG -x INFO
.PHONY: console-x


lint:
>	uv run ruff format
>	uv run ruff check --fix
.PHONY: lint

mypy:
>	uv run mypy $(PROJECT_NAME) --strict
.PHONY: mypy

build:
>	uv bulid
.PHONY: build
