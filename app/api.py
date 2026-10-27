"""API HTTP mínima do Sistema de Reservas de Hotel (SRH).

Usa apenas a biblioteca padrão do Python e o repositório SQLite do projeto.
Execute na raiz do repositório:
    python -m app.api
    python -m app.api --porta 8080
    python -m app.api --db srh_wda.db
"""

import argparse
import json
import os
import sqlite3
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from app.database.repositorio import Repositorio
from app.models.quartos import Simples, Duplo, Luxo
from app.models.pessoas import Hospede
from app.services.tarifas import Tarifa
from app.services.reservas import ServicoReservas
from app.services.relatorios import RelatorioOcupacao

TIPOS_QUARTO = {"Simples": Simples, "Duplo": Duplo, "Luxo": Luxo}


def _quarto_json(quarto) -> dict:
    return {
        "numero": quarto.numero,
        "tipo": type(quarto).__name__,
        "capacidade": quarto.capacidade,
        "diaria": quarto.diaria,
        "status": quarto.status,
    }


def _hospede_json(hospede) -> dict:
    return {
        "id": hospede.id,
        "nome": hospede.nome,
        "documento": hospede.documento,
        "email": hospede.email,
        "telefone": hospede.telefone,
        "observacoes": getattr(hospede, "observacoes", ""),
        "acessibilidade": getattr(hospede, "acessibilidade", False),
    }


def _reserva_json(reserva) -> dict:
    pagamentos = []
    for pagamento in reserva.pagamentos:
        pagamentos.append({
            "id": pagamento.id,
            "forma": getattr(pagamento, "forma", getattr(pagamento, "metodo", "")),
            "valor": pagamento.valor,
            "data": str(pagamento.data),
        })

    adicionais = []
    for adicional in reserva.adicionais:
        adicionais.append({
            "id": adicional.id,
            "descricao": adicional.descricao,
            "valor": adicional.valor,
            "data": str(adicional.data) if hasattr(adicional, "data") else None,
        })

    hospedes_ids = getattr(reserva, "hospedes_ids", None)
    if hospedes_ids is None:
        hospede_id = getattr(reserva, "hospede_id", None)
        hospedes_ids = [hospede_id] if hospede_id else []

    return {
        "id": reserva.id,
        "quarto": reserva.quarto_relacionado,
        "status": reserva.status,
        "entrada": str(reserva.data_entrada),
        "saida": str(reserva.data_saida),
        "noites": len(reserva),
        "qtd_hospedes": reserva.qtd_hospedes,
        "hospedes_ids": list(hospedes_ids),
        "total_pago": reserva.total_pago(),
        "total_adicionais": reserva.total_adicionais(),
        "pagamentos": pagamentos,
        "adicionais": adicionais,
    }


def _data(texto: str) -> date:
    """Converte AAAA-MM-DD para date e retorna erro claro se inválido."""
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("Data obrigatória no formato AAAA-MM-DD")
    try:
        return date.fromisoformat(texto)
    except ValueError as erro:
        raise ValueError(f"Data inválida: {texto!r}. Use AAAA-MM-DD") from erro


def _servico(repo: Repositorio, numero_quarto: str | None = None) -> ServicoReservas:
    """Monta o serviço usando a diária do quarto, quando informada."""
    tarifa = None
    if numero_quarto is not None:
        quarto = repo.obter_quarto(numero_quarto)
        if quarto is None:
            raise ValueError(f"Quarto {numero_quarto!r} não encontrado")
        tarifa = Tarifa(quarto.diaria)
    return ServicoReservas(repo, tarifa)


