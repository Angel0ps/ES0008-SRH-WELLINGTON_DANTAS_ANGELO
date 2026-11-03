from datetime import date
from app.models.quartos import Quarto
from app.models.rastreios import Rastreabilidade


# ==================================================== Super Classe Registro ====================================================

class Registro:  # Concentra os dados comuns a todos os registros. Como id, origem, data e etc.

    TIPOS_VALIDOS = ("reserva", "bloqueio")
    STATUS_VALIDOS = ("ativo", "cancelado", "finalizado")

    def __init__(
        self,
        id: str,
        quarto_relacionado: str,
        data: date,
        tipo: str,
        status: str
    ):
        if type(self) is Registro:
            raise TypeError(
                "Registro é abstrata e não pode ser instanciada diretamente.\n"
                "Use Reserva ou Bloqueio."
            )

        self.id = id
        self.quarto_relacionado = quarto_relacionado
        self.data = data
        self.tipo = tipo
        self.status = status

    # ================= id =====================

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("id não pode ser vazio")

        self.__id = str(valor).strip()

    # =========== quarto relacionado ============

    @property
    def quarto_relacionado(self):
        return self.__quarto_relacionado

    @quarto_relacionado.setter
    def quarto_relacionado(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("Quarto relacionado não pode ser vazio")

        self.__quarto_relacionado = str(valor).strip()

    # =========== data ============

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, valor: date):
        if not isinstance(valor, date):
            raise ValueError("Data deve ser um objeto do tipo date")

        self.__data = valor

    # =========== tipo ============

    @property
    def tipo(self):
        return self.__tipo

    @tipo.setter
    def tipo(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("Tipo não pode ser vazio")

        self.__tipo = str(valor).strip()

    # =========== status ============

    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("Status não pode ser vazio")

        self.__status = str(valor).strip()

    # ================= Métodos Especiais =====================

    def __str__(self):
        return (
            f"Registro: {self.id}\n"
            f"Quarto: {self.quarto_relacionado} \n"
            f"{self.status}"
        )

    def __repr__(self):
        return (
            f"{type(self).__name__}("
            f"id={self.id!r},"
            f"quarto_relacionado={self.quarto_relacionado!r}, "
            f"data={self.data!r}, "
            f"tipo={self.tipo!r}, "
            f"status={self.status!r})"
        )

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Registro):
            return NotImplemented

        return self.id == outro.id

    def __hash__(self):
        return hash(self.id)


# =================================================================== subclasse Reserva =================================================================

