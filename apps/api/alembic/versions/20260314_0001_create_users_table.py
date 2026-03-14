from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260314_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("nickname", sa.String(length=80), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="user"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_status", "users", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_users_status", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
