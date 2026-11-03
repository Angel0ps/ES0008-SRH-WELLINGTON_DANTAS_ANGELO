"""Testes de integração HTTP da API FastAPI usando SQLite em memória."""

import pytest
from fastapi.testclient import TestClient

from app.database.repositorio import Repositorio
from app.main import create_app


@pytest.fixture
def client():
    repo = Repositorio(":memory:")
    app = create_app(repositorio=repo)
    with TestClient(app) as test_client:
        yield test_client
    repo.fechar()


def cadastrar_base(client):
    resposta = client.post("/quartos", json={
        "numero": "101", "capacidade": 2, "diaria": 100.0,
        "tipo": "Simples", "diferencial": "Acomodação econômica",
    })
    assert resposta.status_code == 201
    resposta = client.post("/hospedes", json={
        "id": "h1", "nome": "Ana Souza", "documento": "12345678901",
        "email": "ana@mail.com", "telefone": "88999998888",
    })
    assert resposta.status_code == 201


def criar_reserva(client, reserva_id="r1", entrada="2026-12-10", saida="2026-12-12"):
    resposta = client.post("/reservas", json={
        "id": reserva_id, "quarto": "101", "entrada": entrada,
        "saida": saida, "hospedes_ids": ["h1"], "qtd_hospedes": 1,
        "origem": "site",
    })
    if resposta.status_code == 201:
        client.post(f"/reservas/{reserva_id}/confirmar")
    return resposta


