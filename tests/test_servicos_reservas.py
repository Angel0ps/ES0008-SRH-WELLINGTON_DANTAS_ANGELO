from datetime import date

import pytest

from app.models.pessoas import Hospede
from app.models.quartos import Simples, Luxo
from app.database.repositorio import Repositorio
from app.services.reservas import ServicoReservas
from app.services.tarifas import Tarifa


@pytest.fixture
def repo():
    r = Repositorio(":memory:")
    r.salvar_quarto(Simples(numero="101", capacidade=2, diaria=100.0))
    r.salvar_quarto(Luxo(numero="201", capacidade=4, diaria=300.0))
    r.salvar_hospede(Hospede(
        id="h1", nome="Ana Souza", documento="12345678901",
        email="ana@mail.com", telefone="88999998888"))
    r.salvar_hospede(Hospede(
        id="h2", nome="Bruno Lima", documento="98765432100",
        email="bruno@mail.com", telefone="88988887777"))
    return r


@pytest.fixture
def servico(repo):
    return ServicoReservas(repo)


def _criar(servico, id="r1", quarto="101", entrada=date(2026, 12, 10),
           saida=date(2026, 12, 12), hospedes=("h1",), qtd=1):
    return servico.criar_reserva(
        id=id, numero_quarto=quarto, data_entrada=entrada, data_saida=saida,
        hospedes_ids=list(hospedes), qtd_hospedes=qtd)


# ==================== criação ====================
def test_criar_reserva_persiste(servico, repo):
    r = _criar(servico)
    assert r.status == "Confirmada"
    relida = repo.obter_reserva("r1")
    assert relida.data_entrada == date(2026, 12, 10)
    assert relida.hospedes_ids == ["h1"]


def test_criar_reserva_quarto_inexistente(servico):
    with pytest.raises(ValueError, match="não cadastrado"):
        _criar(servico, quarto="999")


def test_criar_reserva_quarto_em_manutencao(servico, repo):
    quarto = repo.obter_quarto("101")
    quarto.status = "manutencao"
    repo.salvar_quarto(quarto)
    with pytest.raises(ValueError, match="manutencao"):
        _criar(servico)


def test_criar_reserva_capacidade_excedida(servico):
    with pytest.raises(ValueError, match="Capacidade excedida"):
        _criar(servico, quarto="101", qtd=3)


def test_criar_reserva_hospede_inexistente(servico):
    with pytest.raises(ValueError, match="Hóspede"):
        _criar(servico, hospedes=("hx",))


