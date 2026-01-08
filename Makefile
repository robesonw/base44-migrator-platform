.PHONY: dev migrate

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

migrate:
	alembic upgrade head
