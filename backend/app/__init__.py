from pathlib import Path

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
    from .auth_routes import auth_api
    from .platform_routes import platform_api
    from .routes import api

    app.register_blueprint(
        auth_api,
        url_prefix="/api/auth",
    )
    app.register_blueprint(
        platform_api,
        url_prefix="/api/platform",
    )
    app.register_blueprint(
        api,
        url_prefix="/api",
    )

    @app.get("/api/health")
    def health():
        version_path = Path(
            app.root_path
        ).parent.parent / "VERSION"

        version = (
            version_path.read_text().strip()
            if version_path.exists()
            else "unknown"
        )

        return {
            "application": "Paradigm Training Manager",
            "status": "ok",
            "version": version,
        }

    return app
