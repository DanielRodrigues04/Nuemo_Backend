from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models.attendance import Atendimento
from app.models.company import Empresa
from app.models.exam import Exame
from app.models.enums import FormaPagamento, StatusAtendimento, TipoEmpresa


def seed_companies() -> list[Empresa]:
    return [
        Empresa(
            nome="Metalurgica Horizonte",
            tipo=TipoEmpresa.EMPRESA,
            documento="12345678000190",
            contato="financeiro@horizonte.com.br",
        ),
        Empresa(
            nome="Construtora Alvorada",
            tipo=TipoEmpresa.EMPRESA,
            documento="98765432000155",
            contato="cobranca@alvorada.com.br",
        ),
        Empresa(
            nome="Carlos Pereira",
            tipo=TipoEmpresa.PESSOA_FISICA,
            documento="12345678901",
            contato="(11) 99999-0000",
        ),
    ]


def seed_exams() -> list[Exame]:
    return [
        Exame(nome="ASO Admissional", valor=Decimal("85.00")),
        Exame(nome="Audiometria", valor=Decimal("60.00")),
        Exame(nome="Espirometria", valor=Decimal("72.00")),
        Exame(nome="Acuidade Visual", valor=Decimal("45.00")),
    ]


def seed_attendances(companies: list[Empresa], exams: list[Exame]) -> list[Atendimento]:
    now = datetime.now(timezone.utc)
    return [
        Atendimento(
            data=now - timedelta(days=2),
            nome_paciente="Mariana Costa",
            cpf_paciente="11122233344",
            empresa_id=companies[0].id,
            exame_id=exams[0].id,
            valor=Decimal("85.00"),
            forma_pagamento=FormaPagamento.PIX,
            status=StatusAtendimento.PAGO,
        ),
        Atendimento(
            data=now - timedelta(days=7),
            nome_paciente="Rafael Matos",
            cpf_paciente="22233344455",
            empresa_id=companies[1].id,
            exame_id=exams[1].id,
            valor=Decimal("60.00"),
            forma_pagamento=FormaPagamento.FATURADO,
            status=StatusAtendimento.PENDENTE,
        ),
        Atendimento(
            data=now - timedelta(days=12),
            nome_paciente="Juliana Prado",
            cpf_paciente="33344455566",
            empresa_id=companies[0].id,
            exame_id=exams[2].id,
            valor=Decimal("72.00"),
            forma_pagamento=FormaPagamento.DINHEIRO,
            status=StatusAtendimento.PAGO,
        ),
        Atendimento(
            data=now - timedelta(days=35),
            nome_paciente="Caio Sampaio",
            cpf_paciente="44455566677",
            empresa_id=companies[1].id,
            exame_id=exams[0].id,
            valor=Decimal("85.00"),
            forma_pagamento=FormaPagamento.FATURADO,
            status=StatusAtendimento.PENDENTE,
        ),
        Atendimento(
            data=now - timedelta(days=65),
            nome_paciente="Fernanda Melo",
            cpf_paciente="55566677788",
            empresa_id=companies[2].id,
            exame_id=exams[3].id,
            valor=Decimal("45.00"),
            forma_pagamento=FormaPagamento.PIX,
            status=StatusAtendimento.PAGO,
        ),
    ]


def main() -> None:
    with SessionLocal() as db:
        has_companies = db.scalar(select(Empresa.id).limit(1))
        if has_companies is not None:
            print("Seed skipped: database already has data.")
            return

        companies = seed_companies()
        exams = seed_exams()

        db.add_all(companies)
        db.add_all(exams)
        db.commit()

        companies = db.scalars(select(Empresa).order_by(Empresa.id.asc())).all()
        exams = db.scalars(select(Exame).order_by(Exame.id.asc())).all()
        attendances = seed_attendances(companies, exams)

        db.add_all(attendances)
        db.commit()
        print("Seed completed successfully.")


if __name__ == "__main__":
    main()