class Reserva(Registro, Rastreabilidade):
    # A classe central do sistema herda os atributos de Registro e Rastreabilidade.
    STATUS_VALIDOS = ("Pendente", "Confirmada", "Hospedado", "Finalizada", "Cancelada", "No-show")

    def __init__(
        self,
        id: str,
        quarto_relacionado: str,
        data: date,
        tipo: str,
        status: str,
        data_entrada: date,
        data_saida: date,
        qtd_hospedes: int,
        adicionais: list | None = None,
        pagamentos: list | None = None,
        hospede_id: str | None = None,
        hospedes_ids: list | None = None,
        origem: str = "balcao",
    ):
        super().__init__(
            id,
            quarto_relacionado,
            data,
            tipo,
            status
        )

        # Inicialização explícita porque Registro não herda de Rastreabilidade.
        Rastreabilidade.__init__(self)

        self.data_entrada = data_entrada
        self.data_saida = data_saida
        self.qtd_hospedes = qtd_hospedes
        self.hospedes_ids = (
            list(hospedes_ids) if hospedes_ids is not None
            else ([hospede_id] if hospede_id is not None else [])
        )
        self.adicionais = adicionais if adicionais is not None else []
        self.pagamentos = pagamentos if pagamentos is not None else []
        self.origem = origem

    @property
    def origem(self) -> str:
        return self.__origem

    @origem.setter
    def origem(self, valor: str) -> None:
        origem = str(valor or "").strip().casefold()
        if origem not in {"site", "telefone", "balcao"}:
            raise ValueError("Origem deve ser site, telefone ou balcao")
        self.__origem = origem

    # ========== data entrada ==========

    @property
    def data_entrada(self):
        return self.__data_entrada

    @data_entrada.setter
    def data_entrada(self, valor: date) -> None:
        if not isinstance(valor, date):
            raise ValueError(
                "Data de entrada deve ser um objeto do tipo date"
            )

        self.__data_entrada = valor

    # ========== data saída ==========

    @property
    def data_saida(self):
        return self.__data_saida

    @data_saida.setter
    def data_saida(self, valor: date) -> None:
        if not isinstance(valor, date):
            raise ValueError(
                "Data de saída deve ser um objeto do tipo date"
            )

        if hasattr(self, "_Reserva__data_entrada"):
            if valor <= self.__data_entrada:
                raise ValueError(
                    "Data de saída deve ser posterior à data de entrada"
                )

        self.__data_saida = valor

    # ========== hóspedes relacionados ==========

    @property
    def hospedes_ids(self):
        return self.__hospedes_ids

    @hospedes_ids.setter
    def hospedes_ids(self, valores: list):
        if not isinstance(valores, list):
            raise ValueError("IDs dos hóspedes devem estar em uma lista")

        ids = []

        for valor in valores:
            if valor is None or not str(valor).strip():
                raise ValueError("ID do hóspede não pode ser vazio")

            ids.append(str(valor).strip())

        if len(ids) != len(set(ids)):
            raise ValueError("Não é permitido repetir hóspedes na reserva")

        self.__hospedes_ids = ids
        self.__hospede_id = ids[0] if ids else None

    @property
    def hospede_id(self):
        return self.__hospede_id

    @hospede_id.setter
    def hospede_id(self, valor: str | None):
        if valor is None:
            self.__hospede_id = None

            if hasattr(self, "_Reserva__hospedes_ids"):
                self.__hospedes_ids = []

            return

        if not str(valor).strip():
            raise ValueError("ID do hóspede não pode ser vazio")

        valor = str(valor).strip()
        self.__hospede_id = valor

        if (
            hasattr(self, "_Reserva__hospedes_ids")
            and valor not in self.__hospedes_ids
        ):
            self.__hospedes_ids.insert(0, valor)

    def vincular_hospede(self, hospede_id: str):
        if not hospede_id or not str(hospede_id).strip():
            raise ValueError("ID do hóspede não pode ser vazio")

        hospede_id = str(hospede_id).strip()

        if hospede_id in self.hospedes_ids:
            raise ValueError("Hóspede já está vinculado à reserva")

        self.hospedes_ids = self.hospedes_ids + [hospede_id]

    # ========== quantidade de hóspedes ==========

    @property
    def qtd_hospedes(self):
        return self.__qtd_hospedes

    @qtd_hospedes.setter
    def qtd_hospedes(self, valor: int) -> None:
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise ValueError(
                "Quantidade de hóspedes deve ser um número inteiro"
            )

        if valor <= 0:
            raise ValueError(
                "Quantidade de hóspedes deve ser maior que zero"
            )

        self.__qtd_hospedes = valor

    # ========== adicionais ==========

    @property
    def adicionais(self):
        return self.__adicionais

    @adicionais.setter
    def adicionais(self, valor: list):
        if not isinstance(valor, list):
            raise ValueError("Adicionais deve ser uma lista")

        if not all(isinstance(item, Adicional) for item in valor):
            raise ValueError(
                "Todos os adicionais devem ser objetos Adicional"
            )

        self.__adicionais = valor

    # ========== pagamentos ==========

    @property
    def pagamentos(self):
        return self.__pagamentos

    @pagamentos.setter
    def pagamentos(self, valor: list):
        if not isinstance(valor, list):
            raise ValueError("Pagamentos deve ser uma lista")

        if not all(isinstance(item, Pagamento) for item in valor):
            raise ValueError(
                "Todos os pagamentos devem ser objetos Pagamento"
            )

        self.__pagamentos = valor

    # ========== métodos da reserva ==========

    def confirmar(self, responsavel: str = "sistema"):
        if self.status != "Pendente":
            raise ValueError("Somente reservas Pendentes podem ser confirmadas")
        self.status = "Confirmada"

        self.rastrearEdicao(
            responsavel,
            "Reserva confirmada."
        )

        return f"Reserva {self.id} confirmada."

    def cancelarReserva(self, responsavel: str = "sistema") -> str:
        if self.status not in ("Pendente", "Confirmada"):
            raise ValueError("Somente reservas Pendentes ou Confirmadas podem ser canceladas")
        self.status = "Cancelada"

        self.rastrearEdicao(
            responsavel,
            "Reserva cancelada."
        )

        return f"Reserva {self.id} cancelada."

    def checkIn(self, responsavel: str = "sistema"):
        if self.status != "Confirmada":
            raise ValueError("Check-in exige uma reserva Confirmada")
        self.status = "Hospedado"

        self.rastrearEdicao(
            responsavel,
            "Check-in realizado."
        )

        return f"Check-in da reserva {self.id} realizado."

    def checkOut(self, responsavel: str = "sistema"):
        if self.status != "Hospedado":
            raise ValueError("Check-out exige uma reserva com check-in realizado")
        self.status = "Finalizada"

        self.rastrearEdicao(
            responsavel,
            "Check-out realizado."
        )

        return f"Check-out da reserva {self.id} realizado."

    def marcarNoShow(self, responsavel: str = "sistema"):
        if self.status != "Confirmada":
            raise ValueError("No-show exige uma reserva Confirmada")
        self.status = "No-show"
        self.rastrearEdicao(responsavel, "No-show registrado.")
        return f"No-show da reserva {self.id} registrado."

    def total_pago(self) -> float:
        return sum(
            pagamento.valor
            for pagamento in self.pagamentos
        )

    def total_adicionais(self) -> float:
        return sum(
            adicional.valor
            for adicional in self.adicionais
        )

    def total_devido(self, valor_reserva: float) -> float:
        total = valor_reserva + self.total_adicionais()

        return max(0.0, total - self.total_pago())

    # ========== método especial ==========

    def __len__(self):
        return (self.data_saida - self.data_entrada).days

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Reserva):
            return NotImplemented
        return (
            self.quarto_relacionado == outro.quarto_relacionado
            and self.data_entrada == outro.data_entrada
            and self.data_saida == outro.data_saida
        )

    def __hash__(self) -> int:
        return hash((self.quarto_relacionado, self.data_entrada, self.data_saida))


