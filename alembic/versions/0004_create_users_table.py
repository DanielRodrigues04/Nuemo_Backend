"""create users table

Revision ID: 0004_create_users_table
Revises: 0003_billing_competence
Create Date: 2026-04-05 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_create_users_table"
down_revision = "0003_billing_competence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_usuarios_id", "usuarios", ["id"], unique=False)
    op.create_index("ix_usuarios_username", "usuarios", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_usuarios_username", table_name="usuarios")
    op.drop_index("ix_usuarios_id", table_name="usuarios")
    op.drop_table("usuarios")
