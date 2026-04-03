from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from app.models.enums import FormaPagamento
from app.schemas.attendance import AttendanceRead
from app.schemas.company import CompanyRead


class DashboardReport(BaseModel):
    mes_referencia: str
    total_faturado: float
    total_recebido: float
    total_pendente: float
    quantidade_pendencias: int = 0
    empresas_com_pendencia: int = 0


class DebtorCompanyReport(BaseModel):
    empresa_id: int
    empresa_nome: str
    documento: str | None = None
    contato: str | None = None
    total_pendente: float
    quantidade_atendimentos: int


class MonthListReport(BaseModel):
    meses: list[str]


class MonthlyCloseReport(BaseModel):
    mes: str
    total_faturado: float
    total_recebido: float
    total_pendente: float
    quantidade_pendencias: int = 0
    empresas_devedoras: list[DebtorCompanyReport]


class ExamGroupReport(BaseModel):
    exame_id: int
    exame_nome: str
    quantidade: int
    valor_total: float


class CompanyDetailReport(BaseModel):
    empresa: CompanyRead
    mes_referencia: str | None = None
    periodo_inicio: str | None = None
    periodo_fim: str | None = None
    total_exames: int
    valor_total: float
    valor_recebido: float
    valor_pendente: float
    exames_por_tipo: list[ExamGroupReport]
    atendimentos: list[AttendanceRead]


class CompanySettlementRequest(BaseModel):
    month: str | None = Field(default=None)
    data_inicio: str | None = Field(default=None)
    data_fim: str | None = Field(default=None)
    forma_pagamento: FormaPagamento = FormaPagamento.PIX

    @model_validator(mode="after")
    def validate_period(self) -> "CompanySettlementRequest":
        has_month = bool(self.month)
        has_start = bool(self.data_inicio)
        has_end = bool(self.data_fim)

        if has_month and (has_start or has_end):
            raise ValueError("Use apenas month ou data_inicio/data_fim para definir o periodo.")
        if has_start != has_end:
            raise ValueError("Informe data_inicio e data_fim juntos.")
        if not has_month and not (has_start and has_end):
            raise ValueError("Informe um month ou um intervalo completo para realizar a baixa.")
        if self.forma_pagamento == FormaPagamento.FATURADO:
            raise ValueError("A baixa em lote exige uma forma de recebimento imediata.")
        return self


class CompanySettlementReport(BaseModel):
    empresa: CompanyRead
    mes_referencia: str | None = None
    periodo_inicio: str
    periodo_fim: str
    forma_pagamento: FormaPagamento
    quantidade_atendimentos: int
    total_baixado: float
    atendimentos_ids: list[int]
