"""Entidades de domínio do SRH-WDA."""

from .quartos import Quarto, Simples, Duplo, Luxo
from .pessoas import Pessoa, Hospede, Funcionario
from .rastreios import Rastreabilidade
from .registros import Registro, Reserva, Pagamento, Adicional, Bloqueio

__all__ = [
    "Quarto", "Simples", "Duplo", "Luxo",
    "Pessoa", "Hospede", "Funcionario",
    "Rastreabilidade",
    "Registro", "Reserva", "Pagamento", "Adicional", "Bloqueio",
]
