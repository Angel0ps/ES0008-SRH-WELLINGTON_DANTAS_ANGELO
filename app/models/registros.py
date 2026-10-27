from datetime import date
from .quartos import Quarto

# ==================================================== Super Classe Registro ====================================================
class Registro: # Concentra os dados comuns a todos os registros. Como id, origem, data e etc.

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
                "Registro é abstrata e não pode ser instanciada diretamente.\nUse Reserva ou Bloqueio."
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
            raise ValueError(
                "id não pode ser vazio"
                )

        self.__id = str(valor).strip()

    # =========== quarto relacionado ============

    @property
    def quarto_relacionado(self):
        return self.__quarto_relacionado

    @quarto_relacionado.setter
    def quarto_relacionado(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError(
                "Quarto relacionado não pode ser vazio"
            )

        self.__quarto_relacionado = str(valor).strip()

    # =========== data ============

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, valor: date):
        if not isinstance(valor, date):
            raise ValueError(
                "Data deve ser um objeto do tipo date"
            )

        self.__data = valor

    # =========== tipo ============

    @property
    def tipo(self):
        return self.__tipo

    @tipo.setter
    def tipo(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError(
                "Tipo não pode ser vazio"
            )

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
            f"Registro: {self.id}\nQuarto: {self.quarto_relacionado} \n{self.status}"
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
class Reserva(Registro): # A classe central do sistema deve herdar atributos de registro e rastreabilidade. Contém data de entrada, saida, quarto reservado e etc.
                 # Por enquanto, vamos irei fazer sem herdar a rastreabilidade.

    def __init__( # Parâmetros da reserva
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
    ):
        super().__init__( # Chama o construtor da classe pai Registro
            id,
            quarto_relacionado,
            data,
            tipo,
            status
        )

        self.data_entrada = data_entrada
        self.data_saida = data_saida
        self.qtd_hospedes = qtd_hospedes
        self.hospedes_ids = (
            list(hospedes_ids) if hospedes_ids is not None
            else ([hospede_id] if hospede_id is not None else [])
        )
        self.adicionais = adicionais if adicionais is not None else []
        self.pagamentos = pagamentos if pagamentos is not None else []

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
        if hasattr(self, "_Reserva__hospedes_ids") and valor not in self.__hospedes_ids:
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

    def confirmar(self):
        self.status = "Confirmada"
        return f"Reserva {self.id} confirmada."

    def cancelarReserva(self) -> str:
        self.status = "Cancelada"
        return f"Reserva {self.id} cancelada."

    def checkIn(self):
        self.status = "Hospedado"
        return f"Check-in da reserva {self.id} realizado."

    def checkOut(self):
        self.status = "Finalizada"
        return f"Check-out da reserva {self.id} realizado."

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

# ============================================================== composições e subclasses =================================================================
  
class Pagamento:

    # Pagamento realizado para uma reserva.

    def __init__(self, *args, id=None, valor=None, data=None, metodo=None, reserva_id=None, forma=None):
        # Aceita a assinatura do modelo (id, valor, data, metodo) e
        # a assinatura histórica do serviço/testes (id, reserva_id, forma, valor[, data]).
        if args:
            if len(args) in (4, 5) and isinstance(args[1], str) and isinstance(args[2], str):
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
        normalizado = metodo.lower().replace("á", "a").replace("ã", "a").replace("é", "e")
        formas_validas = {
            "pix", "cartao", "cartao_credito", "cartao_debito",
            "credito", "debito", "dinheiro", "transferencia", "ted", "doc",
            "cartão", "cartão de crédito", "cartão de débito",
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


class Adicional:

    # Item ou serviço extra cobrado em uma reserva.

    def __init__(self, *args, id=None, descricao=None, valor=None, data=None, reserva_id=None):
        # Aceita (id, descricao, valor, data) e (id, reserva_id, descricao, valor).
        if args:
            if len(args) in (4, 5) and isinstance(args[1], str) and isinstance(args[2], str):
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
class Bloqueio():

    # Indisponibilização temporária de um quarto.

    pass

# Definitivamente, tenho que modularizar isso