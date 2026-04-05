"""add attendance billing competence

Revision ID: 0003_attendance_billing_competence
Revises: 0002_financial_fields
Create Date: 2026-04-05 00:00:00.000000
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "0003_attendance_billing_competence"
down_revision = "0002_financial_fields"
branch_labels = None
depends_on = None


def month_start(value: datetime) -> date:
    normalized = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return normalized.date().replace(day=1)


def next_month_start(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def upgrade() -> None:
    op.add_column("atendimentos", sa.Column("competencia_cobranca", sa.Date(), nullable=True))
    op.add_column("atendimentos", sa.Column("data_pagamento", sa.DateTime(timezone=True), nullable=True))

    bind = op.get_bind()
    attendances = sa.table(
        "atendimentos",
        sa.column("id", sa.Integer()),
        sa.column("data", sa.DateTime(timezone=True)),
        sa.column("forma_pagamento", sa.String(length=20)),
        sa.column("status", sa.String(length=20)),
    )

    rows = bind.execute(
        sa.select(attendances.c.id, attendances.c.data, attendances.c.forma_pagamento, attendances.c.status)
    ).mappings()

    for row in rows:
        attendance_date = row["data"]
        if isinstance(attendance_date, str):
            attendance_date = datetime.fromisoformat(attendance_date.replace("Z", "+00:00"))

        current_month = month_start(attendance_date)
        competence = next_month_start(current_month) if row["forma_pagamento"] == "faturado" else current_month
        payment_date = attendance_date if row["status"] == "pago" else None

        bind.execute(
            sa.text(
                """
                UPDATE atendimentos
                SET competencia_cobranca = :competencia_cobranca,
                    data_pagamento = :data_pagamento
                WHERE id = :attendance_id
                """
            ),
            {
                "attendance_id": row["id"],
                "competencia_cobranca": competence,
                "data_pagamento": payment_date,
            },
        )

    op.alter_column("atendimentos", "competencia_cobranca", nullable=False)
    op.create_index("ix_atendimentos_competencia_cobranca", "atendimentos", ["competencia_cobranca"], unique=False)
    op.create_index("ix_atendimentos_data_pagamento", "atendimentos", ["data_pagamento"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_atendimentos_data_pagamento", table_name="atendimentos")
    op.drop_index("ix_atendimentos_competencia_cobranca", table_name="atendimentos")
    op.drop_column("atendimentos", "data_pagamento")
    op.drop_column("atendimentos", "competencia_cobranca")
