# Copyright © 2026 Paradigm Strategic Partners, LLC.
# All Rights Reserved.
#
# Paradigm Training Manager™ is proprietary and confidential software.
# Unauthorized copying, modification, distribution, or use is prohibited.
# Software ID: PTM-PSP-2026

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
    email_domain = db.Column(db.String(255), nullable=True)
    email_pattern = db.Column(db.String(50), nullable=True)
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


    users = db.relationship(
        "User",
        back_populates="agency",
        cascade="save-update, merge",
    )

    import_jobs = db.relationship(
        "ImportJob",
        back_populates="agency",
        cascade="save-update, merge",
    )

    officer_assignments = db.relationship(
        "OfficerAssignment",
        back_populates="agency",
        cascade="save-update, merge",
    )

    credential_verifications = db.relationship(
        "OfficerCredentialVerification",
        back_populates="agency",
        cascade="save-update, merge",
    )

    license_tracking_records = db.relationship(
        "OfficerLicenseTracking",
        back_populates="agency",
        cascade="save-update, merge",
    )



class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=True,
        index=True,
    )

    email = db.Column(
        db.String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=True,
    )

    invitation_token_hash = db.Column(
        db.String(64),
        nullable=True,
        unique=True,
        index=True,
    )

    invitation_created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    invitation_expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    first_name = db.Column(
        db.String(100),
        nullable=False,
    )

    last_name = db.Column(
        db.String(100),
        nullable=False,
    )

    role = db.Column(
        db.String(30),
        nullable=False,
        default="AGENCY_ADMIN",
        index=True,
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="active",
        index=True,
    )

    last_login_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    onboarding_completed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    agency = db.relationship(
        "Agency",
        back_populates="users",
    )


class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id = db.Column(
        db.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=True,
        index=True,
    )

    user_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    event_type = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )

    ip_address = db.Column(
        db.String(64),
        nullable=True,
    )

    user_agent = db.Column(
        db.String(500),
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )

    agency = db.relationship(
        "Agency",
    )

    user = db.relationship(
        "User",
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
    suffix = db.Column(db.String(20), nullable=True)
    email_override = db.Column(db.String(255), nullable=True)
    peace_officer_service_start_date = db.Column(
        db.Date,
        nullable=True,
    )
    jailer_service_start_date = db.Column(
        db.Date,
        nullable=True,
    )
    telecommunicator_service_start_date = db.Column(
        db.Date,
        nullable=True,
    )
    verified_military_months = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    verified_education_level = db.Column(
        db.String(30),
        nullable=True,
    )
    verified_college_credit_hours = db.Column(
        db.Integer,
        nullable=True,
    )
    verified_military_training_credit_hours = db.Column(
        db.Integer,
        nullable=True,
    )
    verified_jailer_cultural_diversity_exemption = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )
    employment_status = db.Column(db.String(30), nullable=False, default="active")
    archived_at = db.Column(db.DateTime(timezone=True), nullable=True)
    archived_reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    agency = db.relationship("Agency", back_populates="officers")

    awards = db.relationship(
        "OfficerAward",
        back_populates="officer",
        cascade="save-update, merge",
    )

    training_records = db.relationship(
        "TrainingRecord",
        back_populates="officer",
        cascade="save-update, merge",
    )

    assignments = db.relationship(
        "OfficerAssignment",
        back_populates="officer",
        cascade="save-update, merge",
    )

    credential_verifications = db.relationship(
        "OfficerCredentialVerification",
        back_populates="officer",
        cascade="save-update, merge",
    )

    license_tracking_records = db.relationship(
        "OfficerLicenseTracking",
        back_populates="officer",
        cascade="save-update, merge",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "agency_id",
            "tcole_pid",
            name="uq_officers_agency_tcole_pid",
        ),
    )


class OfficerLicenseTracking(db.Model):
    __tablename__ = "officer_license_tracking"

    id = db.Column(
        db.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=False,
        index=True,
    )
    officer_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("officers.id"),
        nullable=False,
        index=True,
    )
    license_type = db.Column(
        db.String(30),
        nullable=False,
        index=True,
    )
    tracking_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
    )
    last_disabled_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )
    last_disabled_by = db.Column(
        db.String(255),
        nullable=True,
    )
    last_disabled_reason = db.Column(
        db.Text,
        nullable=True,
    )
    updated_by = db.Column(
        db.String(255),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    agency = db.relationship(
        "Agency",
        back_populates="license_tracking_records",
    )

    officer = db.relationship(
        "Officer",
        back_populates="license_tracking_records",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "agency_id",
            "officer_id",
            "license_type",
            name="uq_officer_license_tracking",
        ),
    )


class OfficerAssignment(db.Model):
    __tablename__ = "officer_assignments"

    id = db.Column(
        db.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=False,
        index=True,
    )
    officer_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("officers.id"),
        nullable=False,
        index=True,
    )
    assignment_type = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )
    effective_date = db.Column(
        db.Date,
        nullable=False,
    )
    end_date = db.Column(
        db.Date,
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    agency = db.relationship(
        "Agency",
        back_populates="officer_assignments",
    )

    officer = db.relationship(
        "Officer",
        back_populates="assignments",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "agency_id",
            "officer_id",
            "assignment_type",
            "effective_date",
            name="uq_officer_assignment",
        ),
    )


