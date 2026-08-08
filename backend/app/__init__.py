from flask import Flask


def create_app():
    app = Flask(__name__)

    @app.get("/api/health")
    def health():
        return {
            "application": "Paradigm Training Manager",
            "status": "ok",
            "version": "0.1.0",
        }

    return app
