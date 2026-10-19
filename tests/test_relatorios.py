
import sqlite3
from datetime import date

import pytest

from app.services import relatorios


@pytest.fixture
def banco_teste(monkeypatch):
    """Cria um banco temporário para testar o relatório."""

    conexao = sqlite3.connect(":memory:")
    conexao.row_factory = sqlite3.Row

    conexao.executescript("""
        CREATE TABLE quartos (
            numero TEXT PRIMARY KEY,
            capacidade INTEGER NOT NULL,
            diaria REAL NOT NULL,
            status TEXT NOT NULL
        );

        CREATE TABLE reservas (
            id TEXT PRIMARY KEY,
            hospede_id TEXT NOT NULL,
            quarto_numero TEXT NOT NULL,
            data_reserva TEXT NOT NULL,
            data_entrada TEXT NOT NULL,
            data_saida TEXT NOT NULL,
            qtd_hospedes INTEGER NOT NULL,
            status TEXT NOT NULL
        );
    """)

    monkeypatch.setattr(
        relatorios,
        "conectar",
        lambda: conexao
    )

    yield conexao
    conexao.close()


def cadastrar_quartos(conexao, numeros):
    """Insere quartos para os testes."""

    conexao.executemany(
        """
        INSERT INTO quartos (numero, capacidade, diaria, status)
        VALUES (?, ?, ?, ?)
        """,
        [
            (numero, 2, 150.0, "disponivel")
            for numero in numeros
        ]
    )
    conexao.commit()


def cadastrar_reserva(
    conexao,
    id_reserva,
    quarto,
    entrada,
    saida,
    status="Confirmada"
):
    """Insere uma reserva para os testes."""

    conexao.execute(
        """
        INSERT INTO reservas (
            id, hospede_id, quarto_numero, data_reserva,
            data_entrada, data_saida, qtd_hospedes, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            id_reserva,
            f"H{id_reserva}",
            quarto,
            "2026-10-01",
            entrada,
            saida,
            1,
            status
        )
    )
    conexao.commit()


def test_relatorio_sem_quartos(banco_teste):
    """Sem quartos cadastrados, a ocupação deve ser zero."""

    resultado = relatorios.relatorio_ocupacao(
        date(2026, 10, 19),
        date(2026, 10, 19)
    )

    assert len(resultado) == 1
    assert resultado[0]["quartos_ocupados"] == 0
    assert resultado[0]["total_quartos"] == 0
    assert resultado[0]["percentual_ocupacao"] == 0.0


def test_relatorio_sem_reservas(banco_teste):
    """Quartos cadastrados sem reservas devem ter ocupação zero."""

    cadastrar_quartos(banco_teste, ["101", "102", "103"])

    resultado = relatorios.relatorio_ocupacao(
        date(2026, 10, 19),
        date(2026, 10, 19)
    )

    assert resultado[0]["quartos_ocupados"] == 0
    assert resultado[0]["total_quartos"] == 3
    assert resultado[0]["percentual_ocupacao"] == 0.0


def test_calcula_ocupacao_por_dia(banco_teste):
    """Conta quartos ocupados respeitando entrada e saída."""

    cadastrar_quartos(banco_teste, ["101", "102", "103"])

    cadastrar_reserva(
        banco_teste, "R1", "101", "2026-10-19", "2026-10-21"
    )
    cadastrar_reserva(
        banco_teste, "R2", "102", "2026-10-20", "2026-10-23"
    )

    resultado = relatorios.relatorio_ocupacao(
        date(2026, 10, 19),
        date(2026, 10, 23)
    )

    assert [dia["quartos_ocupados"] for dia in resultado] == [
        1, 2, 1, 1, 0
    ]

    assert [dia["percentual_ocupacao"] for dia in resultado] == [
        33.33, 66.67, 33.33, 33.33, 0.0
    ]


def test_reservas_canceladas_nao_contam(banco_teste):
    """Reservas canceladas não devem aumentar a ocupação."""

    cadastrar_quartos(banco_teste, ["101", "102"])

    cadastrar_reserva(
        banco_teste, "R1", "101", "2026-10-19", "2026-10-21"
    )
    cadastrar_reserva(
        banco_teste,
        "R2",
        "102",
        "2026-10-19",
        "2026-10-21",
        status="Cancelada"
    )

    resultado = relatorios.relatorio_ocupacao(
        date(2026, 10, 19),
        date(2026, 10, 19)
    )

    assert resultado[0]["quartos_ocupados"] == 1
    assert resultado[0]["total_quartos"] == 2
    assert resultado[0]["percentual_ocupacao"] == 50.0


def test_rejeita_data_inicial_posterior(banco_teste):
    """A data inicial não pode ser posterior à data final."""

    with pytest.raises(ValueError):
        relatorios.relatorio_ocupacao(
            date(2026, 10, 23),
            date(2026, 10, 19)
        )


@pytest.mark.parametrize(
    "data_inicio, data_fim",
    [
        ("2026-10-19", date(2026, 10, 23)),
        (date(2026, 10, 19), "2026-10-23"),
    ]
)
def test_rejeita_datas_que_nao_sao_date(
    banco_teste,
    data_inicio,
    data_fim
):
    """As datas devem ser objetos datetime.date."""

    with pytest.raises(ValueError):
        relatorios.relatorio_ocupacao(data_inicio, data_fim)