class OfficerCredentialVerification(db.Model):
    __tablename__ = "officer_credential_verifications"

    id = db.Column(
        db.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=False,
        index=True,
    )
    officer_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("officers.id"),
        nullable=False,
        index=True,
    )
    credential_type = db.Column(
        db.String(100),
        nullable=False,
        index=True,
    )
    status = db.Column(
        db.String(30),
        nullable=False,
        default="VERIFIED",
    )
    effective_date = db.Column(
        db.Date,
        nullable=True,
    )
    verified_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )
    verified_by = db.Column(
        db.String(255),
        nullable=True,
    )
    reference = db.Column(
        db.String(500),
        nullable=True,
    )
    notes = db.Column(
        db.Text,
        nullable=True,
    )
    revoked_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    agency = db.relationship(
        "Agency",
        back_populates="credential_verifications",
    )

    officer = db.relationship(
        "Officer",
        back_populates="credential_verifications",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "agency_id",
            "officer_id",
            "credential_type",
            "verified_at",
            name="uq_officer_credential_verification",
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
    cycle_filename = db.Column(db.String(255), nullable=True)
    licensee_search_filename = db.Column(
        db.String(255),
        nullable=True,
    )
    officer_count = db.Column(db.Integer, nullable=False, default=0)
    award_rows_processed = db.Column(db.Integer, nullable=False, default=0)
    course_rows_processed = db.Column(db.Integer, nullable=False, default=0)
    cycle_rows_processed = db.Column(db.Integer, nullable=False, default=0)
    licensee_search_rows_processed = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    peace_officer_license_rows = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    jailer_license_rows = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    jailer_service_dates_populated = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    jailer_service_dates_updated = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    jailer_service_dates_unchanged = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    service_dates_populated = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    service_dates_updated = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    service_dates_unchanged = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    unmatched_license_rows = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    training_records_with_hours = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )
    award_count = db.Column(db.Integer, nullable=False, default=0)
    course_count = db.Column(db.Integer, nullable=False, default=0)
    warning_count = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    skipped_award_count = db.Column(db.Integer, nullable=False, default=0)
    skipped_course_count = db.Column(db.Integer, nullable=False, default=0)
    failure_reason = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    agency = db.relationship("Agency", back_populates="import_jobs")


class OfficerAward(db.Model):
    __tablename__ = "officer_awards"

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=False,
        index=True,
    )
    officer_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("officers.id"),
        nullable=False,
        index=True,
    )
    award_type = db.Column(db.String(50), nullable=False)
    award_name = db.Column(db.String(255), nullable=False)
    award_date = db.Column(db.Date, nullable=False)
    source = db.Column(db.String(50), nullable=False, default="TCOLE")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    officer = db.relationship("Officer", back_populates="awards")

    __table_args__ = (
        db.UniqueConstraint(
            "agency_id",
            "officer_id",
            "award_type",
            "award_name",
            "award_date",
            name="uq_officer_award",
        ),
    )


class TrainingRecord(db.Model):
    __tablename__ = "training_records"

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=False,
        index=True,
    )
    officer_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("officers.id"),
        nullable=False,
        index=True,
    )
    course_number = db.Column(db.String(50), nullable=False)
    course_title = db.Column(db.String(500), nullable=False)
    course_date = db.Column(db.Date, nullable=False, index=True)
    plus_course_id = db.Column(db.String(50), nullable=True)
    credited_hours = db.Column(db.Numeric(8, 2), nullable=True)
    hours_source = db.Column(db.String(50), nullable=True)
    source = db.Column(db.String(50), nullable=False, default="TCOLE")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    officer = db.relationship("Officer", back_populates="training_records")

    training_credits = db.relationship(
        "TrainingCredit",
        back_populates="training_record",
        cascade="save-update, merge",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "agency_id",
            "officer_id",
            "course_number",
            "course_title",
            "course_date",
            "plus_course_id",
            name="uq_training_record",
        ),
    )



class TrainingCredit(db.Model):
    __tablename__ = "training_credits"

    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agency_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("agencies.id"),
        nullable=False,
        index=True,
    )
    officer_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("officers.id"),
        nullable=False,
        index=True,
    )
    training_record_id = db.Column(
        db.Uuid(as_uuid=True),
        db.ForeignKey("training_records.id"),
        nullable=False,
        index=True,
    )
    course_number = db.Column(db.String(50), nullable=False)
    course_date = db.Column(db.Date, nullable=False)
    credited_hours = db.Column(db.Numeric(8, 2), nullable=False)
    role_snapshot = db.Column(db.String(255), nullable=True)
    reported_total_text = db.Column(db.String(255), nullable=True)
    source = db.Column(
        db.String(50),
        nullable=False,
        default="TCOLE_CYCLE_REPORT",
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
    )

    training_record = db.relationship(
        "TrainingRecord",
        back_populates="training_credits",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "agency_id",
            "training_record_id",
            "course_number",
            "course_date",
            "credited_hours",
            "role_snapshot",
            name="uq_training_credit",
        ),
    )
