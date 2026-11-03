from datetime import date, datetime, time, timedelta

from app.config import carregar_configuracoes

from app.models.registros import Reserva, Pagamento, Adicional
from app.services.tarifas import Tarifa

# ============================================= constantes de negócio =============================================
MULTA_NO_SHOW_DIARIAS = 1  # no-show: multa de uma diária

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

    def __init__(self, repositorio, tarifa: Tarifa | None = None, configuracoes: dict | None = None):
        self.repositorio = repositorio
        self.configuracoes = configuracoes or carregar_configuracoes()
        self.tarifa = tarifa

    # ==================== criação ====================
    def criar_reserva(
        self,
        id: str,
        numero_quarto: str,
        data_entrada: date,
        data_saida: date,
        hospedes_ids: list,
        qtd_hospedes: int,
        origem: str = "balcao",
        status_inicial: str = "Pendente",
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

        if status_inicial not in {"Pendente", "Confirmada"}:
            raise ValueError("Status inicial deve ser Pendente ou Confirmada")

        reserva = Reserva(
            id=id,
            quarto_relacionado=quarto.numero,
            data=date.today(),
            tipo="reserva",
            status=status_inicial,
            data_entrada=data_entrada,
            data_saida=data_saida,
            qtd_hospedes=qtd_hospedes,
            hospedes_ids=list(hospedes_ids),
            origem=origem,
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
        # Bloqueios por período são inclusivos no calendário; reservas usam
        # intervalo semiaberto [entrada, saída).
        for bloqueio in self.repositorio.listar_bloqueios(quarto_numero=numero_quarto):
            if _norm(bloqueio.status) not in ("ativo", "confirmado"):
                continue
            if entrada <= bloqueio.data_fim and bloqueio.data < saida:
                raise ValueError(
                    f"Quarto {numero_quarto} bloqueado de {bloqueio.data} a "
                    f"{bloqueio.data_fim}: {bloqueio.motivo or bloqueio.tipo}"
                )

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
    def confirmar(self, reserva_id: str) -> Reserva:
        reserva = self._obter_reserva(reserva_id)
        if _norm(reserva.status) != "pendente":
            raise ValueError("Somente reservas Pendentes podem ser confirmadas")
        quarto = self.repositorio.obter_quarto(reserva.quarto_relacionado)
        if quarto is None or _norm(quarto.status) in STATUS_QUARTO_BLOQUEANTE or _norm(quarto.status) == "ocupado":
            raise ValueError("Quarto indisponível para confirmação da reserva")
        self._garantir_sem_conflito(
            reserva.quarto_relacionado, reserva.data_entrada, reserva.data_saida
        )
        reserva.confirmar()
        self.repositorio.salvar_reserva(reserva)
        return reserva

    def check_in(self, reserva_id: str, hoje: date | datetime | None = None) -> Reserva:
        reserva = self._obter_reserva(reserva_id)
        if _norm(reserva.status) != "confirmada":
            raise ValueError(
                f"Check-in só é permitido em reserva Confirmada (atual: {reserva.status!r})"
            )

        hora_config = time.fromisoformat(self.configuracoes["checkin"]["horario"])
        tolerancia = int(self.configuracoes["checkin"]["tolerancia_antecipada_minutos"])
        momento = hoje or datetime.now()
        if isinstance(momento, date) and not isinstance(momento, datetime):
            momento = datetime.combine(momento, hora_config)
        elif momento.tzinfo is not None:
            momento = momento.astimezone().replace(tzinfo=None)
        if momento.date() != reserva.data_entrada:
            raise ValueError("Check-in antecipado ou fora da data prevista para a entrada")
        inicio_permitido = datetime.combine(reserva.data_entrada, hora_config) - timedelta(minutes=tolerancia)
        if momento < inicio_permitido:
            raise ValueError(f"Check-in permitido a partir de {inicio_permitido.time().strftime('%H:%M')}")

        quarto = self.repositorio.obter_quarto(reserva.quarto_relacionado)
        if quarto is None or _norm(quarto.status) != "disponivel":
            raise ValueError("Quarto deve estar DISPONIVEL para check-in")
        for bloqueio in self.repositorio.listar_bloqueios(quarto_numero=quarto.numero):
            if _norm(bloqueio.status) in ("ativo", "confirmado") and bloqueio.data <= momento.date() <= bloqueio.data_fim:
                raise ValueError("Quarto está bloqueado para manutenção na data do check-in")

        reserva.checkIn()
        self.repositorio.salvar_reserva(reserva)
        quarto.status = "ocupado"
        self.repositorio.salvar_quarto(quarto)
        return reserva

    def check_out(self, reserva_id: str, momento: date | datetime | None = None) -> Reserva:
        reserva = self._obter_reserva(reserva_id)
        if _norm(reserva.status) != "hospedado":
            raise ValueError(
                f"Check-out só é permitido em reserva Hospedado (atual: {reserva.status!r})"
            )

        horario = time.fromisoformat(self.configuracoes["checkout"]["horario"])
        tolerancia = int(self.configuracoes["checkout"]["tolerancia_atraso_minutos"])
        instante = momento or datetime.now()
        if isinstance(instante, date) and not isinstance(instante, datetime):
            instante = datetime.combine(instante, horario)
        elif instante.tzinfo is not None:
            instante = instante.astimezone().replace(tzinfo=None)
        if instante.date() < reserva.data_saida:
            raise ValueError("Check-out não pode ocorrer antes da data prevista para a saída")
        limite = datetime.combine(reserva.data_saida, horario) + timedelta(minutes=tolerancia)
        diarias_extras = 0
        if instante > limite:
            diarias_extras = max(
                1,
                (instante.date() - reserva.data_saida).days
                + (1 if instante.time() > horario else 0),
            )
        diaria_extra = sum(
            self._diaria_do_quarto_na_data(
                reserva, reserva.data_saida + timedelta(days=indice)
            )
            for indice in range(diarias_extras)
        )

        valor_hospedagem = self.calcular_valor_reserva(reserva)
        total_devido = valor_hospedagem + reserva.total_adicionais() + diaria_extra
        total_pago = reserva.total_pago()
        if total_pago + 0.00001 < total_devido:
            raise ValueError(
                f"Pagamento insuficiente: total devido R$ {total_devido:.2f}; "
                f"total pago R$ {total_pago:.2f}"
            )

        if diaria_extra:
            reserva.adicionais.append(
                Adicional(
                    id=f"late-checkout-{reserva.id}",
                    descricao=f"{diarias_extras} diária(s) extra(s) por check-out após o horário limite",
                    valor=diaria_extra,
                    data=reserva.data_saida,
                )
            )
        reserva.checkOut()
        self.repositorio.salvar_reserva(reserva)

        quarto = self.repositorio.obter_quarto(reserva.quarto_relacionado)
        if quarto is not None and _norm(quarto.status) == "ocupado":
            # A manutenção agendada permanece na tabela de bloqueios por período;
            # não transformamos um bloqueio temporário em status global permanente.
            quarto.status = "disponivel"
            self.repositorio.salvar_quarto(quarto)
        return reserva

    def cancelar(self, reserva_id: str, hoje: date | datetime | None = None) -> float:
        """Cancela reserva pendente/confirmada conforme a janela em horas."""
        reserva = self._obter_reserva(reserva_id)
        status_atual = _norm(reserva.status)
        if status_atual not in {"pendente", "confirmada"}:
            raise ValueError(
                f"Só é possível cancelar reserva Pendente ou Confirmada (atual: {reserva.status!r})"
            )

        if hoje is None:
            momento = datetime.now()
        elif isinstance(hoje, datetime):
            momento = hoje.astimezone().replace(tzinfo=None) if hoje.tzinfo else hoje
        elif isinstance(hoje, date):
            momento = datetime.combine(hoje, time.min)
        else:
            raise ValueError("Informe uma data ou data/hora válida para o cancelamento")

        hora_checkin = time.fromisoformat(self.configuracoes["checkin"]["horario"])
        entrada = datetime.combine(reserva.data_entrada, hora_checkin)
        horas_antecedencia = (entrada - momento).total_seconds() / 3600
        prazo_gratuito = int(self.configuracoes["cancelamento"]["prazo_gratuito_horas"])

        if status_atual == "pendente" or horas_antecedencia >= prazo_gratuito:
            multa = 0.0
        else:
            diaria = self._diaria_do_quarto_na_data(reserva, reserva.data_entrada)
            percentual = float(self.configuracoes["cancelamento"]["multa_percentual"])
            multa = diaria * percentual

        reserva.cancelarReserva()
        self.repositorio.salvar_reserva(reserva)
        self.repositorio.salvar_penalidade(reserva.id, "cancelamento", multa, momento.date())
        return multa

    def no_show(self, reserva_id: str, hoje: date | datetime | None = None) -> float:
        """Marca NO_SHOW após 23:59 da entrada mais a tolerância configurada."""
        reserva = self._obter_reserva(reserva_id)
        if _norm(reserva.status) != "confirmada":
            raise ValueError(
                f"Só é possível marcar No-show em reserva Confirmada (atual: {reserva.status!r})"
            )
        if hoje is None:
            momento = datetime.now()
        elif isinstance(hoje, datetime):
            momento = hoje.astimezone().replace(tzinfo=None) if hoje.tzinfo else hoje
        elif isinstance(hoje, date):
            # Uma data isolada representa o fim daquele dia para compatibilidade
            # com chamadas antigas; APIs podem enviar o instante exato.
            momento = datetime.combine(hoje, time.max)
        else:
            raise ValueError("Informe uma data ou data/hora válida para o no-show")

        limite = datetime.combine(reserva.data_entrada, time(23, 59)) + timedelta(
            minutes=int(self.configuracoes["no_show"]["tolerancia_minutos"])
        )
        if momento <= limite:
            raise ValueError(
                f"No-show só pode ser marcado após o dia da entrada e a tolerância: {limite.isoformat(sep=' ')}"
            )

        diaria = self._diaria_do_quarto_na_data(reserva, reserva.data_entrada)
        multa = diaria * MULTA_NO_SHOW_DIARIAS
        reserva.marcarNoShow("sistema")
        self.repositorio.salvar_reserva(reserva)
        self.repositorio.salvar_penalidade(reserva.id, "no_show", multa, momento.date())
        return multa

    # ==================== pagamentos e adicionais ====================
    def lancar_pagamento(
        self,
        reserva_id: str,
        id: str,
        forma: str,
        valor: float,
        data: date | None = None,
        categoria: str = "hospedagem"
    ) -> Pagamento:
        reserva = self._obter_reserva(reserva_id)

        pagamento = Pagamento(
            id, reserva.id, forma, valor, data or date.today(), categoria=categoria
        )
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