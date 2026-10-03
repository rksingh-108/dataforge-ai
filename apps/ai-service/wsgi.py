"""WSGI entrypoint: `gunicorn 'wsgi:app'`."""
from ai_service.app import create_app

app = create_app()
