"""v0.5.8 expand audit event activity

Revision ID: b7f2d4e6a801
Revises: ac26f9e613fc
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa


revision = "b7f2d4e6a801"
down_revision = "ac26f9e613fc"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "audit_events",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "object_type",
                sa.String(length=50),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "object_id",
                sa.String(length=100),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "result",
                sa.String(length=30),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "details",
                sa.JSON(),
                nullable=True,
            )
        )

        batch_op.create_index(
            batch_op.f(
                "ix_audit_events_object_type"
            ),
            ["object_type"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_audit_events_object_id"
            ),
            ["object_id"],
            unique=False,
        )

        batch_op.create_index(
            batch_op.f(
                "ix_audit_events_result"
            ),
            ["result"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table(
        "audit_events",
        schema=None,
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f(
                "ix_audit_events_result"
            )
        )
        batch_op.drop_index(
            batch_op.f(
                "ix_audit_events_object_id"
            )
        )
        batch_op.drop_index(
            batch_op.f(
                "ix_audit_events_object_type"
            )
        )

        batch_op.drop_column("details")
        batch_op.drop_column("result")
        batch_op.drop_column("object_id")
        batch_op.drop_column("object_type")
