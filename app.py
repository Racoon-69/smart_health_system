"""WSGI entry point.

Local development: ``flask --app app run --debug``
Production: ``gunicorn --bind 0.0.0.0:8000 'app:app'``
"""

import os

from healthcare import create_app

app = create_app(os.getenv("FLASK_ENV", "development"))

from healthcare.extensions import socketio

if __name__ == "__main__":
    # The development server is intentionally restricted to local use.
    socketio.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=app.config["DEBUG"])
