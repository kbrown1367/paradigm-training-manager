"""add users auth foundation

Revision ID: f6b1a2c3d4e5
Revises: cee5a16f19c2
Create Date: 2026-08-11

"""

from alembic import op
import sqlalchemy as sa


revision = "f6b1a2c3d4e5"
down_revision = "cee5a16f19c2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "agency_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "first_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "last_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "last_login_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["agency_id"],
            ["agencies.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_index(
        op.f("ix_users_agency_id"),
        "users",
        ["agency_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_users_email"),
        "users",
        ["email"],
        unique=True,
    )

    op.create_index(
        op.f("ix_users_role"),
        "users",
        ["role"],
        unique=False,
    )

    op.create_index(
        op.f("ix_users_status"),
        "users",
        ["status"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_users_status"),
        table_name="users",
    )

    op.drop_index(
        op.f("ix_users_role"),
        table_name="users",
    )

    op.drop_index(
        op.f("ix_users_email"),
        table_name="users",
    )

    op.drop_index(
        op.f("ix_users_agency_id"),
        table_name="users",
    )

    op.drop_table("users")
