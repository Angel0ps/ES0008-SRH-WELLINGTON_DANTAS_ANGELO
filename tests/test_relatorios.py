from datetime import date

import pytest

from app.models.pessoas import Hospede
from app.models.quartos import Simples, Duplo
from app.database.repositorio import Repositorio
from app.services.reservas import ServicoReservas
from app.services.relatorios import RelatorioOcupacao


@pytest.fixture
def repo():
    r = Repositorio(":memory:")
    r.salvar_quarto(Simples(numero="101", capacidade=2, diaria=100.0))
    r.salvar_quarto(Duplo(numero="102", capacidade=3, diaria=180.0))
    r.salvar_hospede(Hospede(
        id="h1", nome="Ana Souza", documento="12345678901",
        email="ana@mail.com", telefone="88999998888"))
    return r


def test_periodo_sem_reservas_taxa_zero(repo):
    rel = RelatorioOcupacao(repo)
    assert rel.taxa_ocupacao(date(2026, 12, 1), date(2026, 12, 8)) == 0.0


def test_reserva_ocupa_apenas_noites_do_periodo(repo):
    s = ServicoReservas(repo)
    s.criar_reserva(id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 4),
                    hospedes_ids=["h1"], qtd_hospedes=1)  # 2 noites
    rel = RelatorioOcupacao(repo)
    # 2 noites / (2 quartos x 7 dias) = 2/14
    assert rel.taxa_ocupacao(date(2026, 12, 1), date(2026, 12, 8)) == pytest.approx(1 / 7)


def test_periodo_parcial_conta_so_a_intersecao(repo):
    s = ServicoReservas(repo)
    s.criar_reserva(id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 6), data_saida=date(2026, 12, 8),
                    hospedes_ids=["h1"], qtd_hospedes=1)
    rel = RelatorioOcupacao(repo)
    # a reserva tem 2 noites (6 e 7); o período tem 7 dias e 2 quartos: 2/14
    assert rel.taxa_ocupacao(date(2026, 12, 6), date(2026, 12, 13)) == pytest.approx(1 / 7)


def test_reserva_cancelada_nao_conta_na_ocupacao(repo):
    s = ServicoReservas(repo)
    s.criar_reserva(id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 6),
                    hospedes_ids=["h1"], qtd_hospedes=1)
    s.cancelar("r1", hoje=date(2026, 12, 1))  # multa: 1 diária
    rel = RelatorioOcupacao(repo)
    assert rel.taxa_ocupacao(date(2026, 12, 1), date(2026, 12, 8)) == 0.0


def test_reserva_finalizada_conta_no_historico(repo):
    s = ServicoReservas(repo)
    s.criar_reserva(id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 4),
                    hospedes_ids=["h1"], qtd_hospedes=1)
    s.check_in("r1", hoje=date(2026, 12, 2))
    s.check_out("r1")
    rel = RelatorioOcupacao(repo)
    assert rel.taxa_ocupacao(date(2026, 12, 1), date(2026, 12, 8)) == pytest.approx(1 / 7)


def test_ocupacao_por_quarto(repo):
    s = ServicoReservas(repo)
    s.criar_reserva(id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 5),
                    hospedes_ids=["h1"], qtd_hospedes=1)
    rel = RelatorioOcupacao(repo)
    por_quarto = rel.ocupacao_por_quarto(date(2026, 12, 1), date(2026, 12, 8))
    assert por_quarto == {"101": 3, "102": 0}


def test_periodo_invalido(repo):
    rel = RelatorioOcupacao(repo)
    with pytest.raises(ValueError):
        rel.taxa_ocupacao(date(2026, 12, 8), date(2026, 12, 1))