# ============================================================== composições e subclasses =================================================================

class Pagamento(Rastreabilidade):
    # Pagamento realizado para uma reserva.

    def __init__(
        self,
        *args,
        id=None,
        valor=None,
        data=None,
        metodo=None,
        reserva_id=None,
        forma=None,
        categoria="hospedagem"
    ):
        # Aceita a assinatura do modelo (id, valor, data, metodo) e
        # a assinatura histórica do serviço/testes (id, reserva_id, forma, valor[, data]).
        if args:
            if (
                len(args) in (4, 5)
                and isinstance(args[1], str)
                and isinstance(args[2], str)
            ):
                id, reserva_id, forma, valor = args[:4]
                data = args[4] if len(args) == 5 else (data or date.today())
                metodo = forma

            elif len(args) >= 1:
                nomes = ("id", "valor", "data", "metodo")
                valores = dict(zip(nomes, args))
                id = valores.get("id", id)
                valor = valores.get("valor", valor)
                data = valores.get("data", data)
                metodo = valores.get("metodo", metodo)

        if forma is not None:
            metodo = forma

        self.id = id
        self.valor = valor
        self.data = data or date.today()
        self.metodo = metodo
        self.reserva_id = reserva_id
        self.categoria = categoria

        Rastreabilidade.__init__(self)

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("ID do pagamento não pode ser vazio")

        self.__id = str(valor).strip()

    @property
    def valor(self):
        return self.__valor

    @valor.setter
    def valor(self, valor: float):
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            raise ValueError("Valor do pagamento deve ser numérico")

        if valor <= 0:
            raise ValueError("Valor do pagamento deve ser positivo")

        self.__valor = valor

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, valor: date):
        if not isinstance(valor, date):
            raise ValueError("Data do pagamento deve ser do tipo date")

        self.__data = valor

    @property
    def metodo(self):
        return self.__metodo

    @metodo.setter
    def metodo(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("Método de pagamento não pode ser vazio")

        metodo = str(valor).strip()
        normalizado = (
            metodo.lower()
            .replace("á", "a")
            .replace("ã", "a")
            .replace("é", "e")
        )

        formas_validas = {
            "pix", "cartao", "cartao_credito", "cartao_debito",
            "credito", "debito", "dinheiro", "transferencia", "ted", "doc",
            "cartao de credito", "cartao de debito", "cartão", "cartão de crédito", "cartão de débito",
        }

        if normalizado not in formas_validas:
            raise ValueError(f"Método de pagamento inválido: {metodo!r}")

        self.__metodo = metodo

    @property
    def forma(self):
        return self.metodo

    @forma.setter
    def forma(self, valor):
        self.metodo = valor

    @property
    def categoria(self) -> str:
        return self.__categoria

    @categoria.setter
    def categoria(self, valor: str) -> None:
        categorias = {"hospedagem", "adicional", "outro"}
        categoria = str(valor).strip().casefold() if valor is not None else ""
        if categoria not in categorias:
            raise ValueError("Categoria deve ser hospedagem, adicional ou outro")
        self.__categoria = categoria


class Adicional:
    # Item ou serviço extra cobrado em uma reserva.

    def __init__(
        self,
        *args,
        id=None,
        descricao=None,
        valor=None,
        data=None,
        reserva_id=None
    ):
        # Aceita (id, descricao, valor, data) e (id, reserva_id, descricao, valor).
        if args:
            if (
                len(args) in (4, 5)
                and isinstance(args[1], str)
                and isinstance(args[2], str)
            ):
                id, reserva_id, descricao, valor = args[:4]
                data = args[4] if len(args) == 5 else (data or date.today())

            else:
                nomes = ("id", "descricao", "valor", "data")
                valores = dict(zip(nomes, args))
                id = valores.get("id", id)
                descricao = valores.get("descricao", descricao)
                valor = valores.get("valor", valor)
                data = valores.get("data", data)

        self.id = id
        self.descricao = descricao
        self.valor = valor
        self.data = data or date.today()
        self.reserva_id = reserva_id

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("ID do adicional não pode ser vazio")

        self.__id = str(valor).strip()

    @property
    def descricao(self):
        return self.__descricao

    @descricao.setter
    def descricao(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("Descrição do adicional não pode ser vazia")

        self.__descricao = str(valor).strip()

    @property
    def valor(self):
        return self.__valor

    @valor.setter
    def valor(self, valor: float):
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            raise ValueError("Valor do adicional deve ser numérico")

        if valor < 0:
            raise ValueError("Valor do adicional não pode ser negativo")

        self.__valor = valor

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, valor: date):
        if not isinstance(valor, date):
            raise ValueError("Data do adicional deve ser do tipo date")

        self.__data = valor


# ==================================================== Subclasse Bloqueio ====================================================

class Bloqueio(Registro, Rastreabilidade):
    """Indisponibilização de um quarto por um intervalo de datas.

    ``data`` representa o início; ``data_fim`` é inclusiva.
    """

    def __init__(
        self,
        id: str,
        quarto_relacionado: str,
        data: date,
        tipo: str = "manutencao",
        status: str = "ativo",
        criado_por: str = "sistema",
        data_fim: date | None = None,
        motivo: str = "",
    ):
        super().__init__(id, quarto_relacionado, data, tipo, status)
        self.data_fim = data_fim or data
        self.motivo = motivo
        Rastreabilidade.__init__(self, criado_por)

    @property
    def data_fim(self) -> date:
        return self.__data_fim

    @data_fim.setter
    def data_fim(self, valor: date) -> None:
        if not isinstance(valor, date):
            raise ValueError("Data final do bloqueio deve ser uma data válida")
        if valor < self.data:
            raise ValueError("Data final do bloqueio não pode anteceder a data inicial")
        self.__data_fim = valor

    @property
    def motivo(self) -> str:
        return self.__motivo

    @motivo.setter
    def motivo(self, valor: str) -> None:
        self.__motivo = str(valor or "").strip()

    def cancelar(self, responsavel: str = "sistema"):
        self.status = "cancelado"
        self.rastrearEdicao(responsavel, "Bloqueio cancelado.")
        return f"Bloqueio {self.id} cancelado."


# Definitivamente, era bom modularizar isso.
