"""v0.4.2 add user invitation fields

Revision ID: 2f4c8a7d91b3
Revises: dd8e524c8cff
Create Date: 2026-08-12
"""

from alembic import op
import sqlalchemy as sa


revision = "2f4c8a7d91b3"
down_revision = "dd8e524c8cff"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            nullable=True,
        )

        batch_op.add_column(
            sa.Column(
                "invitation_token_hash",
                sa.String(length=64),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "invitation_created_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "invitation_expires_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

        batch_op.create_index(
            "ix_users_invitation_token_hash",
            ["invitation_token_hash"],
            unique=True,
        )

        batch_op.create_index(
            "ix_users_invitation_expires_at",
            ["invitation_expires_at"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index(
            "ix_users_invitation_expires_at"
        )

        batch_op.drop_index(
            "ix_users_invitation_token_hash"
        )

        batch_op.drop_column(
            "invitation_expires_at"
        )

        batch_op.drop_column(
            "invitation_created_at"
        )

        batch_op.drop_column(
            "invitation_token_hash"
        )

    op.execute(
        sa.text(
            """
            UPDATE users
            SET password_hash = 'invitation-disabled'
            WHERE password_hash IS NULL
            """
        )
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            nullable=False,
        )
