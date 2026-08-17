"""v0.6.0 add retained TCOLE source files

Revision ID: d4e5f6a7b8c9
Revises: b7f2d4e6a801
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "b7f2d4e6a801"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "retained_tcole_files",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "import_job_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "file_type",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "content_type",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.LargeBinary(),
            nullable=False,
        ),
        sa.Column(
            "size_bytes",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agency_id"],
            ["agencies.id"],
        ),
        sa.ForeignKeyConstraint(
            ["import_job_id"],
            ["import_jobs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "agency_id",
            "file_type",
            name=(
                "uq_retained_tcole_file_"
                "agency_type"
            ),
        ),
    )

    op.create_index(
        op.f(
            "ix_retained_tcole_files_agency_id"
        ),
        "retained_tcole_files",
        ["agency_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_retained_tcole_files_import_job_id"
        ),
        "retained_tcole_files",
        ["import_job_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_retained_tcole_files_expires_at"
        ),
        "retained_tcole_files",
        ["expires_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f(
            "ix_retained_tcole_files_expires_at"
        ),
        table_name="retained_tcole_files",
    )
    op.drop_index(
        op.f(
            "ix_retained_tcole_files_import_job_id"
        ),
        table_name="retained_tcole_files",
    )
    op.drop_index(
        op.f(
            "ix_retained_tcole_files_agency_id"
        ),
        table_name="retained_tcole_files",
    )
    op.drop_table("retained_tcole_files")
