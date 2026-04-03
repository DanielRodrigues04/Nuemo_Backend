"""add financial identity fields

Revision ID: 0002_financial_fields
Revises: 0001_create_initial_tables
Create Date: 2026-04-02 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_financial_fields"
down_revision = "0001_create_initial_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("empresas", sa.Column("documento", sa.String(length=18), nullable=True))
    op.add_column("empresas", sa.Column("contato", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_empresas_documento", "empresas", ["documento"])

    op.add_column("atendimentos", sa.Column("cpf_paciente", sa.String(length=14), nullable=True))
    op.create_index("ix_atendimentos_cpf_paciente", "atendimentos", ["cpf_paciente"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_atendimentos_cpf_paciente", table_name="atendimentos")
    op.drop_column("atendimentos", "cpf_paciente")

    op.drop_constraint("uq_empresas_documento", "empresas", type_="unique")
    op.drop_column("empresas", "contato")
    op.drop_column("empresas", "documento")