def criar_handler(repo: Repositorio):
    """Cria um handler HTTP ligado ao repositório informado."""

    class HotelHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, formato, *args):
            # Evita poluir o terminal durante os testes.
            pass

        def _responder(self, status: int, payload) -> None:
            corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _ler_json(self) -> dict:
            try:
                tamanho = int(self.headers.get("Content-Length", "0"))
            except ValueError as erro:
                raise ValueError("Content-Length inválido") from erro

            if tamanho <= 0:
                return {}

            try:
                corpo = json.loads(self.rfile.read(tamanho).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as erro:
                raise ValueError("JSON inválido") from erro

            if not isinstance(corpo, dict):
                raise ValueError("O corpo JSON deve ser um objeto")
            return corpo

        def _partes(self) -> list[str]:
            caminho = urlparse(self.path).path
            return [parte for parte in caminho.split("/") if parte]

        def _query(self) -> dict:
            return parse_qs(urlparse(self.path).query)

        def do_GET(self) -> None:
            partes = self._partes()
            try:
                if partes == ["quartos"]:
                    return self._responder(200, [_quarto_json(q) for q in repo.listar_quartos()])

                if partes == ["hospedes"]:
                    return self._responder(200, [_hospede_json(h) for h in repo.listar_hospedes()])

                if partes == ["reservas"]:
                    return self._responder(200, [_reserva_json(r) for r in repo.listar_reservas()])

                if len(partes) == 2 and partes[0] == "reservas":
                    reserva = repo.obter_reserva(partes[1])
                    if reserva is None:
                        return self._responder(404, {"erro": "Reserva não encontrada"})
                    return self._responder(200, _reserva_json(reserva))

                if partes == ["relatorios", "ocupacao"]:
                    consulta = self._query()
                    inicio = _data(consulta["inicio"][0])
                    fim = _data(consulta["fim"][0])
                    relatorio = RelatorioOcupacao(repo)
                    return self._responder(200, {
                        "inicio": str(inicio),
                        "fim": str(fim),
                        "taxa_ocupacao": relatorio.taxa_ocupacao(inicio, fim),
                        "noites_por_quarto": relatorio.ocupacao_por_quarto(inicio, fim),
                    })

                return self._responder(404, {"erro": "Rota não encontrada"})
            except KeyError as erro:
                return self._responder(400, {"erro": f"Parâmetro obrigatório ausente: {erro.args[0]}"})
            except ValueError as erro:
                return self._responder(400, {"erro": str(erro)})

        def do_POST(self) -> None:
            partes = self._partes()
            try:
                corpo = self._ler_json()

                if partes == ["quartos"]:
                    tipo = corpo.get("tipo", "Simples")
                    classe_quarto = TIPOS_QUARTO.get(tipo)
                    if classe_quarto is None:
                        return self._responder(400, {
                            "erro": f"Tipo de quarto inválido: {tipo!r}. Use Simples, Duplo ou Luxo."
                        })
                    quarto = classe_quarto(
                        numero=corpo["numero"],
                        capacidade=corpo["capacidade"],
                        diaria=corpo["diaria"],
                        status=corpo.get("status", "disponivel"),
                        observacoes=corpo.get("observacoes", ""),
                    )
                    repo.salvar_quarto(quarto)
                    return self._responder(201, _quarto_json(quarto))

                if partes == ["hospedes"]:
                    hospede = Hospede(
                        id=corpo["id"],
                        nome=corpo["nome"],
                        documento=corpo["documento"],
                        email=corpo["email"],
                        telefone=corpo["telefone"],
                        observacoes=corpo.get("observacoes", ""),
                        acessibilidade=corpo.get("acessibilidade", False),
                    )
                    repo.salvar_hospede(hospede)
                    return self._responder(201, _hospede_json(hospede))

                if partes == ["reservas"]:
                    servico = _servico(repo, corpo["quarto"])
                    reserva = servico.criar_reserva(
                        id=corpo["id"],
                        numero_quarto=corpo["quarto"],
                        data_entrada=_data(corpo["entrada"]),
                        data_saida=_data(corpo["saida"]),
                        hospedes_ids=corpo["hospedes_ids"],
                        qtd_hospedes=corpo["qtd_hospedes"],
                    )
                    return self._responder(201, _reserva_json(reserva))

                if len(partes) == 3 and partes[0] == "reservas":
                    return self._acao_reserva(partes[1], partes[2], corpo)

                return self._responder(404, {"erro": "Rota não encontrada"})
            except KeyError as erro:
                return self._responder(400, {"erro": f"Campo obrigatório ausente: {erro.args[0]}"})
            except ValueError as erro:
                # Os serviços usam ValueError para violações de regras de negócio.
                return self._responder(422, {"erro": str(erro)})
            except sqlite3.IntegrityError as erro:
                return self._responder(422, {"erro": f"Violação de integridade dos dados: {erro}"})

        def _acao_reserva(self, reserva_id: str, acao: str, corpo: dict) -> None:
            servico = _servico(repo)

            if acao == "checkin":
                hoje = _data(corpo["hoje"]) if "hoje" in corpo else None
                reserva = servico.check_in(reserva_id, hoje)
                return self._responder(200, _reserva_json(reserva))

            if acao == "checkout":
                reserva = servico.check_out(reserva_id)
                return self._responder(200, _reserva_json(reserva))

            if acao == "cancelar":
                hoje = _data(corpo["hoje"]) if "hoje" in corpo else None
                multa = servico.cancelar(reserva_id, hoje)
                return self._responder(200, {
                    "id": reserva_id, "status": "Cancelada", "multa": multa
                })

            if acao == "noshow":
                hoje = _data(corpo["hoje"]) if "hoje" in corpo else None
                multa = servico.no_show(reserva_id, hoje)
                return self._responder(200, {
                    "id": reserva_id, "status": "No-show", "multa": multa
                })

            if acao == "pagamentos":
                pagamento = servico.lancar_pagamento(
                    reserva_id,
                    id=corpo["id"],
                    forma=corpo["forma"],
                    valor=corpo["valor"],
                    data=_data(corpo["data"]) if "data" in corpo else None,
                )
                return self._responder(201, {
                    "id": pagamento.id,
                    "reserva": reserva_id,
                    "forma": getattr(pagamento, "forma", getattr(pagamento, "metodo", "")),
                    "valor": pagamento.valor,
                    "data": str(pagamento.data),
                })

            if acao == "adicionais":
                adicional = servico.lancar_adicional(
                    reserva_id,
                    id=corpo["id"],
                    descricao=corpo["descricao"],
                    valor=corpo["valor"],
                )
                return self._responder(201, {
                    "id": adicional.id,
                    "reserva": reserva_id,
                    "descricao": adicional.descricao,
                    "valor": adicional.valor,
                })

            return self._responder(404, {"erro": f"Ação {acao!r} não encontrada"})

    return HotelHandler


def servir(host: str = "127.0.0.1", porta: int = 8000, caminho_db: str | None = None) -> None:
    caminho = caminho_db or os.environ.get("HOTEL_DB", "srh_wda.db")
    repo = Repositorio(caminho)
    servidor = ThreadingHTTPServer((host, porta), criar_handler(repo))
    print(f"API em http://{host}:{porta} usando o banco {caminho!r}")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando API...")
    finally:
        servidor.server_close()
        repo.fechar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="hotel-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--db", default=None, help="Caminho do banco SQLite (padrão: srh_wda.db)")
    args = parser.parse_args()
    servir(args.host, args.porta, args.db)
