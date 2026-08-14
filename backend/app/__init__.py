# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

from pathlib import Path

from flask import Flask

from .config import Config
from .extensions import db, migrate
from .software_identity import get_software_identity


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models
    from .auth_routes import auth_api
    from .frontend_routes import frontend_web
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
    app.register_blueprint(
        frontend_web,
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

        identity = get_software_identity(
            version=version,
        )

        return {
            "application": identity["product_name"],
            "product_name": identity["product_name"],
            "product_mark": identity["product_mark"],
            "software_id": identity["software_id"],
            "owner": identity["owner"],
            "copyright": identity["copyright"],
            "status": "ok",
            "version": identity["version"],
        }

    return app
