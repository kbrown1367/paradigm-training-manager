from flask import Flask

from .config import Config
from .extensions import db, migrate


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models

    @app.get("/api/health")
    def health():
        return {
            "application": "Paradigm Training Manager",
            "status": "ok",
            "version": "0.1.4",
        }

    return app
