"""Relatórios operacionais e financeiros do SRH.

Os períodos usam intervalo semiaberto [inicio, fim): a data final não é
incluída. ADR e RevPAR usam pagamentos efetivamente recebidos e classificados
como hospedagem, filtrados pela data de recebimento. As noites vendidas são
obtidas das reservas que ocuparam o quarto no período.
"""

from datetime import date, timedelta


STATUS_CONTAM_OCUPACAO = ("confirmada", "hospedado", "finalizada")
STATUS_CONTAM_RECEITA = ("confirmada", "hospedado", "finalizada")


def _normalizar_status(valor: str) -> str:
    return str(valor).strip().casefold()


def _validar_periodo(inicio: date, fim: date) -> None:
    if not isinstance(inicio, date) or not isinstance(fim, date):
        raise ValueError("Início e fim devem ser datas válidas")
    if fim <= inicio:
        raise ValueError("O fim do período deve ser posterior ao início")


class RelatorioOcupacao:
    """Calcula noites ocupadas e taxa de ocupação no período [início, fim)."""

    def __init__(self, repositorio):
        self.repositorio = repositorio

    @staticmethod
    def _noites_no_periodo(reserva, inicio: date, fim: date) -> int:
        ini = max(reserva.data_entrada, inicio)
        fim_reserva = min(reserva.data_saida, fim)
        return max(0, (fim_reserva - ini).days)

    def noites_disponiveis_por_quarto(self, inicio: date, fim: date) -> dict:
        """Conta noites vendáveis, descontando manutenção/bloqueios ativos."""
        _validar_periodo(inicio, fim)
        resultado = {}
        bloqueios = self.repositorio.listar_bloqueios()
        for quarto in self.repositorio.listar_quartos():
            if _normalizar_status(quarto.status) in {"manutencao", "bloqueado"}:
                resultado[quarto.numero] = 0
                continue
            noites = 0
            dia = inicio
            while dia < fim:
                indisponivel = any(
                    b.quarto_relacionado == quarto.numero
                    and _normalizar_status(b.status) in {"ativo", "confirmado"}
                    and b.data <= dia <= b.data_fim
                    for b in bloqueios
                )
                if not indisponivel:
                    noites += 1
                dia += timedelta(days=1)
            resultado[quarto.numero] = noites
        return resultado

    def ocupacao_por_quarto(self, inicio: date, fim: date) -> dict:
        _validar_periodo(inicio, fim)
        resultado = {q.numero: 0 for q in self.repositorio.listar_quartos()}
        for reserva in self.repositorio.listar_reservas():
            if _normalizar_status(reserva.status) not in STATUS_CONTAM_OCUPACAO:
                continue
            if reserva.quarto_relacionado in resultado:
                resultado[reserva.quarto_relacionado] += self._noites_no_periodo(
                    reserva, inicio, fim
                )
        return resultado

    def taxa_ocupacao(self, inicio: date, fim: date) -> float:
        _validar_periodo(inicio, fim)
        quartos = self.repositorio.listar_quartos()
        if not quartos:
            return 0.0
        noites = sum(self.ocupacao_por_quarto(inicio, fim).values())
        capacidade = sum(self.noites_disponiveis_por_quarto(inicio, fim).values())
        return (noites / capacidade * 100) if capacidade else 0.0

    def gerar(self, inicio: date, fim: date) -> dict:
        por_quarto = self.ocupacao_por_quarto(inicio, fim)
        noites_ocupadas = sum(por_quarto.values())
        noites_disponiveis = sum(self.noites_disponiveis_por_quarto(inicio, fim).values())
        taxa = (noites_ocupadas / noites_disponiveis * 100) if noites_disponiveis else 0.0
        return {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "noites_ocupadas": noites_ocupadas,
            "noites_disponiveis": noites_disponiveis,
            "taxa_ocupacao": round(taxa, 2),
            "taxa_ocupacao_fracao": round(taxa / 100, 4),
            "noites_por_quarto": por_quarto,
        }


