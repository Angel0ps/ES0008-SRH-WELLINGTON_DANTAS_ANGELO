# ============================================ Super Classe Quartos ============================================

class Quarto():

    # Classe base abstrata de um quarto.
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

    # ================================ métodos =============================

    # ==== número do apto ====
    @property
    def numero(self):
        return self.__numero

    @numero.setter
    def numero(self, endereco: str):
        if not endereco or not str(endereco).strip():
            raise ValueError("O número do quarto não pode ser vazio.")
        self.__numero = str(endereco).strip()

    # ==== capacidade de hospedes ====
    @property
    def capacidade(self):
        return self.__capacidade

    @capacidade.setter
    def capacidade(self, quantidade: int):
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValueError("A capacidade do quarto deve ser um número inteiro positivo.")
        self.__capacidade = quantidade

    # ==== diária do quarto ====
    @property
    def diaria(self):
        return self.__diaria

    @diaria.setter
    def diaria(self, valor: float):
        if not isinstance(valor, (int, float)) or valor <= 0:
            raise ValueError("O valor da diária deve ser um número positivo.")
        self.__diaria = float(valor)

    # ==== status do quarto ====
    @property
    def status(self):
        return self.__status

    @status.setter
    def status(self, situacao: str):
        if situacao not in self.STATUS_VALIDOS:
            raise ValueError(
                f"Status inválido: {situacao!r}. Use um de {self.STATUS_VALIDOS}"
            )
        self.__status = situacao

    # ==== bloqueios do quarto ====
    @property
    def bloqueios(self):
        return self.__bloqueios

    @bloqueios.setter
    def bloqueios(self, lista: list):
        if not isinstance(lista, list):
            raise TypeError("bloqueios deve ser uma lista.")
        self.__bloqueios = lista

    # ==== observações do quarto ====
    @property
    def observacoes(self):
        return self.__observacoes

    @observacoes.setter
    def observacoes(self, obs: str):
        if not isinstance(obs, str):
            raise ValueError("As observações devem ser uma string.")
        self.__observacoes = obs.strip()

    # ============================ métodos especiais ==============================
    def __str__(self) -> str:                   # Representação do quarto em string
        return f"Quarto {self.numero} ({self.status}) - R$ {self.diaria:.2f}/noite"

    def __lt__(self, outro: "Quarto"):          # Permite a comparação de quartos pela diária
        if not isinstance(outro, Quarto):
            return NotImplemented
        return self.diaria < outro.diaria

    def __repr__(self) -> str:                  # Representação do quarto para rastreio.
        return (
            f"Quarto(numero={self.numero!r}, capacidade={self.capacidade}, "
            f"diaria={self.diaria}, status={self.status!r})"
        )

    def __eq__(self, outro: object) -> bool:    # Compara se dois quartos são iguais pelo número.
        if not isinstance(outro, Quarto):
            return NotImplemented
        return self.numero == outro.numero

    def __hash__(self) -> int:                  # Retorna o hash do quarto baseado no número.
        return hash(self.numero)


class Simples(Quarto):
    pass


class Duplo(Quarto):
    pass


class Luxo(Quarto):
    pass
