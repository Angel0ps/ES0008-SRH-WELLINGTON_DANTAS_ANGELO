"""Schemas Pydantic usados na validação da API FastAPI."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuartoEntrada(SchemaBase):
    numero: str = Field(min_length=1)
    tipo: Literal["Simples", "Duplo", "Luxo"] = "Simples"
    capacidade: int = Field(gt=0)
    diaria: float = Field(gt=0)
    status: str = "disponivel"
    observacoes: str = ""
    diferencial: str = ""


class HospedeEntrada(SchemaBase):
    id: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    documento: str = Field(min_length=6)
    email: str = Field(min_length=5)
    telefone: str = Field(min_length=10)
    observacoes: str = ""
    acessibilidade: bool = False


class FuncionarioEntrada(SchemaBase):
    id: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    documento: str = Field(min_length=1)
    email: str = Field(min_length=5)
    telefone: str = Field(min_length=10)
    cargo: str = Field(min_length=1)


class ReservaEntrada(SchemaBase):
    id: str = Field(min_length=1)
    quarto: str = Field(min_length=1)
    entrada: date
    saida: date
    hospedes_ids: list[str] = Field(min_length=1)
    qtd_hospedes: int = Field(gt=0)
    origem: Literal["site", "telefone", "balcao"] = "balcao"

    @model_validator(mode="after")
    def validar_periodo_e_hospedes(self):
        if self.saida <= self.entrada:
            raise ValueError("Data de saída deve ser posterior à data de entrada")
        if self.qtd_hospedes != len(self.hospedes_ids):
            raise ValueError("A quantidade de hóspedes deve corresponder aos hóspedes vinculados")
        if len(set(self.hospedes_ids)) != len(self.hospedes_ids):
            raise ValueError("Não é permitido repetir hóspedes na reserva")
        return self


class DataOpcional(SchemaBase):
    hoje: date | None = None
    momento: datetime | None = None



class PagamentoEntrada(SchemaBase):
    id: str = Field(min_length=1)
    forma: str = Field(min_length=1)
    valor: float = Field(gt=0)
    data: date | None = None
    categoria: Literal["hospedagem", "adicional", "outro"] = "hospedagem"


class AdicionalEntrada(SchemaBase):
    id: str = Field(min_length=1)
    descricao: str = Field(min_length=1)
    valor: float = Field(ge=0)


class BloqueioEntrada(SchemaBase):
    id: str = Field(min_length=1)
    quarto: str = Field(min_length=1)
    data_inicio: date
    data_fim: date
    motivo: str = ""
    tipo: str = "manutencao"
    status: str = "ativo"

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.data_fim < self.data_inicio:
            raise ValueError("Data final do bloqueio não pode anteceder a data inicial")
        return self
