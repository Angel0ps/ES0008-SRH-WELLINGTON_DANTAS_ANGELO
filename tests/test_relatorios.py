from datetime import date

import pytest

from app.models.pessoas import Hospede
from app.models.quartos import Simples, Duplo
from app.database.repositorio import Repositorio
from app.services.reservas import ServicoReservas
from app.services.relatorios import (
    RelatorioOcupacao, RelatorioReceita, RelatorioCancelamentos
)


@pytest.fixture
def repo():
    r = Repositorio(":memory:")
    r.salvar_quarto(Simples(numero="101", capacidade=2, diaria=100.0))
    r.salvar_quarto(Duplo(numero="102", capacidade=3, diaria=180.0))
    r.salvar_hospede(Hospede(
        id="h1", nome="Ana Souza", documento="12345678901",
        email="ana@mail.com", telefone="88999998888"))
    return r


def criar_confirmada(servico, **dados):
    reserva = servico.criar_reserva(**dados, status_inicial="Pendente")
    return servico.confirmar(reserva.id)


def test_periodo_sem_reservas_taxa_zero(repo):
    rel = RelatorioOcupacao(repo)
    assert rel.taxa_ocupacao(date(2026, 12, 1), date(2026, 12, 8)) == 0.0


def test_reserva_ocupa_apenas_noites_do_periodo(repo):
    s = ServicoReservas(repo)
    criar_confirmada(s,id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 4),
                    hospedes_ids=["h1"], qtd_hospedes=1)  # 2 noites
    rel = RelatorioOcupacao(repo)
    # 2 noites / (2 quartos x 7 dias) = 2/14
    assert rel.taxa_ocupacao(date(2026, 12, 1), date(2026, 12, 8)) == pytest.approx(100 / 7)


def test_periodo_parcial_conta_so_a_intersecao(repo):
    s = ServicoReservas(repo)
    criar_confirmada(s,id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 6), data_saida=date(2026, 12, 8),
                    hospedes_ids=["h1"], qtd_hospedes=1)
    rel = RelatorioOcupacao(repo)
    # a reserva tem 2 noites (6 e 7); o período tem 7 dias e 2 quartos: 2/14
    assert rel.taxa_ocupacao(date(2026, 12, 6), date(2026, 12, 13)) == pytest.approx(100 / 7)


def test_reserva_cancelada_nao_conta_na_ocupacao(repo):
    s = ServicoReservas(repo)
    criar_confirmada(s,id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 6),
                    hospedes_ids=["h1"], qtd_hospedes=1)
    s.cancelar("r1", hoje=date(2026, 12, 1))  # multa: 1 diária
    rel = RelatorioOcupacao(repo)
    assert rel.taxa_ocupacao(date(2026, 12, 1), date(2026, 12, 8)) == 0.0


def test_reserva_finalizada_conta_no_historico(repo):
    s = ServicoReservas(repo)
    criar_confirmada(s,id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 4),
                    hospedes_ids=["h1"], qtd_hospedes=1)
    s.check_in("r1", hoje=date(2026, 12, 2))
    valor = s.calcular_valor_reserva(repo.obter_reserva("r1"))
    s.lancar_pagamento("r1", "p-checkout", "pix", valor, date(2026, 12, 4))
    from datetime import datetime
    s.check_out("r1", datetime(2026, 12, 4, 12, 0))
    rel = RelatorioOcupacao(repo)
    assert rel.taxa_ocupacao(date(2026, 12, 1), date(2026, 12, 8)) == pytest.approx(100 / 7)


def test_ocupacao_por_quarto(repo):
    s = ServicoReservas(repo)
    criar_confirmada(s,id="r1", numero_quarto="101",
                    data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 5),
                    hospedes_ids=["h1"], qtd_hospedes=1)
    rel = RelatorioOcupacao(repo)
    por_quarto = rel.ocupacao_por_quarto(date(2026, 12, 1), date(2026, 12, 8))
    assert por_quarto == {"101": 3, "102": 0}


def test_periodo_invalido(repo):
    rel = RelatorioOcupacao(repo)
    with pytest.raises(ValueError):
        rel.taxa_ocupacao(date(2026, 12, 8), date(2026, 12, 1))


def test_adr_e_revpar_consideram_recebimentos_de_hospedagem(repo):
    servico = ServicoReservas(repo)
    criar_confirmada(servico,
        id="r-adr", numero_quarto="101",
        data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 4),
        hospedes_ids=["h1"], qtd_hospedes=1,
    )
    servico.lancar_pagamento(
        "r-adr", id="p-adr", forma="pix", valor=300.0,
        data=date(2026, 12, 3), categoria="hospedagem",
    )
    servico.lancar_pagamento(
        "r-adr", id="p-adicional", forma="pix", valor=80.0,
        data=date(2026, 12, 3), categoria="adicional",
    )
    relatorio = RelatorioReceita(repo)
    # Somente os R$ 300 recebidos como hospedagem entram no indicador.
    assert relatorio.adr(date(2026, 12, 1), date(2026, 12, 8)) == 150.0
    # 2 quartos x 7 dias = 14 noites disponíveis.
    assert relatorio.revpar(date(2026, 12, 1), date(2026, 12, 8)) == pytest.approx(21.43)


