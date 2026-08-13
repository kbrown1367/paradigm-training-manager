"""v0.4.3 add user onboarding completion

Revision ID: 7a2d9f4c81e6
Revises: 2f4c8a7d91b3
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa


revision = "7a2d9f4c81e6"
down_revision = "2f4c8a7d91b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "onboarding_completed_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

    # Existing agency administrators are established users.
    # Mark them complete so this first-login tutorial applies
    # only to administrators created after v0.4.3.
    op.execute(
        sa.text(
            """
            UPDATE users
            SET onboarding_completed_at = CURRENT_TIMESTAMP
            WHERE role = 'AGENCY_ADMIN'
              AND onboarding_completed_at IS NULL
            """
        )
    )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column(
            "onboarding_completed_at"
        )