def test_fastapi_disponibiliza_openapi_e_health(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_post_e_get_quartos(client):
    cadastrar_base(client)
    resposta = client.get("/quartos")
    assert resposta.status_code == 200
    assert resposta.json()[0]["numero"] == "101"
    assert resposta.json()[0]["diferencial"] == "Acomodação econômica"


def test_post_hospede(client):
    resposta = client.post("/hospedes", json={
        "id": "h1", "nome": "Ana Souza", "documento": "12345678901",
        "email": "ana@mail.com", "telefone": "88999998888",
    })
    assert resposta.status_code == 201
    assert resposta.json()["nome"] == "Ana Souza"


def test_criar_reserva_inicia_pendente_e_pode_ser_confirmada(client):
    cadastrar_base(client)
    resposta = client.post("/reservas", json={
        "id": "r1", "quarto": "101", "entrada": "2026-12-10",
        "saida": "2026-12-12", "hospedes_ids": ["h1"],
        "qtd_hospedes": 1, "origem": "site",
    })
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "Pendente"
    assert resposta.json()["origem"] == "site"
    confirmacao = client.post("/reservas/r1/confirmar")
    assert confirmacao.status_code == 200
    assert confirmacao.json()["status"] == "Confirmada"
    assert resposta.json()["noites"] == 2


def test_conflito_de_datas_retorna_422(client):
    cadastrar_base(client)
    assert criar_reserva(client).status_code == 201
    resposta = criar_reserva(client, "r2", "2026-12-11", "2026-12-13")
    assert resposta.status_code == 422
    assert "Conflito" in resposta.json()["detail"]


def test_checkin_checkout_cancelamento_e_no_show(client):
    cadastrar_base(client)
    assert criar_reserva(client).status_code == 201
    resposta = client.post("/reservas/r1/checkin", json={"hoje": "2026-12-10"})
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "Hospedado"
    assert client.get("/quartos").json()[0]["status"] == "ocupado"
    client.post("/reservas/r1/pagamentos", json={
        "id": "p-checkout", "forma": "pix", "valor": 345.0,
        "data": "2026-12-12", "categoria": "hospedagem",
    })
    resposta = client.post("/reservas/r1/checkout", json={"momento": "2026-12-12T12:00:00"})
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "Finalizada"
    assert client.get("/quartos").json()[0]["status"] == "disponivel"


def test_cancelamento_com_multa_e_no_show(client):
    cadastrar_base(client)
    assert criar_reserva(client).status_code == 201
    resposta = client.post("/reservas/r1/cancelar", json={"hoje": "2026-12-09"})
    assert resposta.status_code == 200
    assert resposta.json()["multa"] == 150.0

    assert criar_reserva(client, "r2").status_code == 201
    resposta = client.post("/reservas/r2/noshow", json={"hoje": "2026-12-11"})
    assert resposta.status_code == 200
    assert resposta.json()["multa"] == 150.0


def test_pagamento_adicional_e_relatorio_financeiro_real(client):
    cadastrar_base(client)
    assert criar_reserva(client).status_code == 201
    pagamento = client.post("/reservas/r1/pagamentos", json={
        "id": "p1", "forma": "pix", "valor": 150.0,
        "data": "2026-12-10", "categoria": "hospedagem",
    })
    assert pagamento.status_code == 201
    adicional = client.post("/reservas/r1/pagamentos", json={
        "id": "p2", "forma": "pix", "valor": 30.0,
        "data": "2026-12-10", "categoria": "adicional",
    })
    assert adicional.status_code == 201
    resposta = client.get("/relatorios", params={"inicio": "2026-12-01", "fim": "2026-12-20"})
    assert resposta.status_code == 200
    assert resposta.json()["receita"]["receita_hospedagem"] == 150.0


def test_funcionarios_e_bloqueios(client):
    cadastrar_base(client)
    funcionario = client.post("/funcionarios", json={
        "id": "f1", "nome": "João Lima", "documento": "11122233344",
        "email": "joao@example.com", "telefone": "88999998888",
        "cargo": "Recepcionista",
    })
    assert funcionario.status_code == 201
    assert client.get("/funcionarios/f1").json()["cargo"] == "Recepcionista"

    bloqueio = client.post("/bloqueios", json={
        "id": "b1", "quarto": "101", "data_inicio": "2026-12-10",
        "data_fim": "2026-12-12", "motivo": "Manutenção elétrica",
    })
    assert bloqueio.status_code == 201
    reserva = criar_reserva(client)
    assert reserva.status_code == 422
    assert "bloqueado" in reserva.json()["detail"]

    cancelado = client.post("/bloqueios/b1/cancelar")
    assert cancelado.status_code == 200
    assert cancelado.json()["status"] == "cancelado"


def test_reserva_inexistente_retorna_404(client):
    resposta = client.get("/reservas/inexistente")
    assert resposta.status_code == 404


def test_validacao_pydantic_retorna_422(client):
    resposta = client.post("/quartos", json={"numero": "101", "capacidade": 0, "diaria": -1})
    assert resposta.status_code == 422


def test_crud_quartos_hospedes_e_historico(client):
    cadastrar_base(client)
    assert client.get("/quartos/101").status_code == 200
    atualizacao_quarto = client.put("/quartos/101", json={
        "numero": "101", "tipo": "Duplo", "capacidade": 3,
        "diaria": 180, "status": "disponivel",
    })
    assert atualizacao_quarto.status_code == 200
    assert atualizacao_quarto.json()["tipo"] == "Duplo"

    assert client.get("/hospedes/h1").status_code == 200
    atualizacao_hospede = client.put("/hospedes/h1", json={
        "id": "h1", "nome": "Ana Souza Atualizada",
        "documento": "12345678901", "email": "ana@mail.com",
        "telefone": "88999998888",
    })
    assert atualizacao_hospede.status_code == 200
    assert atualizacao_hospede.json()["nome"] == "Ana Souza Atualizada"

    assert criar_reserva(client).status_code == 201
    historico = client.get("/hospedes/h1/reservas")
    assert historico.status_code == 200
    assert historico.json()[0]["id"] == "r1"


def test_api_expoe_configuracoes_e_relatorio_por_tipo(client):
    config = client.get("/configuracoes")
    assert config.status_code == 200
    assert len(config.json()["tarifas"]["temporadas"]) == 3
    assert client.get(
        "/relatorios/receita-por-tipo?inicio=2026-12-01&fim=2027-01-01"
    ).status_code == 200


def test_api_crud_remove_recursos_sem_vinculos(client):
    cadastrar_base(client)
    assert client.delete("/quartos/101").status_code == 204
    assert client.get("/quartos/101").status_code == 404
    assert client.delete("/hospedes/h1").status_code == 204
    assert client.get("/hospedes/h1").status_code == 404


def test_api_impede_remover_quarto_vinculado_a_reserva(client):
    cadastrar_base(client)
    assert criar_reserva(client).status_code == 201
    resposta = client.delete("/quartos/101")
    assert resposta.status_code == 409


def test_bloqueio_nao_pode_ser_criado_sobre_reserva_confirmada(client):
    cadastrar_base(client)
    assert criar_reserva(client).status_code == 201
    resposta = client.post("/bloqueios", json={
        "id": "b-conflict", "quarto": "101",
        "data_inicio": "2026-12-11", "data_fim": "2026-12-13",
        "motivo": "Manutenção emergencial",
    })
    assert resposta.status_code == 409


def test_reserva_pendente_nao_ocupa_ate_confirmacao(client):
    cadastrar_base(client)
    payload = {
        "quarto": "101", "entrada": "2026-12-10", "saida": "2026-12-12",
        "hospedes_ids": ["h1"], "qtd_hospedes": 1,
    }
    primeira = client.post("/reservas", json={**payload, "id": "r-pendente-1"})
    segunda = client.post("/reservas", json={**payload, "id": "r-pendente-2"})
    assert primeira.status_code == segunda.status_code == 201
    assert client.post("/reservas/r-pendente-1/confirmar").status_code == 200
    conflito = client.post("/reservas/r-pendente-2/confirmar")
    assert conflito.status_code == 422


def test_reserva_rejeita_origem_invalida(client):
    cadastrar_base(client)
    resposta = client.post("/reservas", json={
        "id": "r-invalida", "quarto": "101", "entrada": "2026-12-10",
        "saida": "2026-12-12", "hospedes_ids": ["h1"],
        "qtd_hospedes": 1, "origem": "aplicativo",
    })
    assert resposta.status_code == 422


def test_no_show_api_respeita_tolerancia_em_minutos(client):
    cadastrar_base(client)
    assert criar_reserva(client).status_code == 201
    cedo = client.post("/reservas/r1/noshow", json={
        "momento": "2026-12-11T00:30:00",
    })
    assert cedo.status_code == 422
    valido = client.post("/reservas/r1/noshow", json={
        "momento": "2026-12-11T01:00:00",
    })
    assert valido.status_code == 200


def test_api_calcula_valor_previsto_da_reserva(client):
    cadastrar_base(client)
    criada = client.post("/reservas", json={
        "id": "r-valor", "quarto": "101", "entrada": "2026-12-10",
        "saida": "2026-12-12", "hospedes_ids": ["h1"], "qtd_hospedes": 1,
    })
    assert criada.status_code == 201
    assert criada.json()["valor_hospedagem"] == 345.0
    valor = client.get("/reservas/r-valor/valor")
    assert valor.status_code == 200
    assert valor.json()["saldo_devedor"] == 345.0
