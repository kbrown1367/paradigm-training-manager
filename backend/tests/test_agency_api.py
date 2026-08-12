from app import create_app
from app.extensions import db
from app.models import Agency


def test_agency_list_is_returned():
    app = create_app(
        {
            "TESTING": True,
            "AUTHORIZATION_DISABLED": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with app.app_context():
        db.create_all()

        db.session.add(
            Agency(
                name="Port of Galveston Police Department"
            )
        )
        db.session.commit()

    client = app.test_client()

    response = client.get("/api/agencies")

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["name"] == "Port of Galveston Police Department"
    assert data[0]["id"] is not None
