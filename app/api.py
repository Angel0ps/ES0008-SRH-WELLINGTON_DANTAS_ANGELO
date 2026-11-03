"""Rotas HTTP do SRH. A aplicação ASGI é criada em app.main."""

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.database.repositorio import Repositorio
from app.models.pessoas import Funcionario, Hospede
from app.models.quartos import Simples, Duplo, Luxo
from app.models.registros import Bloqueio
from app.schemas.api import (
    AdicionalEntrada, BloqueioEntrada, DataOpcional, FuncionarioEntrada,
    HospedeEntrada, PagamentoEntrada, QuartoEntrada, ReservaEntrada,
)
from app.services.relatorios import (
    RelatorioCancelamentos, RelatorioOcupacao, RelatorioReceita,
)
from app.services.reservas import ServicoReservas
from app.services.tarifas import Tarifa

router = APIRouter()
TIPOS_QUARTO = {"Simples": Simples, "Duplo": Duplo, "Luxo": Luxo}


def obter_repositorio(request: Request) -> Repositorio:
    return request.app.state.repositorio


def _servico(repo: Repositorio, numero_quarto: str | None = None) -> ServicoReservas:
    tarifa = None
    if numero_quarto is not None:
        quarto = repo.obter_quarto(numero_quarto)
        if quarto is None:
            raise HTTPException(status_code=404, detail=f"Quarto {numero_quarto!r} não encontrado")
        tarifa = Tarifa(quarto.diaria)
    return ServicoReservas(repo, tarifa)


def _quarto_json(quarto) -> dict:
    return {
        "numero": quarto.numero, "tipo": type(quarto).__name__,
        "capacidade": quarto.capacidade, "diaria": quarto.diaria,
        "status": quarto.status, "diferencial": quarto.diferencial,
        "observacoes": quarto.observacoes,
        "bloqueios": [_bloqueio_json(b) for b in getattr(quarto, "bloqueios", [])],
    }


def _hospede_json(hospede) -> dict:
    return {
        "id": hospede.id, "nome": hospede.nome,
        "documento": hospede.documento, "email": hospede.email,
        "telefone": hospede.telefone, "observacoes": hospede.observacoes,
        "acessibilidade": hospede.acessibilidade,
    }


def _funcionario_json(funcionario) -> dict:
    return {
        "id": funcionario.id, "nome": funcionario.nome,
        "documento": funcionario.documento, "email": funcionario.email,
        "telefone": funcionario.telefone, "cargo": funcionario.cargo,
    }


def _bloqueio_json(bloqueio) -> dict:
    return {
        "id": bloqueio.id, "quarto": bloqueio.quarto_relacionado,
        "data_inicio": bloqueio.data.isoformat(),
        "data_fim": bloqueio.data_fim.isoformat(), "motivo": bloqueio.motivo,
        "tipo": bloqueio.tipo, "status": bloqueio.status,
    }


def _reserva_json(reserva) -> dict:
    pagamentos = [{
        "id": p.id, "forma": getattr(p, "forma", getattr(p, "metodo", "")),
        "valor": p.valor, "data": p.data.isoformat(),
        "categoria": getattr(p, "categoria", "hospedagem"),
    } for p in reserva.pagamentos]
    adicionais = [{
        "id": a.id, "descricao": a.descricao, "valor": a.valor,
        "data": a.data.isoformat() if hasattr(a, "data") else None,
    } for a in reserva.adicionais]
    ids = getattr(reserva, "hospedes_ids", None)
    if ids is None:
        principal = getattr(reserva, "hospede_id", None)
        ids = [principal] if principal else []
    return {
        "id": reserva.id, "quarto": reserva.quarto_relacionado,
        "status": reserva.status, "entrada": reserva.data_entrada.isoformat(),
        "saida": reserva.data_saida.isoformat(), "noites": len(reserva),
        "qtd_hospedes": reserva.qtd_hospedes, "hospedes_ids": list(ids),
        "total_pago": reserva.total_pago(), "total_adicionais": reserva.total_adicionais(),
        "pagamentos": pagamentos, "adicionais": adicionais,
    }


def _periodo(inicio: date, fim: date) -> None:
    if fim <= inicio:
        raise HTTPException(status_code=422, detail="O fim do período deve ser posterior ao início")


@router.get("/health", tags=["Sistema"])
def health():
    return {"status": "ok", "servico": "SRH-WDA"}


@router.get("/quartos", tags=["Quartos"])
def listar_quartos(repo: Repositorio = Depends(obter_repositorio)):
    return [_quarto_json(q) for q in repo.listar_quartos()]


