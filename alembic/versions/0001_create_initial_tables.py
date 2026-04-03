"""create initial tables

Revision ID: 0001_create_initial_tables
Revises:
Create Date: 2026-03-31 22:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_create_initial_tables"
down_revision = None
branch_labels = None
depends_on = None


company_type = sa.Enum("empresa", "pessoa_fisica", name="tipoempresa", native_enum=False)
payment_type = sa.Enum("dinheiro", "pix", "faturado", name="formapagamento", native_enum=False)
status_type = sa.Enum("pago", "pendente", name="statusatendimento", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "empresas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("tipo", company_type, nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome"),
    )
    op.create_table(
        "exames",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome"),
    )
    op.create_table(
        "atendimentos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("data", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("nome_paciente", sa.String(length=255), nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("exame_id", sa.Integer(), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("forma_pagamento", payment_type, nullable=False),
        sa.Column("status", status_type, nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["exame_id"], ["exames.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_atendimentos_data", "atendimentos", ["data"], unique=False)
    op.create_index("ix_atendimentos_status", "atendimentos", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_atendimentos_status", table_name="atendimentos")
    op.drop_index("ix_atendimentos_data", table_name="atendimentos")
    op.drop_table("atendimentos")
    op.drop_table("exames")
    op.drop_table("empresas")
