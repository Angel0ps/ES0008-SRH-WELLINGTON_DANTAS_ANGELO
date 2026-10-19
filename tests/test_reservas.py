import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.registros import Registro, Reserva, Pagamento, Adicional

def _reserva(**overrides):
    base = dict(
        id="res1",
        quarto_relacionado="101",
        data=date(2026, 10, 10),
        tipo="reserva",
        status="ativo",
        data_entrada=date(2026, 10, 10),
        data_saida=date(2026, 10, 15),
        qtd_hospedes=2,
    )
    base.update(overrides)
    return Reserva(**base)
 
 
def test_registro_nao_pode_ser_instanciado_diretamente():
    with pytest.raises(TypeError):
        Registro(id="r1", quarto_relacionado="101", data=date.today(),
                 tipo="reserva", status="ativo")
 
 
def test_reserva_e_instancia_de_registro():
    r = _reserva()
    assert isinstance(r, Registro)
 
 
def test_criar_reserva_valida():
    r = _reserva()
    assert r.id == "res1"
    assert r.quarto_relacionado == "101"
    assert r.qtd_hospedes == 2
    assert r.adicionais == []
    assert r.pagamentos == []
 
 
def test_len_retorna_quantidade_de_noites():
    r = _reserva(data_entrada=date(2026, 10, 10), data_saida=date(2026, 10, 15))
    assert len(r) == 5
 
 
def test_data_saida_antes_de_entrada_levanta_erro():
    with pytest.raises(ValueError):
        _reserva(data_entrada=date(2026, 10, 15), data_saida=date(2026, 10, 10))
 
 
def test_qtd_hospedes_zero_levanta_erro():
    with pytest.raises(ValueError):
        _reserva(qtd_hospedes=0)
 
 
def test_qtd_hospedes_tipo_invalido_levanta_erro():
    with pytest.raises(ValueError):
        _reserva(qtd_hospedes="dois")
 
 
def test_adicional_negativo_levanta_erro():
    with pytest.raises(ValueError):
        Adicional(
            id="a1",
            descricao="Serviço extra",
            valor=-10.0,
            data=date(2026, 10, 10)
        )
 
 
def test_pagamentos_tipo_invalido_levanta_erro():
    with pytest.raises(ValueError):
        _reserva(pagamentos="não é lista")
 
 
def test_confirmar_altera_status():
    r = _reserva()
    assert r.status == "ativo"
    msg = r.confirmar()
    assert r.status == "Confirmada"
    assert "confirmada" in msg.lower()
 
 
def test_cancelar_reserva_altera_status():
    r = _reserva()
    msg = r.cancelarReserva()
    assert r.status == "Cancelada"
    assert "cancelada" in msg.lower()
 
 
def test_checkin_altera_status():
    r = _reserva()
    r.checkIn()
    assert r.status == "Hospedado"
 
 
def test_checkout_altera_status():
    r = _reserva()
    r.checkOut()
    assert r.status == "Finalizada"
 
 
def test_total_pago_sem_pagamentos():
    r = _reserva()
    assert r.total_pago() == 0.0
 
 
def test_total_devido_sem_pagamentos():
    adicional = Adicional(
        id="a1",
        descricao="Serviço extra",
        valor=50.0,
        data=date(2026, 10, 10)
    )

    r = _reserva(adicionais=[adicional])

    assert r.total_devido(valor_reserva=500.0) == 550.0
 
 
def test_total_devido_nunca_fica_negativo():
    pagamento = Pagamento(
        id="p1",
        valor=1000.0,
        data=date(2026, 10, 10),
        metodo="Cartão"
    )

    r = _reserva(pagamentos=[pagamento])

    assert r.total_devido(valor_reserva=100.0) == 0.0
 
 
# ---------- manipulação pós-criação ----------
 
def test_alterar_data_saida_atualiza_len():
    r = _reserva(data_entrada=date(2026, 10, 10), data_saida=date(2026, 10, 15))
    assert len(r) == 5
    r.data_saida = date(2026, 10, 20)
    assert len(r) == 10
 
 
def test_alterar_qtd_hospedes_apos_criacao():
    r = _reserva()
    r.qtd_hospedes = 4
    assert r.qtd_hospedes == 4
 
 
def test_str_reserva_contem_info_principal():
    r = _reserva()
    texto = str(r)
    assert "res1" in texto
    assert "101" in texto
 