from datetime import date

from app.models.registros import Reserva, Pagamento, Adicional
from app.services.tarifas import Tarifa

# ============================================= constantes de negócio =============================================
PRAZO_CANCELAMENTO_GRATUITO_DIAS = 2   # cancelar com >= 2 dias de antecedência: sem multa
MULTA_CANCELAMENTO_DIARIAS = 1         # fora do prazo: multa de 1 diária
MULTA_NO_SHOW_DIARIAS = 1              # não compareceu: multa de 1 diária

# status (em minúsculo) cujo quarto fica reservado/ocupado
STATUS_OCUPAM_QUARTO = ("confirmada", "hospedado")
# status de quarto que impedem novas reservas (ex.: manutenção)
STATUS_QUARTO_BLOQUEANTE = ("manutencao", "bloqueado")


def _norm(valor: str) -> str:
    """Normaliza um texto para comparações (minúsculas, sem espaços)."""
    return str(valor).strip().lower()


# ==================================================== Serviço de Reservas ====================================================
class ServicoReservas:
    """Regras de negócio: criação, check-in, check-out, cancelamento e no-show.

    Recebe um Repositorio e, opcionalmente, uma Tarifa (para valor da
    estadia e multas com fim de semana/temporada). Sem Tarifa, usa a
    diária simples do quarto.
    """

    def __init__(self, repositorio, tarifa: Tarifa | None = None):
        self.repositorio = repositorio
        self.tarifa = tarifa

    # ==================== criação ====================
    def criar_reserva(
        self,
        id: str,
        numero_quarto: str,
        data_entrada: date,
        data_saida: date,
        hospedes_ids: list,
        qtd_hospedes: int
    ) -> Reserva:
        # Valida datas e consistência dos hóspedes antes de consultar/persistir.
        if not isinstance(data_entrada, date) or not isinstance(data_saida, date):
            raise ValueError("As datas da reserva devem ser objetos date válidos")
        if data_saida <= data_entrada:
            raise ValueError("Data de saída deve ser posterior à data de entrada")
        if not isinstance(qtd_hospedes, int) or isinstance(qtd_hospedes, bool) or qtd_hospedes <= 0:
            raise ValueError("Quantidade de hóspedes deve ser um inteiro maior que zero")
        if not isinstance(hospedes_ids, (list, tuple)) or not hospedes_ids:
            raise ValueError("Informe os hóspedes vinculados à reserva")
        if len(set(hospedes_ids)) != len(hospedes_ids):
            raise ValueError("Não é permitido repetir hóspedes na reserva")

        quarto = self.repositorio.obter_quarto(numero_quarto)

        if quarto is None:
            raise ValueError(f"Quarto {numero_quarto!r} não cadastrado")

        if _norm(quarto.status) == "ocupado":
            raise ValueError(
                f"Quarto {quarto.numero} está ocupado e não aceita novas reservas"
            )

        if _norm(quarto.status) in STATUS_QUARTO_BLOQUEANTE:
            raise ValueError(
                f"Quarto {quarto.numero} está com status '{quarto.status}': não aceita reservas"
            )

        if qtd_hospedes > quarto.capacidade:
            raise ValueError(
                f"Capacidade excedida: quarto {quarto.numero} comporta {quarto.capacidade} hóspede(s), "
                f"mas foram pedidas {qtd_hospedes} vaga(s)"
            )

        if len(hospedes_ids) != qtd_hospedes:
            raise ValueError(
                "A quantidade de hóspedes deve corresponder ao número de hóspedes vinculados"
            )

        for hid in hospedes_ids:
            if self.repositorio.obter_hospede(hid) is None:
                raise ValueError(f"Hóspede {hid!r} não cadastrado")

        self._garantir_sem_conflito(quarto.numero, data_entrada, data_saida)

        reserva = Reserva(
            id=id,
            quarto_relacionado=quarto.numero,
            data=date.today(),
            tipo="reserva",
            status="Confirmada",
            data_entrada=data_entrada,
            data_saida=data_saida,
            qtd_hospedes=qtd_hospedes,
            hospedes_ids=list(hospedes_ids),
        )
        self.repositorio.salvar_reserva(reserva)

        return reserva

    def _garantir_sem_conflito(
        self, numero_quarto: str, entrada: date, saida: date
    ) -> None:
        """Bloqueia reservas sobrepostas no mesmo quarto.

        Usa intervalo semiaberto [entrada, saida): o check-out de uma
        reserva pode coincidir com o check-in de outra. Reservas
        Canceladas e No-shows não ocupam o quarto.
        """
        for outra in self.repositorio.listar_reservas():
            if outra.quarto_relacionado != numero_quarto:
                continue
            if _norm(outra.status) not in STATUS_OCUPAM_QUARTO:
                continue
            if entrada < outra.data_saida and outra.data_entrada < saida:
                raise ValueError(
                    f"Conflito de datas com a reserva {outra.id!r} "
                    f"({outra.data_entrada} -> {outra.data_saida}) no quarto {numero_quarto}"
                )

    # ==================== valor ====================
    def calcular_valor_reserva(self, reserva: Reserva) -> float:
        """noites x diária (com fim de semana/temporada, se houver Tarifa)."""
        tarifa = self.tarifa
        if tarifa is None:
            quarto = self.repositorio.obter_quarto(reserva.quarto_relacionado)
            tarifa = Tarifa(quarto.diaria)

        return tarifa.calcular_total(reserva.data_entrada, reserva.data_saida)

    def _diaria_do_quarto_na_data(self, reserva: Reserva, data: date) -> float:
        if self.tarifa is not None:
            return self.tarifa.calcular_diaria(data)

        quarto = self.repositorio.obter_quarto(reserva.quarto_relacionado)

        return quarto.diaria

    # ==================== fluxos ====================
    def check_in(self, reserva_id: str, hoje: date | None = None) -> Reserva:
        hoje = hoje or date.today()
        reserva = self._obter_reserva(reserva_id)

        if _norm(reserva.status) != "confirmada":
            raise ValueError(
                f"Check-in só é permitido em reserva Confirmada (atual: {reserva.status!r})"
            )

        if hoje < reserva.data_entrada:
            raise ValueError(
                f"Check-in antecipado: a entrada só está prevista para {reserva.data_entrada}"
            )

        reserva.checkIn()  # status -> Hospedado
        self.repositorio.salvar_reserva(reserva)

        quarto = self.repositorio.obter_quarto(reserva.quarto_relacionado)
        if _norm(quarto.status) == "disponivel":
            quarto.status = "ocupado"
            self.repositorio.salvar_quarto(quarto)

        return reserva

    def check_out(self, reserva_id: str) -> Reserva:
        reserva = self._obter_reserva(reserva_id)

        if _norm(reserva.status) != "hospedado":
            raise ValueError(
                f"Check-out só é permitido em reserva Hospedado (atual: {reserva.status!r})"
            )

        reserva.checkOut()  # status -> Finalizada
        self.repositorio.salvar_reserva(reserva)

        quarto = self.repositorio.obter_quarto(reserva.quarto_relacionado)
        quarto.status = "disponivel"
        self.repositorio.salvar_quarto(quarto)

        return reserva

    def cancelar(self, reserva_id: str, hoje: date | None = None) -> float:
        """Cancela a reserva e retorna o valor da multa.

        - faltando >= 2 dias para a entrada: multa zero;
        - caso contrário: multa de 1 diária (com tarifa, se houver).
        """
        hoje = hoje or date.today()
        reserva = self._obter_reserva(reserva_id)

        if _norm(reserva.status) != "confirmada":
            raise ValueError(
                f"Só é possível cancelar reserva Confirmada (atual: {reserva.status!r})"
            )

        dias_para_entrada = (reserva.data_entrada - hoje).days

        if dias_para_entrada >= PRAZO_CANCELAMENTO_GRATUITO_DIAS:
            multa = 0.0
        else:
            diaria = self._diaria_do_quarto_na_data(reserva, reserva.data_entrada)
            multa = diaria * MULTA_CANCELAMENTO_DIARIAS

        reserva.cancelarReserva()  # status -> Cancelada
        self.repositorio.salvar_reserva(reserva)

        return multa

    def no_show(self, reserva_id: str, hoje: date | None = None) -> float:
        """Marca a reserva como No-show e retorna a multa (1 diária).

        Só é possível se o dia da entrada já passou sem check-in.
        """
        hoje = hoje or date.today()
        reserva = self._obter_reserva(reserva_id)

        if _norm(reserva.status) != "confirmada":
            raise ValueError(
                f"Só é possível marcar No-show em reserva Confirmada (atual: {reserva.status!r})"
            )

        if hoje <= reserva.data_entrada:
            raise ValueError(
                f"No-show só pode ser marcado após o dia da entrada ({reserva.data_entrada})"
            )

        diaria = self._diaria_do_quarto_na_data(reserva, reserva.data_entrada)
        multa = diaria * MULTA_NO_SHOW_DIARIAS

        reserva.status = "No-show"
        self.repositorio.salvar_reserva(reserva)

        return multa

    # ==================== pagamentos e adicionais ====================
    def lancar_pagamento(
        self,
        reserva_id: str,
        id: str,
        forma: str,
        valor: float,
        data: date | None = None
    ) -> Pagamento:
        reserva = self._obter_reserva(reserva_id)

        pagamento = Pagamento(id, reserva.id, forma, valor, data or date.today())
        reserva.pagamentos.append(pagamento)
        self.repositorio.salvar_reserva(reserva)

        return pagamento

    def lancar_adicional(
        self,
        reserva_id: str,
        id: str,
        descricao: str,
        valor: float
    ) -> Adicional:
        reserva = self._obter_reserva(reserva_id)

        adicional = Adicional(id, reserva.id, descricao, valor)
        reserva.adicionais.append(adicional)
        self.repositorio.salvar_reserva(reserva)

        return adicional

    # ==================== auxiliar ====================
    def _obter_reserva(self, reserva_id: str) -> Reserva:
        reserva = self.repositorio.obter_reserva(reserva_id)

        if reserva is None:
            raise ValueError(f"Reserva {reserva_id!r} não encontrada")

        return reserva