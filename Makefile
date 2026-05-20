SECRETS := python3 $(HOME)/secrets/generate_env.py management-hub
COMPOSE := docker compose
UV      := uv

.PHONY: up down restart logs ps env test

up: env
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart: env
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

env:
	$(SECRETS)

test:
	$(UV) run pytest

push:
	git push origin main

monitor:
	gh run watch $$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')

deploy: push monitor