def test_receita_e_ocupacao_ignoram_canceladas(repo):
    servico = ServicoReservas(repo)
    criar_confirmada(servico,
        id="r-cancelada", numero_quarto="101",
        data_entrada=date(2026, 12, 2), data_saida=date(2026, 12, 4),
        hospedes_ids=["h1"], qtd_hospedes=1,
    )
    servico.cancelar("r-cancelada", hoje=date(2026, 12, 1))
    receita = RelatorioReceita(repo)
    ocupacao = RelatorioOcupacao(repo)
    assert receita.adr(date(2026, 12, 1), date(2026, 12, 8)) == 0.0
    assert receita.revpar(date(2026, 12, 1), date(2026, 12, 8)) == 0.0
    assert ocupacao.taxa_ocupacao(date(2026, 12, 1), date(2026, 12, 8)) == 0.0


def test_relatorio_cancelamentos_e_no_show_le_multas_persistidas(repo):
    servico = ServicoReservas(repo)
    criar_confirmada(servico,
        id="r-cancel", numero_quarto="101",
        data_entrada=date(2026, 12, 10), data_saida=date(2026, 12, 12),
        hospedes_ids=["h1"], qtd_hospedes=1,
    )
    servico.cancelar("r-cancel", hoje=date(2026, 12, 9))
    rel = RelatorioCancelamentos(repo).gerar(
        date(2026, 12, 9), date(2026, 12, 10)
    )
    assert rel["cancelamentos"] == 1
    assert rel["multas_cancelamento"] == 100.0
    assert rel["total_multas"] == 100.0


def test_penalidade_no_show_persistida_e_consultavel(repo):
    servico = ServicoReservas(repo)
    criar_confirmada(servico,
        id="r-noshow", numero_quarto="101",
        data_entrada=date(2026, 12, 10), data_saida=date(2026, 12, 12),
        hospedes_ids=["h1"], qtd_hospedes=1,
    )
    servico.no_show("r-noshow", hoje=date(2026, 12, 11))
    itens = repo.listar_penalidades(date(2026, 12, 11), date(2026, 12, 12))
    assert len(itens) == 1
    assert itens[0]["tipo"] == "no_show"
    assert itens[0]["valor"] == 100.0



def test_cancelamento_sem_multa_tambem_fica_persistido(tmp_path):
    caminho = tmp_path / "relatorio.db"
    r = Repositorio(caminho)
    r.salvar_quarto(Simples(numero="101", capacidade=2, diaria=100.0))
    r.salvar_hospede(Hospede(
        id="h1", nome="Ana Souza", documento="12345678901",
        email="ana@mail.com", telefone="88999998888"
    ))
    servico = ServicoReservas(r)
    criar_confirmada(servico,
        id="r-free", numero_quarto="101",
        data_entrada=date(2026, 12, 10), data_saida=date(2026, 12, 12),
        hospedes_ids=["h1"], qtd_hospedes=1,
    )
    assert servico.cancelar("r-free", hoje=date(2026, 12, 8)) == 0.0
    r.fechar()

    # Reabre o arquivo para comprovar persistência real no SQLite.
    reaberto = Repositorio(caminho)
    rel = RelatorioCancelamentos(reaberto).gerar(
        date(2026, 12, 8), date(2026, 12, 9)
    )
    assert rel["cancelamentos"] == 1
    assert rel["multas_cancelamento"] == 0.0
    assert rel["detalhes"][0]["valor"] == 0.0
    reaberto.fechar()


def test_relatorio_receita_por_tipo_de_quarto(repo):
    s = ServicoReservas(repo)
    criar_confirmada(s,
        id="r-simples", numero_quarto="101", data_entrada=date(2026, 12, 2),
        data_saida=date(2026, 12, 4), hospedes_ids=["h1"], qtd_hospedes=1,
    )
    s.lancar_pagamento("r-simples", "p-simples", "pix", 250, date(2026, 12, 3))
    receita = RelatorioReceita(repo).gerar(date(2026, 12, 1), date(2026, 12, 8))
    assert receita["receita_por_tipo_quarto"] == {"Simples": 250.0}


def test_noites_disponiveis_descontam_bloqueio_de_manutencao(repo):
    from app.models.registros import Bloqueio
    repo.salvar_bloqueio(Bloqueio(
        id="b-rel", quarto_relacionado="101", data=date(2026, 12, 2),
        data_fim=date(2026, 12, 3), motivo="Manutenção",
    ))
    rel = RelatorioOcupacao(repo)
    disponibilidade = rel.noites_disponiveis_por_quarto(date(2026, 12, 1), date(2026, 12, 5))
    assert disponibilidade["101"] == 2
    assert disponibilidade["102"] == 4
