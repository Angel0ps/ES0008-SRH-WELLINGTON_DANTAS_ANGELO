
# ======================= Testes de persistência dos lançamentos =======================

import sqlite3
from datetime import date

import pytest

from app.database.repositorio import Repositorio
from app.models.quartos import Simples
from app.models.pessoas import Hospede
from app.models.registros import Reserva, Pagamento, Adicional


@pytest.fixture
def repositorio(tmp_path):
    """Prepara um banco isolado para cada teste."""
    repo = Repositorio(tmp_path / "teste.db")

    # Cadastra o hóspede e o quarto necessários para a reserva.
    hospede = Hospede(
        id="H001",
        nome="Hóspede de Teste",
        documento="12345678900",
        email="teste@email.com",
        telefone="88999990000",
    )
    quarto = Simples(
        numero="101",
        capacidade=2,
        diaria=150.0,
    )

    repo.salvar_hospede(hospede)
    repo.salvar_quarto(quarto)

    # Cria uma reserva válida para associar os lançamentos.
    reserva = Reserva(
        id="R001",
        quarto_relacionado="101",
        data=date(2026, 10, 19),
        tipo="reserva",
        status="Confirmada",
        data_entrada=date(2026, 10, 20),
        data_saida=date(2026, 10, 22),
        qtd_hospedes=2,
        hospede_id="H001",
    )

    repo.salvar_reserva(reserva)

    yield repo

    repo.fechar()


def test_salvar_pagamento(repositorio):
    pagamento = Pagamento(
        id="P001",
        valor=200.0,
        data=date(2026, 10, 20),
        metodo="Pix",
    )

    # O repositório persiste os lançamentos associados à reserva.
    reserva = repositorio.obter_reserva("R001")
    reserva.pagamentos.append(pagamento)
    repositorio.salvar_reserva(reserva)

    registro = repositorio.conn.execute(
        "SELECT * FROM pagamentos WHERE id = ?",
        ("P001",),
    ).fetchone()

    assert registro is not None
    assert registro["reserva_id"] == "R001"
    assert registro["valor"] == pytest.approx(200.0)
    assert registro["data_pagamento"] == "2026-10-20"
    assert registro["metodo"] == "Pix"
    assert registro["forma"] == "Pix"


def test_salvar_adicional(repositorio):
    adicional = Adicional(
        id="A001",
        descricao="Serviço de lavanderia",
        valor=35.0,
        data=date(2026, 10, 21),
    )

    reserva = repositorio.obter_reserva("R001")
    reserva.adicionais.append(adicional)
    repositorio.salvar_reserva(reserva)

    registro = repositorio.conn.execute(
        "SELECT * FROM adicionais WHERE id = ?",
        ("A001",),
    ).fetchone()

    assert registro is not None
    assert registro["reserva_id"] == "R001"
    assert registro["descricao"] == "Serviço de lavanderia"
    assert registro["valor"] == pytest.approx(35.0)
    assert registro["data_lancamento"] == "2026-10-21"


def test_pagamento_pode_ser_recuperado_com_a_reserva(repositorio):
    pagamento = Pagamento(
        id="P002",
        valor=100.0,
        data=date(2026, 10, 20),
        metodo="Cartão",
    )

    reserva = repositorio.obter_reserva("R001")
    reserva.pagamentos.append(pagamento)
    repositorio.salvar_reserva(reserva)

    reserva_recuperada = repositorio.obter_reserva("R001")

    assert len(reserva_recuperada.pagamentos) == 1
    assert reserva_recuperada.pagamentos[0].id == "P002"
    assert reserva_recuperada.pagamentos[0].valor == pytest.approx(100.0)
    assert reserva_recuperada.pagamentos[0].metodo == "Cartão"


def test_adicional_pode_ser_recuperado_com_a_reserva(repositorio):
    adicional = Adicional(
        id="A002",
        descricao="Frigobar",
        valor=20.0,
        data=date(2026, 10, 21),
    )

    reserva = repositorio.obter_reserva("R001")
    reserva.adicionais.append(adicional)
    repositorio.salvar_reserva(reserva)

    reserva_recuperada = repositorio.obter_reserva("R001")

    assert len(reserva_recuperada.adicionais) == 1
    assert reserva_recuperada.adicionais[0].id == "A002"
    assert reserva_recuperada.adicionais[0].descricao == "Frigobar"


def test_pagamento_de_reserva_inexistente_e_rejeitado(repositorio):
    pagamento = Pagamento(
        id="P003",
        valor=100.0,
        data=date(2026, 10, 20),
        metodo="Cartão",
    )

    with pytest.raises(sqlite3.IntegrityError):
        with repositorio.conn:
            repositorio._salvar_pagamento_no_contexto(
                "RESERVA_INEXISTENTE",
                pagamento,
            )


def test_adicional_de_reserva_inexistente_e_rejeitado(repositorio):
    adicional = Adicional(
        id="A003",
        descricao="Frigobar",
        valor=20.0,
        data=date(2026, 10, 21),
    )

    with pytest.raises(sqlite3.IntegrityError):
        with repositorio.conn:
            repositorio._salvar_adicional_no_contexto(
                "RESERVA_INEXISTENTE",
                adicional,
            )
