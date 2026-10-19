# ===================================== Testes para verificar as operações de lancamentos =================================
import sqlite3
from datetime import date

import pytest

from app.database import database
from app.database.lancamento_database import (
    salvar_pagamento,
    salvar_adicional,
)
from app.models.registros import Pagamento, Adicional


@pytest.fixture
def banco_temporario(tmp_path, monkeypatch):
    """Prepara um banco isolado para cada teste."""
    monkeypatch.setattr(
        database,
        "DB_PATH",
        tmp_path / "teste.db",
    )

    database.criar_tabelas()

    with database.conectar() as conexao:
        conexao.execute(
            "INSERT INTO hospedes (id, nome) VALUES (?, ?)",
            ("H001", "Hóspede de Teste"),
        )

        conexao.execute(
            """
            INSERT INTO quartos (numero, capacidade, diaria, status)
            VALUES (?, ?, ?, ?)
            """,
            ("101", 2, 150.0, "disponivel"),
        )

        conexao.execute(
            """
            INSERT INTO reservas (
                id, hospede_id, quarto_numero, data_reserva,
                data_entrada, data_saida, qtd_hospedes, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "R001",
                "H001",
                "101",
                "2026-10-19",
                "2026-10-20",
                "2026-10-22",
                2,
                "Confirmada",
            ),
        )

    return database


def test_salvar_pagamento(banco_temporario):
    pagamento = Pagamento(
        id="P001",
        valor=200.0,
        data=date(2026, 10, 20),
        metodo="Pix",
    )

    salvar_pagamento(pagamento, "R001")

    with banco_temporario.conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM pagamentos WHERE id = ?",
            ("P001",),
        ).fetchone()

    assert registro is not None
    assert registro["reserva_id"] == "R001"
    assert registro["valor"] == pytest.approx(200.0)
    assert registro["data_pagamento"] == "2026-10-20"
    assert registro["metodo"] == "Pix"


def test_salvar_adicional(banco_temporario):
    adicional = Adicional(
        id="A001",
        descricao="Serviço de lavanderia",
        valor=35.0,
        data=date(2026, 10, 21),
    )

    salvar_adicional(adicional, "R001")

    with banco_temporario.conectar() as conexao:
        registro = conexao.execute(
            "SELECT * FROM adicionais WHERE id = ?",
            ("A001",),
        ).fetchone()

    assert registro is not None
    assert registro["reserva_id"] == "R001"
    assert registro["descricao"] == "Serviço de lavanderia"
    assert registro["valor"] == pytest.approx(35.0)
    assert registro["data_lancamento"] == "2026-10-21"


def test_pagamento_de_reserva_inexistente_e_rejeitado(
    banco_temporario,
):
    pagamento = Pagamento(
        id="P002",
        valor=100.0,
        data=date(2026, 10, 20),
        metodo="Cartão",
    )

    with pytest.raises(sqlite3.IntegrityError):
        salvar_pagamento(pagamento, "RESERVA_INEXISTENTE")


def test_adicional_de_reserva_inexistente_e_rejeitado(
    banco_temporario,
):
    adicional = Adicional(
        id="A002",
        descricao="Frigobar",
        valor=20.0,
        data=date(2026, 10, 21),
    )

    with pytest.raises(sqlite3.IntegrityError):
        salvar_adicional(adicional, "RESERVA_INEXISTENTE")
