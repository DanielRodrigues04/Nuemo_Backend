from enum import Enum


class TipoEmpresa(str, Enum):
    EMPRESA = "empresa"
    PESSOA_FISICA = "pessoa_fisica"


class FormaPagamento(str, Enum):
    DINHEIRO = "dinheiro"
    PIX = "pix"
    FATURADO = "faturado"


class StatusAtendimento(str, Enum):
    PAGO = "pago"
    PENDENTE = "pendente"
