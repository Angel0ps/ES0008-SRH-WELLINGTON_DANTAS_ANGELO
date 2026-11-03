# ============================================ Super Classe Quartos ============================================

from abc import ABC, abstractmethod


class Quarto(ABC):
    """Representa um quarto e concentra as validações comuns.

    A classe é abstrata: as categorias concretas implementam
    requisitarQuarto() e herdam as validações comuns.
    """

    STATUS_VALIDOS = ("disponivel", "ocupado", "manutencao", "bloqueado")

    def __init__(self, numero: str, capacidade: int, diaria: float,
                 status: str = "disponivel", bloqueios: list | None = None,
                 observacoes: str = ""):
        self.__numero = numero
        self.__capacidade = capacidade
        self.__diaria = diaria
        self.__status = status
        self.__bloqueios = bloqueios if bloqueios is not None else []
        self.__observacoes = observacoes

    # ================================ propriedades =============================

    @property
    def numero(self) -> str:
        return self.__numero

    @numero.setter
    def numero(self, endereco: str) -> None:
        if not endereco or not str(endereco).strip():
            raise ValueError("O número do quarto não pode ser vazio.")
        self.__numero = str(endereco).strip()

    @property
    def capacidade(self) -> int:
        return self.__capacidade

    @capacidade.setter
    def capacidade(self, quantidade: int) -> None:
        if (not isinstance(quantidade, int) or isinstance(quantidade, bool)
                or quantidade <= 0):
            raise ValueError("A capacidade do quarto deve ser um número inteiro positivo.")
        self.__capacidade = quantidade

    @property
    def diaria(self) -> float:
        return self.__diaria

    @diaria.setter
    def diaria(self, valor: float) -> None:
        if (not isinstance(valor, (int, float)) or isinstance(valor, bool)
                or valor <= 0):
            raise ValueError("O valor da diária deve ser um número positivo.")
        self.__diaria = float(valor)

    @property
    def status(self) -> str:
        return self.__status

    @status.setter
    def status(self, situacao: str) -> None:
        if situacao not in self.STATUS_VALIDOS:
            raise ValueError(
                f"Status inválido: {situacao!r}. Use um de {self.STATUS_VALIDOS}"
            )
        self.__status = situacao

    @property
    def bloqueios(self) -> list:
        # Cópia para evitar alteração externa sem passar pela propriedade.
        return list(self.__bloqueios)

    @bloqueios.setter
    def bloqueios(self, lista: list) -> None:
        if not isinstance(lista, list):
            raise TypeError("bloqueios deve ser uma lista.")
        self.__bloqueios = list(lista)

    @property
    def observacoes(self) -> str:
        return self.__observacoes

    @observacoes.setter
    def observacoes(self, obs: str) -> None:
        if not isinstance(obs, str):
            raise ValueError("As observações devem ser uma string.")
        self.__observacoes = obs.strip()

    @property
    def diferencial(self) -> str:
        return self.__diferencial

    @diferencial.setter
    def diferencial(self, valor: str) -> None:
        if not isinstance(valor, str):
            raise ValueError("O diferencial deve ser uma string.")
        self.__diferencial = valor.strip()

    # ================================ métodos UML =============================

    @abstractmethod
    def requisitarQuarto(self) -> str:
        """Retorna uma descrição simples para apresentação do quarto."""
        return (
            f"Quarto {self.numero} - {type(self).__name__}; "
            f"capacidade: {self.capacidade}; diária: R$ {self.diaria:.2f}; "
            f"status: {self.status}."
        )

    # ============================ métodos especiais ===========================

    def __str__(self) -> str:
        return f"Quarto {self.numero} ({self.status}) - R$ {self.diaria:.2f}/noite"

    def __lt__(self, outro: "Quarto"):
        """Ordena primeiro por categoria e depois pela numeração do quarto."""
        if not isinstance(outro, Quarto):
            return NotImplemented
        ordem = {"Simples": 0, "Duplo": 1, "Luxo": 2}
        def chave(quarto):
            numero = str(quarto.numero)
            numero_ordenavel = (0, int(numero)) if numero.isdigit() else (1, numero.casefold())
            return (ordem.get(type(quarto).__name__, 99), numero_ordenavel)
        return chave(self) < chave(outro)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(numero={self.numero!r}, "
            f"capacidade={self.capacidade}, diaria={self.diaria}, "
            f"status={self.status!r}, diferencial={self.diferencial!r})"
        )

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Quarto):
            return NotImplemented
        return self.numero == outro.numero

    def __hash__(self) -> int:
        return hash(self.numero)


# ================================ subclasses concretas ================================

class Simples(Quarto):
    def requisitarQuarto(self) -> str:
        return super().requisitarQuarto()

    def diferenciarSimples(self) -> str:
        return self.diferencial or "Quarto da categoria simples."

    def observacoesSimples(self) -> str:
        return self.observacoes or "Sem observações adicionais para o quarto simples."


class Duplo(Quarto):
    def requisitarQuarto(self) -> str:
        return super().requisitarQuarto()

    def diferenciarDuplo(self) -> str:
        return self.diferencial or "Quarto da categoria dupla."

    def observacoesDuplo(self) -> str:
        return self.observacoes or "Sem observações adicionais para o quarto duplo."


class Luxo(Quarto):
    def requisitarQuarto(self) -> str:
        return super().requisitarQuarto()

    def diferenciarLuxo(self) -> str:
        return self.diferencial or "Quarto da categoria luxo."

    def observacoesLuxo(self) -> str:
        return self.observacoes or "Sem observações adicionais para o quarto luxo."
