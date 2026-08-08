import uuid
from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Agency(db.Model):
    __tablename__ = "agencies"

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(200), nullable=False)
    tcole_agency_number = db.Column(db.String(50), nullable=True)
    ori = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    officers = db.relationship(
        "Officer",
        back_populates="agency",
        cascade="save-update, merge",
    )

    import_jobs = db.relationship(
        "ImportJob",
        back_populates="agency",
        cascade="save-update, merge",
    )


class Officer(db.Model):
    __tablename__ = "officers"

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=False,
        index=True,
    )
    tcole_pid = db.Column(db.String(50), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=False)
    employment_status = db.Column(db.String(30), nullable=False, default="active")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    agency = db.relationship("Agency", back_populates="officers")

    __table_args__ = (
        db.UniqueConstraint(
            "agency_id",
            "tcole_pid",
            name="uq_officers_agency_tcole_pid",
        ),
    )


class ImportJob(db.Model):
    __tablename__ = "import_jobs"

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.String(30), nullable=False, default="pending")
    awards_filename = db.Column(db.String(255), nullable=True)
    courses_filename = db.Column(db.String(255), nullable=True)
    officer_count = db.Column(db.Integer, nullable=False, default=0)
    award_count = db.Column(db.Integer, nullable=False, default=0)
    course_count = db.Column(db.Integer, nullable=False, default=0)
    warning_count = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    agency = db.relationship("Agency", back_populates="import_jobs")