@router.post("/quartos", status_code=status.HTTP_201_CREATED, tags=["Quartos"])
def cadastrar_quarto(dados: QuartoEntrada, repo: Repositorio = Depends(obter_repositorio)):
    classe = TIPOS_QUARTO[dados.tipo]
    quarto = classe(
        numero=dados.numero, capacidade=dados.capacidade, diaria=dados.diaria,
        status=dados.status, observacoes=dados.observacoes, diferencial=dados.diferencial,
    )
    repo.salvar_quarto(quarto)
    return _quarto_json(quarto)


@router.get("/hospedes", tags=["Hóspedes"])
def listar_hospedes(repo: Repositorio = Depends(obter_repositorio)):
    return [_hospede_json(h) for h in repo.listar_hospedes()]


@router.post("/hospedes", status_code=status.HTTP_201_CREATED, tags=["Hóspedes"])
def cadastrar_hospede(dados: HospedeEntrada, repo: Repositorio = Depends(obter_repositorio)):
    hospede = Hospede(**dados.model_dump())
    repo.salvar_hospede(hospede)
    return _hospede_json(hospede)


@router.get("/funcionarios", tags=["Funcionários"])
def listar_funcionarios(repo: Repositorio = Depends(obter_repositorio)):
    return [_funcionario_json(f) for f in repo.listar_funcionarios()]


@router.post("/funcionarios", status_code=status.HTTP_201_CREATED, tags=["Funcionários"])
def cadastrar_funcionario(dados: FuncionarioEntrada, repo: Repositorio = Depends(obter_repositorio)):
    funcionario = Funcionario(**dados.model_dump())
    repo.salvar_funcionario(funcionario)
    return _funcionario_json(funcionario)


@router.get("/funcionarios/{funcionario_id}", tags=["Funcionários"])
def obter_funcionario(funcionario_id: str, repo: Repositorio = Depends(obter_repositorio)):
    funcionario = repo.obter_funcionario(funcionario_id)
    if funcionario is None:
        raise HTTPException(status_code=404, detail="Funcionário não encontrado")
    return _funcionario_json(funcionario)


@router.get("/bloqueios", tags=["Bloqueios"])
def listar_bloqueios(repo: Repositorio = Depends(obter_repositorio)):
    return [_bloqueio_json(b) for b in repo.listar_bloqueios()]


@router.post("/bloqueios", status_code=status.HTTP_201_CREATED, tags=["Bloqueios"])
def cadastrar_bloqueio(dados: BloqueioEntrada, repo: Repositorio = Depends(obter_repositorio)):
    if repo.obter_quarto(dados.quarto) is None:
        raise HTTPException(status_code=404, detail="Quarto não encontrado")
    bloqueio = Bloqueio(
        id=dados.id, quarto_relacionado=dados.quarto, data=dados.data_inicio,
        data_fim=dados.data_fim, motivo=dados.motivo, tipo=dados.tipo,
        status=dados.status,
    )
    repo.salvar_bloqueio(bloqueio)
    return _bloqueio_json(bloqueio)


@router.post("/bloqueios/{bloqueio_id}/cancelar", tags=["Bloqueios"])
def cancelar_bloqueio(bloqueio_id: str, repo: Repositorio = Depends(obter_repositorio)):
    bloqueio = repo.obter_bloqueio(bloqueio_id)
    if bloqueio is None:
        raise HTTPException(status_code=404, detail="Bloqueio não encontrado")
    bloqueio.cancelar()
    repo.salvar_bloqueio(bloqueio)
    return _bloqueio_json(bloqueio)


@router.get("/reservas", tags=["Reservas"])
def listar_reservas(repo: Repositorio = Depends(obter_repositorio)):
    return [_reserva_json(r) for r in repo.listar_reservas()]


@router.post("/reservas", status_code=status.HTTP_201_CREATED, tags=["Reservas"])
def criar_reserva(dados: ReservaEntrada, repo: Repositorio = Depends(obter_repositorio)):
    servico = _servico(repo, dados.quarto)
    reserva = servico.criar_reserva(
        id=dados.id, numero_quarto=dados.quarto,
        data_entrada=dados.entrada, data_saida=dados.saida,
        hospedes_ids=dados.hospedes_ids, qtd_hospedes=dados.qtd_hospedes,
    )
    return _reserva_json(reserva)


@router.get("/reservas/{reserva_id}", tags=["Reservas"])
def obter_reserva(reserva_id: str, repo: Repositorio = Depends(obter_repositorio)):
    reserva = repo.obter_reserva(reserva_id)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva não encontrada")
    return _reserva_json(reserva)


@router.post("/reservas/{reserva_id}/checkin", tags=["Reservas"])
def checkin(reserva_id: str, dados: DataOpcional | None = None, repo: Repositorio = Depends(obter_repositorio)):
    servico = _servico_reserva_existente(repo, reserva_id)
    return _reserva_json(servico.check_in(reserva_id, dados.hoje if dados else None))


@router.post("/reservas/{reserva_id}/checkout", tags=["Reservas"])
def checkout(reserva_id: str, repo: Repositorio = Depends(obter_repositorio)):
    servico = _servico_reserva_existente(repo, reserva_id)
    return _reserva_json(servico.check_out(reserva_id))


