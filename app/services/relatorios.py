from app.services.reservas import _norm

# status que ocuparam/ocupam o quarto (para histórico de ocupação)
STATUS_CONTAM_OCUPACAO = ("confirmada", "hospedado", "finalizada")


# ==================================================== Relatório de Ocupação ====================================================
class RelatorioOcupacao:
    """Calcula a taxa de ocupação por período.

    taxa = noites ocupadas / (quantidade de quartos x dias do período).
    Reservas Canceladas e No-shows não ocupam o quarto.
    """

    def __init__(self, repositorio):
        self.repositorio = repositorio

    def _noites_no_periodo(self, reserva, inicio, fim) -> int:
        """Noites da reserva dentro de [inicio, fim): interseção de intervalos."""
        ini = max(reserva.data_entrada, inicio)
        fim_r = min(reserva.data_saida, fim)

        return max(0, (fim_r - ini).days)

    def taxa_ocupacao(self, inicio, fim) -> float:
        """Taxa de ocupação geral no período [inicio, fim)."""
        if fim <= inicio:
            raise ValueError("O fim do período deve ser posterior ao início")

        quartos = self.repositorio.listar_quartos()

        if not quartos:
            return 0.0

        dias = (fim - inicio).days
        noites = 0

        for reserva in self.repositorio.listar_reservas():
            if _norm(reserva.status) not in STATUS_CONTAM_OCUPACAO:
                continue
            noites += self._noites_no_periodo(reserva, inicio, fim)

        return noites / (len(quartos) * dias)

    def ocupacao_por_quarto(self, inicio, fim) -> dict:
        """Dicionario {numero_do_quarto: noites ocupadas} no período."""
        if fim <= inicio:
            raise ValueError("O fim do período deve ser posterior ao início")

        resultado = {q.numero: 0 for q in self.repositorio.listar_quartos()}

        for reserva in self.repositorio.listar_reservas():
            if _norm(reserva.status) not in STATUS_CONTAM_OCUPACAO:
                continue
            if reserva.quarto_relacionado in resultado:
                resultado[reserva.quarto_relacionado] += self._noites_no_periodo(reserva, inicio, fim)

        return resultado