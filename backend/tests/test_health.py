from pathlib import Path

from app import create_app


def test_health():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    client = app.test_client()

    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.get_json()

    assert data["application"] == "Paradigm Training Manager"
    assert data["status"] == "ok"

    expected_version = (
        Path(__file__)
        .resolve()
        .parents[2]
        .joinpath("VERSION")
        .read_text()
        .strip()
    )

    assert data["version"] == expected_version
