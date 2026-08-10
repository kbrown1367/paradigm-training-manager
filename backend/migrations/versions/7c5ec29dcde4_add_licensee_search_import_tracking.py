"""add licensee search import tracking

Revision ID: 7c5ec29dcde4
Revises: 0eab4d39ee73
Create Date: 2026-08-09 19:15:10.468176
"""

from alembic import op
import sqlalchemy as sa


revision = "7c5ec29dcde4"
down_revision = "0eab4d39ee73"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "import_jobs",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "licensee_search_filename",
                sa.String(length=255),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "licensee_search_rows_processed",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "peace_officer_license_rows",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "service_dates_populated",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "service_dates_updated",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "service_dates_unchanged",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "unmatched_license_rows",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    # The defaults above exist only to backfill
    # pre-existing ImportJob rows during migration.
    # New rows use the SQLAlchemy model defaults.
    with op.batch_alter_table(
        "import_jobs",
        schema=None,
    ) as batch_op:
        for column_name in [
            "licensee_search_rows_processed",
            "peace_officer_license_rows",
            "service_dates_populated",
            "service_dates_updated",
            "service_dates_unchanged",
            "unmatched_license_rows",
        ]:
            batch_op.alter_column(
                column_name,
                server_default=None,
            )


def downgrade():
    with op.batch_alter_table(
        "import_jobs",
        schema=None,
    ) as batch_op:
        batch_op.drop_column(
            "unmatched_license_rows"
        )
        batch_op.drop_column(
            "service_dates_unchanged"
        )
        batch_op.drop_column(
            "service_dates_updated"
        )
        batch_op.drop_column(
            "service_dates_populated"
        )
        batch_op.drop_column(
            "peace_officer_license_rows"
        )
        batch_op.drop_column(
            "licensee_search_rows_processed"
        )
        batch_op.drop_column(
            "licensee_search_filename"
        )