@router.post("/reservas/{reserva_id}/cancelar", tags=["Reservas"])
def cancelar_reserva(reserva_id: str, dados: DataOpcional | None = None, repo: Repositorio = Depends(obter_repositorio)):
    servico = _servico_reserva_existente(repo, reserva_id)
    multa = servico.cancelar(reserva_id, dados.hoje if dados else None)
    return {"id": reserva_id, "status": "Cancelada", "multa": multa}


@router.post("/reservas/{reserva_id}/noshow", tags=["Reservas"])
def registrar_no_show(reserva_id: str, dados: DataOpcional | None = None, repo: Repositorio = Depends(obter_repositorio)):
    servico = _servico_reserva_existente(repo, reserva_id)
    multa = servico.no_show(reserva_id, dados.hoje if dados else None)
    return {"id": reserva_id, "status": "No-show", "multa": multa}


def _servico_reserva_existente(repo: Repositorio, reserva_id: str) -> ServicoReservas:
    reserva = repo.obter_reserva(reserva_id)
    if reserva is None:
        raise HTTPException(status_code=404, detail="Reserva não encontrada")
    return _servico(repo, reserva.quarto_relacionado)


@router.post("/reservas/{reserva_id}/pagamentos", status_code=status.HTTP_201_CREATED, tags=["Pagamentos"])
def lancar_pagamento(reserva_id: str, dados: PagamentoEntrada, repo: Repositorio = Depends(obter_repositorio)):
    servico = _servico_reserva_existente(repo, reserva_id)
    pagamento = servico.lancar_pagamento(
        reserva_id, id=dados.id, forma=dados.forma, valor=dados.valor,
        data=dados.data, categoria=dados.categoria,
    )
    return {
        "id": pagamento.id, "reserva": reserva_id,
        "forma": getattr(pagamento, "forma", pagamento.metodo),
        "valor": pagamento.valor, "data": pagamento.data.isoformat(),
        "categoria": pagamento.categoria,
    }


@router.post("/reservas/{reserva_id}/adicionais", status_code=status.HTTP_201_CREATED, tags=["Adicionais"])
def lancar_adicional(reserva_id: str, dados: AdicionalEntrada, repo: Repositorio = Depends(obter_repositorio)):
    adicional = _servico_reserva_existente(repo, reserva_id).lancar_adicional(
        reserva_id, id=dados.id, descricao=dados.descricao, valor=dados.valor,
    )
    return {"id": adicional.id, "reserva": reserva_id,
            "descricao": adicional.descricao, "valor": adicional.valor}


def _relatorios(repo: Repositorio, inicio: date, fim: date) -> dict:
    _periodo(inicio, fim)
    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "ocupacao": RelatorioOcupacao(repo).gerar(inicio, fim),
        "receita": RelatorioReceita(repo).gerar(inicio, fim),
        "cancelamentos": RelatorioCancelamentos(repo).gerar(inicio, fim),
    }


@router.get("/relatorios", tags=["Relatórios"])
def relatorios_consolidados(
    inicio: date = Query(...), fim: date = Query(...),
    repo: Repositorio = Depends(obter_repositorio),
):
    return _relatorios(repo, inicio, fim)


@router.get("/relatorios/ocupacao", tags=["Relatórios"])
def relatorio_ocupacao(inicio: date = Query(...), fim: date = Query(...), repo: Repositorio = Depends(obter_repositorio)):
    _periodo(inicio, fim)
    return RelatorioOcupacao(repo).gerar(inicio, fim)


@router.get("/relatorios/adr", tags=["Relatórios"])
def relatorio_adr(inicio: date = Query(...), fim: date = Query(...), repo: Repositorio = Depends(obter_repositorio)):
    _periodo(inicio, fim)
    receita = RelatorioReceita(repo).gerar(inicio, fim)
    return {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "adr": receita["adr"], "receita_hospedagem": receita["receita_hospedagem"]}


@router.get("/relatorios/revpar", tags=["Relatórios"])
def relatorio_revpar(inicio: date = Query(...), fim: date = Query(...), repo: Repositorio = Depends(obter_repositorio)):
    _periodo(inicio, fim)
    receita = RelatorioReceita(repo).gerar(inicio, fim)
    return {"inicio": inicio.isoformat(), "fim": fim.isoformat(), "revpar": receita["revpar"], "receita_hospedagem": receita["receita_hospedagem"]}


@router.get("/relatorios/cancelamentos", tags=["Relatórios"])
def relatorio_cancelamentos(inicio: date = Query(...), fim: date = Query(...), repo: Repositorio = Depends(obter_repositorio)):
    _periodo(inicio, fim)
    return RelatorioCancelamentos(repo).gerar(inicio, fim)
