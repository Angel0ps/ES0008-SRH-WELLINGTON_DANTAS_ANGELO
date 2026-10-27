# Testes da Semana 2 atualizados para a API nova de adicionais (lista de Adicional).
from datetime import date

import pytest

from app.models.registros import Registro, Reserva, Pagamento, Adicional


def _reserva(id="r1"):
    return Reserva(
        id=id,
        quarto_relacionado="101",
        data=date(2026, 10, 1),
        tipo="reserva",
        status="Confirmada",
        data_entrada=date(2026, 12, 10),
        data_saida=date(2026, 12, 14),
        qtd_hospedes=2,
        hospedes_ids=["h1", "h2"],
    )


def test_registro_abstrato_nao_instancia():
    with pytest.raises(TypeError):
        Registro("x", "101", date(2026, 10, 1), "reserva", "Confirmada")


def test_len_devolve_noites():
    assert len(_reserva()) == 4


def test_saida_deve_ser_apos_entrada():
    with pytest.raises(ValueError):
        _reserva().data_saida = date(2026, 12, 10)


def test_vincular_hospede_sem_repetir():
    r = _reserva()
    r.vincular_hospede("h3")
    assert r.hospedes_ids == ["h1", "h2", "h3"]
    with pytest.raises(ValueError):
        r.vincular_hospede("h3")


def test_hospedes_repetidos_no_construtor():
    with pytest.raises(ValueError):
        _reserva().hospedes_ids = ["h1", "h1"]


def test_fluxo_de_status():
    r = _reserva()
    r.checkIn()
    assert r.status == "Hospedado"
    r.checkOut()
    assert r.status == "Finalizada"
    r = _reserva(id="r2")
    r.cancelarReserva()
    assert r.status == "Cancelada"


def test_totais_com_objetos_pagamento_e_adicional():
    r = _reserva()
    r.pagamentos.append(Pagamento("p1", "r1", "pix", 200.0, date(2026, 12, 10)))
    r.pagamentos.append(Pagamento("p2", "r1", "cartao_credito", 100.0, date(2026, 12, 11)))
    r.adicionais.append(Adicional("a1", "r1", "Frigobar", 40.0))
    r.adicionais.append(Adicional("a2", "r1", "Lavanderia", 20.0))
    assert r.total_pago() == pytest.approx(300.0)
    assert r.total_adicionais() == pytest.approx(60.0)
    # 400 da reserva + 60 adicionais - 300 pago = 160
    assert r.total_devido(400.0) == pytest.approx(160.0)


def test_total_devido_nunca_negativo():
    r = _reserva()
    r.pagamentos.append(Pagamento("p1", "r1", "pix", 500.0))
    assert r.total_devido(100.0) == 0.0


def test_pagamento_forma_invalida():
    with pytest.raises(ValueError):
        Pagamento("p1", "r1", "cheque", 100.0)


def test_pagamento_e_adicional_valores_devem_ser_positivos():
    with pytest.raises(ValueError):
        Pagamento("p1", "r1", "pix", 0)
    with pytest.raises(ValueError):
        Adicional("a1", "r1", "Frigobar", -10)