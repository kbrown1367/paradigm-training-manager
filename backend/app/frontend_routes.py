# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    send_from_directory,
)


frontend_web = Blueprint(
    "frontend_web",
    __name__,
)


def get_frontend_dist():
    return Path(
        current_app.config[
            "FRONTEND_DIST_DIR"
        ]
    )


def frontend_unavailable():
    return jsonify(
        {
            "error": (
                "PTM frontend build "
                "is not available."
            )
        }
    ), 503


@frontend_web.get("/")
@frontend_web.get("/<path:path>")
def serve_frontend(path=""):
    # Never allow the SPA fallback to convert an
    # unknown API endpoint into a successful HTML
    # response.
    if (
        path == "api"
        or path.startswith("api/")
    ):
        abort(404)

    dist = get_frontend_dist()

    if not dist.is_dir():
        return frontend_unavailable()

    index_file = dist / "index.html"

    if not index_file.is_file():
        return frontend_unavailable()

    if path:
        requested_file = dist / path

        if requested_file.is_file():
            return send_from_directory(
                dist,
                path,
            )

    # React currently performs its own path handling
    # from window.location.pathname. Direct requests
    # and browser refreshes therefore receive the
    # compiled SPA entry point.
    return send_from_directory(
        dist,
        "index.html",
    )
