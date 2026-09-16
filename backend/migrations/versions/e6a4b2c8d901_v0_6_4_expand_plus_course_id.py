"""Expand PLUS_COURSE_ID without truncating training history.

Revision ID: e6a4b2c8d901
Revises: d4e5f6a7b8c9
"""

from alembic import op
import sqlalchemy as sa

revision = "e6a4b2c8d901"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "training_records",
        "plus_course_id",
        existing_type=sa.String(length=50),
        type_=sa.String(length=500),
        existing_nullable=True,
    )


def downgrade():
    connection = op.get_bind()
    oversized = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM training_records "
            "WHERE length(plus_course_id) > 50"
        )
    ).scalar_one()

    if oversized:
        raise RuntimeError(
            "Cannot downgrade: existing PLUS_COURSE_ID values "
            "exceed 50 characters. No records were modified."
        )

    op.alter_column(
        "training_records",
        "plus_course_id",
        existing_type=sa.String(length=500),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