class RelatorioReceita:
    """Calcula ADR e RevPAR a partir dos recebimentos de hospedagem.

    O numerador considera pagamentos da categoria ``hospedagem`` recebidos
    no período. O denominador considera noites de reservas confirmadas,
    hospedadas ou finalizadas que se sobrepõem ao período. Pagamentos de
    adicionais e outras categorias não entram na receita de hospedagem.
    """

    def __init__(self, repositorio):
        self.repositorio = repositorio

    def _metricas(self, inicio: date, fim: date) -> dict:
        _validar_periodo(inicio, fim)
        quartos = self.repositorio.listar_quartos()
        reservas = self.repositorio.listar_reservas()
        quartos_por_numero = {q.numero for q in quartos}
        noites_vendidas = 0

        for reserva in reservas:
            if _normalizar_status(reserva.status) not in STATUS_CONTAM_RECEITA:
                continue
            if reserva.quarto_relacionado not in quartos_por_numero:
                continue
            entrada = max(reserva.data_entrada, inicio)
            saida = min(reserva.data_saida, fim)
            if saida > entrada:
                noites_vendidas += (saida - entrada).days

        pagamentos = self.repositorio.listar_pagamentos(
            inicio, fim, categoria="hospedagem"
        )
        receita = sum(pagamento["valor"] for pagamento in pagamentos)
        disponibilidade = RelatorioOcupacao(self.repositorio).noites_disponiveis_por_quarto(inicio, fim)
        noites_disponiveis = sum(disponibilidade.values())
        receita_por_tipo = {}
        for pagamento in pagamentos:
            tipo = pagamento.get("tipo_quarto", "Não informado")
            receita_por_tipo[tipo] = receita_por_tipo.get(tipo, 0.0) + pagamento["valor"]
        receita_por_tipo = {tipo: round(valor, 2) for tipo, valor in sorted(receita_por_tipo.items())}
        adr = receita / noites_vendidas if noites_vendidas else 0.0
        revpar = receita / noites_disponiveis if noites_disponiveis else 0.0
        return {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "receita_hospedagem": round(receita, 2),
            "receita_hospedagem_recebida": round(receita, 2),
            "pagamentos_hospedagem": len(pagamentos),
            "noites_vendidas": noites_vendidas,
            "noites_disponiveis": noites_disponiveis,
            "adr": round(adr, 2),
            "revpar": round(revpar, 2),
            "receita_por_tipo_quarto": receita_por_tipo,
        }

    def adr(self, inicio: date, fim: date) -> float:
        return self._metricas(inicio, fim)["adr"]

    def revpar(self, inicio: date, fim: date) -> float:
        return self._metricas(inicio, fim)["revpar"]

    def gerar(self, inicio: date, fim: date) -> dict:
        return self._metricas(inicio, fim)


class RelatorioCancelamentos:
    """Consolida cancelamentos, no-shows e multas registradas no SQLite."""

    def __init__(self, repositorio):
        self.repositorio = repositorio

    def gerar(self, inicio: date, fim: date) -> dict:
        _validar_periodo(inicio, fim)
        # Contagens e multas do relatório são filtradas pela data do evento.
        registros = self.repositorio.listar_penalidades(inicio, fim)
        cancelamentos = [p for p in registros if p["tipo"] == "cancelamento"]
        no_shows = [p for p in registros if p["tipo"] == "no_show"]

        # As taxas são calculadas por coorte: reservas criadas no período e
        # penalidades associadas a essas mesmas reservas, mesmo que o evento
        # tenha ocorrido depois do fim do período.
        reservas_criadas = [
            r for r in self.repositorio.listar_reservas()
            if inicio <= r.data < fim
        ]
        ids_coorte = {r.id for r in reservas_criadas}
        penalidades_coorte = [
            p for p in self.repositorio.listar_penalidades()
            if p["reserva_id"] in ids_coorte
        ]
        cancelamentos_coorte = sum(
            p["tipo"] == "cancelamento" for p in penalidades_coorte
        )
        no_shows_coorte = sum(
            p["tipo"] == "no_show" for p in penalidades_coorte
        )
        total = len(reservas_criadas)
        total_eventos = len(cancelamentos) + len(no_shows)
        return {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "reservas_criadas": total,
            "cancelamentos": len(cancelamentos),
            "no_shows": len(no_shows),
            "total_nao_concretizadas": total_eventos,
            "cancelamentos_da_coorte": cancelamentos_coorte,
            "no_shows_da_coorte": no_shows_coorte,
            "taxa_cancelamento": (cancelamentos_coorte / total) if total else 0.0,
            "taxa_no_show": (no_shows_coorte / total) if total else 0.0,
            "multas_cancelamento": round(sum(p["valor"] for p in cancelamentos), 2),
            "multas_no_show": round(sum(p["valor"] for p in no_shows), 2),
            "total_multas": round(sum(p["valor"] for p in registros), 2),
            "detalhes": registros,
        }