# ==================== conflito de datas ====================
def test_conflito_de_datas_bloqueia(servico):
    _criar(servico, id="r1", entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    with pytest.raises(ValueError, match="Conflito"):
        _criar(servico, id="r2", entrada=date(2026, 12, 11), saida=date(2026, 12, 13))


def test_checkout_coincide_com_checkin_sem_conflito(servico):
    _criar(servico, id="r1", entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    r2 = _criar(servico, id="r2", entrada=date(2026, 12, 12), saida=date(2026, 12, 14))
    assert r2.id == "r2"  # intervalo semiaberto: encosta, não conflita


def test_reserva_cancelada_nao_conflita(servico):
    _criar(servico, id="r1", entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    servico.cancelar("r1", hoje=date(2026, 12, 8))  # >= 2 dias: sem multa
    r2 = _criar(servico, id="r2", entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    assert r2.id == "r2"


# ==================== check-in / check-out ====================
def test_check_in_ocupa_o_quarto(servico, repo):
    _criar(servico, entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    r = servico.check_in("r1", hoje=date(2026, 12, 10))
    assert r.status == "Hospedado"
    assert repo.obter_quarto("101").status == "ocupado"


def test_check_in_antecipado_e_barrado(servico):
    _criar(servico, entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    with pytest.raises(ValueError, match="antecipado"):
        servico.check_in("r1", hoje=date(2026, 12, 9))


def test_check_in_duplo_e_barrado(servico):
    _criar(servico, entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    servico.check_in("r1", hoje=date(2026, 12, 10))
    with pytest.raises(ValueError, match="Confirmada"):
        servico.check_in("r1", hoje=date(2026, 12, 10))


def test_check_out_libera_o_quarto(servico, repo):
    _criar(servico, entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    servico.check_in("r1", hoje=date(2026, 12, 10))
    r = servico.check_out("r1")
    assert r.status == "Finalizada"
    assert repo.obter_quarto("101").status == "disponivel"


def test_check_out_sem_checkin_e_barrado(servico):
    _criar(servico)
    with pytest.raises(ValueError, match="Hospedado"):
        servico.check_out("r1")


# ==================== cancelamento com multa ====================
def test_cancelamento_antecipado_sem_multa(servico):
    _criar(servico, entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    multa = servico.cancelar("r1", hoje=date(2026, 12, 8))  # faltam 2 dias
    assert multa == 0.0
    assert servico.repositorio.obter_reserva("r1").status == "Cancelada"


def test_cancelamento_em_cima_da_hora_com_multa_de_uma_diaria(servico):
    _criar(servico, entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    multa = servico.cancelar("r1", hoje=date(2026, 12, 9))  # faltam 1 dia
    assert multa == pytest.approx(100.0)  # 1 diária do quarto 101


def test_cancelar_duas_vezes_e_barrado(servico):
    _criar(servico)
    servico.cancelar("r1", hoje=date(2026, 12, 8))
    with pytest.raises(ValueError, match="Confirmada"):
        servico.cancelar("r1", hoje=date(2026, 12, 8))


# ==================== no-show ====================
def test_no_show_multa_de_uma_diaria(servico, repo):
    _criar(servico, entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    multa = servico.no_show("r1", hoje=date(2026, 12, 11))  # passou o dia da entrada
    assert multa == pytest.approx(100.0)
    assert repo.obter_reserva("r1").status == "No-show"


def test_no_show_antes_da_entrada_e_barrado(servico):
    _criar(servico, entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    with pytest.raises(ValueError, match="dia da entrada"):
        servico.no_show("r1", hoje=date(2026, 12, 10))


def test_no_show_libera_o_quarto_para_nova_reserva(servico):
    _criar(servico, id="r1", entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    servico.no_show("r1", hoje=date(2026, 12, 11))
    r2 = _criar(servico, id="r2", entrada=date(2026, 12, 10), saida=date(2026, 12, 12))
    assert r2.id == "r2"


# ==================== tarifa no valor da reserva ====================
def test_valor_da_reserva_com_tarifa(repo):
    servico = ServicoReservas(repo, Tarifa(100.0))
    r = _criar(servico, entrada=date(2026, 12, 4), saida=date(2026, 12, 6))  # sex + sáb, em dez
    valor = servico.calcular_valor_reserva(r)
    assert valor == pytest.approx(195.0 + 195.0)


def test_multa_usa_tarifa_quando_informada(repo):
    servico = ServicoReservas(repo, Tarifa(100.0))
    _criar(servico, entrada=date(2026, 12, 4), saida=date(2026, 12, 6))  # entrada numa sexta de dez
    multa = servico.cancelar("r1", hoje=date(2026, 12, 3))
    assert multa == pytest.approx(195.0)


# ==================== pagamentos e adicionais ====================
def test_lancar_pagamento_e_adicional_atualiza_totais(servico):
    _criar(servico)
    servico.lancar_pagamento("r1", id="p1", forma="pix", valor=150.0)
    servico.lancar_adicional("r1", id="a1", descricao="Frigobar", valor=30.0)
    r = servico.repositorio.obter_reserva("r1")
    assert r.total_pago() == pytest.approx(150.0)
    assert r.total_adicionais() == pytest.approx(30.0)
    assert r.total_devido(200.0) == pytest.approx(80.0)  # 200 + 30 - 150