.PHONY: install dev test lint migrate seed run-prod

install:
	python3 -m venv venv
	venv/bin/pip install -r requirements-dev.txt

dev:
	FLASK_ENV=development venv/bin/flask --app app run --debug

test:
	venv/bin/pytest --cov=healthcare --cov=utils --cov-report=term-missing

lint:
	venv/bin/ruff check app.py healthcare utils tests

migrate:
	venv/bin/flask --app app db upgrade

seed:
	venv/bin/flask --app app seed

run-prod:
	FLASK_ENV=production venv/bin/gunicorn --config deploy/gunicorn.conf.py app:app
