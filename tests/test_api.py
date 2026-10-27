# Testes da API mínima (Semana 4): sobe o servidor numa thread com banco em memória
# e conversa com ele via urllib (só biblioteca padrão nos testes também).
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from app.database.repositorio import Repositorio
from app.api import criar_handler


@pytest.fixture
def api():
    repo = Repositorio(":memory:")
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), criar_handler(repo))
    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{servidor.server_address[1]}"
    yield base
    servidor.shutdown()
    servidor.server_close()
    repo.fechar()


def _req(metodo, url, corpo=None):
    dados = json.dumps(corpo).encode("utf-8") if corpo is not None else None
    requisicao = urllib.request.Request(url, data=dados, method=metodo)
    if dados is not None:
        requisicao.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(requisicao) as resposta:
            return resposta.status, json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as erro:
        return erro.code, json.loads(erro.read().decode("utf-8"))


def _setup(api):
    _req("POST", f"{api}/quartos",
         {"numero": "101", "capacidade": 2, "diaria": 100.0, "tipo": "Simples"})
    _req("POST", f"{api}/hospedes", {
        "id": "h1", "nome": "Ana Souza", "documento": "12345678901",
        "email": "ana@mail.com", "telefone": "88999998888",
    })


def _cria_reserva(api, id="r1", entrada="2026-12-10", saida="2026-12-12"):
    return _req("POST", f"{api}/reservas", {
        "id": id, "quarto": "101", "entrada": entrada, "saida": saida,
        "hospedes_ids": ["h1"], "qtd_hospedes": 1,
    })


# ==================== cadastros ====================
def test_post_e_get_quartos(api):
    status, _ = _req("POST", f"{api}/quartos",
                     {"numero": "101", "capacidade": 2, "diaria": 100.0, "tipo": "Simples"})
    assert status == 201
    status, quartos = _req("GET", f"{api}/quartos")
    assert status == 200
    assert quartos[0]["numero"] == "101"
    assert quartos[0]["tipo"] == "Simples"


def test_post_hospede(api):
    status, hospede = _req("POST", f"{api}/hospedes", {
        "id": "h1", "nome": "Ana Souza", "documento": "12345678901",
        "email": "ana@mail.com", "telefone": "88999998888",
    })
    assert status == 201
    assert hospede["nome"] == "Ana Souza"


# ==================== reservas ====================
def test_criar_reserva(api):
    _setup(api)
    status, reserva = _cria_reserva(api)
    assert status == 201
    assert reserva["status"] == "Confirmada"
    assert reserva["noites"] == 2


def test_conflito_de_datas_retorna_422(api):
    _setup(api)
    _cria_reserva(api, id="r1")
    status, erro = _cria_reserva(api, id="r2", entrada="2026-12-11", saida="2026-12-13")
    assert status == 422
    assert "Conflito" in erro["erro"]


def test_quarto_em_manutencao_retorna_422(api):
    _setup(api)
    _req("POST", f"{api}/quartos",
         {"numero": "101", "capacidade": 2, "diaria": 100.0, "status": "manutencao"})
    status, erro = _cria_reserva(api)
    assert status == 422
    assert "manutencao" in erro["erro"]


# ==================== fluxos ====================
def test_checkin_e_checkout(api):
    _setup(api)
    _cria_reserva(api)
    status, r = _req("POST", f"{api}/reservas/r1/checkin", {"hoje": "2026-12-10"})
    assert status == 200
    assert r["status"] == "Hospedado"
    status, quartos = _req("GET", f"{api}/quartos")
    assert quartos[0]["status"] == "ocupado"
    status, r = _req("POST", f"{api}/reservas/r1/checkout", {})
    assert r["status"] == "Finalizada"
    status, quartos = _req("GET", f"{api}/quartos")
    assert quartos[0]["status"] == "disponivel"


def test_cancelamento_com_multa(api):
    _setup(api)
    _cria_reserva(api, entrada="2026-12-10", saida="2026-12-12")
    status, corpo = _req("POST", f"{api}/reservas/r1/cancelar", {"hoje": "2026-12-09"})
    assert status == 200
    assert corpo["multa"] == 100.0
    assert corpo["status"] == "Cancelada"


def test_cancelamento_sem_multa(api):
    _setup(api)
    _cria_reserva(api, entrada="2026-12-10", saida="2026-12-12")
    status, corpo = _req("POST", f"{api}/reservas/r1/cancelar", {"hoje": "2026-12-08"})
    assert corpo["multa"] == 0.0


def test_no_show(api):
    _setup(api)
    _cria_reserva(api, entrada="2026-12-10", saida="2026-12-12")
    status, corpo = _req("POST", f"{api}/reservas/r1/noshow", {"hoje": "2026-12-11"})
    assert status == 200
    assert corpo["status"] == "No-show"
    assert corpo["multa"] == 100.0


def test_no_show_antes_da_entrada_retorna_422(api):
    _setup(api)
    _cria_reserva(api, entrada="2026-12-10", saida="2026-12-12")
    status, erro = _req("POST", f"{api}/reservas/r1/noshow", {"hoje": "2026-12-10"})
    assert status == 422


def test_reserva_inexistente_retorna_404(api):
    _setup(api)
    status, _ = _req("GET", f"{api}/reservas/zzz")
    assert status == 404


# ==================== pagamentos / adicionais / relatório ====================
def test_pagamento_e_adicional(api):
    _setup(api)
    _cria_reserva(api)
    status, _ = _req("POST", f"{api}/reservas/r1/pagamentos",
                     {"id": "p1", "forma": "pix", "valor": 150.0})
    assert status == 201
    status, _ = _req("POST", f"{api}/reservas/r1/adicionais",
                     {"id": "a1", "descricao": "Frigobar", "valor": 30.0})
    assert status == 201
    status, r = _req("GET", f"{api}/reservas/r1")
    assert r["total_pago"] == 150.0
    assert r["total_adicionais"] == 30.0


def test_relatorio_de_ocupacao(api):
    _setup(api)
    _cria_reserva(api, entrada="2026-12-10", saida="2026-12-12")
    status, rel = _req("GET", f"{api}/relatorios/ocupacao?inicio=2026-12-01&fim=2026-12-13")
    assert status == 200
    assert rel["noites_por_quarto"] == {"101": 2}
    assert rel["taxa_ocupacao"] == pytest.approx(2 / 12)  # 2 noites / (1 quarto x 12 dias)


def test_rota_inexistente_retorna_404(api):
    status, _ = _req("GET", f"{api}/qualquer")
    assert status == 404