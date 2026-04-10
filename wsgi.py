"""WSGI entry for production (gunicorn, uwsgi, mod_wsgi, etc.)."""
from app import app

application = app
