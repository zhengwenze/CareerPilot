from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260314_0002"
down_revision = "20260314_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_direction", sa.String(length=120), nullable=True),
        sa.Column("target_city", sa.String(length=80), nullable=True),
        sa.Column("target_role", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        "idx_user_profiles_target_city",
        "user_profiles",
        ["target_city"],
        unique=False,
    )
    op.create_index(
        "idx_user_profiles_target_role",
        "user_profiles",
        ["target_role"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_user_profiles_target_role", table_name="user_profiles")
    op.drop_index("idx_user_profiles_target_city", table_name="user_profiles")
    op.drop_table("user_profiles")
