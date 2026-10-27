from datetime import date, timedelta

# ==================================================== Serviço de Tarifa ====================================================
class Tarifa:
    """Calcula o valor da diária de um quarto.

    Regras (acumulativas, aplicadas sobre a diária base):
    - fim de semana (pernoites de sexta e sábado): +30% por padrão;
    - temporada alta (dez, jan, fev e jul): +50% por padrão;
    - desconto: aplicado sobre o TOTAL da estadia (aplicar_desconto).
    """

    MESES_TEMPORADA_ALTA = (12, 1, 2, 7)          # férias de verão + julho
    DIAS_FIM_DE_SEMANA = (4, 5)                   # weekday(): 4 = sexta, 5 = sábado (noites de fds)

    ACRESCIMO_FDS_PADRAO = 0.30
    ACRESCIMO_TEMPORADA_PADRAO = 0.50

    def __init__(
        self,
        diaria_base: float,
        acrescimo_fds: float = ACRESCIMO_FDS_PADRAO,
        acrescimo_temporada: float = ACRESCIMO_TEMPORADA_PADRAO
    ):
        self.diaria_base = diaria_base
        self.acrescimo_fds = acrescimo_fds
        self.acrescimo_temporada = acrescimo_temporada

    # ========== diária base ==========
    @property
    def diaria_base(self) -> float:
        return self.__diaria_base

    @diaria_base.setter
    def diaria_base(self, valor: float) -> None:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor <= 0:
            raise ValueError("A diária base deve ser um número maior que zero")

        self.__diaria_base = float(valor)

    # ========== acréscimo fim de semana ==========
    @property
    def acrescimo_fds(self) -> float:
        return self.__acrescimo_fds

    @acrescimo_fds.setter
    def acrescimo_fds(self, valor: float) -> None:
        self.__acrescimo_fds = self.__valida_percentual(valor, "acréscimo de fim de semana")

    # ========== acréscimo temporada ==========
    @property
    def acrescimo_temporada(self) -> float:
        return self.__acrescimo_temporada

    @acrescimo_temporada.setter
    def acrescimo_temporada(self, valor: float) -> None:
        self.__acrescimo_temporada = self.__valida_percentual(valor, "acréscimo de temporada")

    @staticmethod
    def __valida_percentual(valor: float, nome: str) -> float:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0 <= valor <= 1:
            raise ValueError(f"O {nome} deve ser um percentual entre 0 e 1")

        return float(valor)

    # ========== regras de calendário ==========
    def eh_fim_de_semana(self, data: date) -> bool:
        """Sexta e sábado são noites de fim de semana."""
        return data.weekday() in self.DIAS_FIM_DE_SEMANA

    def eh_temporada_alta(self, data: date) -> bool:
        """Dezembro, janeiro, fevereiro e julho são temporada alta."""
        return data.month in self.MESES_TEMPORADA_ALTA

    # ========== cálculos ==========
    def calcular_diaria(self, data: date) -> float:
        """Diária de UMA noite (a noite de 'data' até 'data + 1 dia')."""
        if not isinstance(data, date):
            raise ValueError("Data deve ser um objeto do tipo date")

        valor = self.diaria_base

        if self.eh_fim_de_semana(data):
            valor *= 1 + self.acrescimo_fds

        if self.eh_temporada_alta(data):
            valor *= 1 + self.acrescimo_temporada

        return valor

    def calcular_total(self, data_entrada: date, data_saida: date) -> float:
        """Soma da diária de cada noite do intervalo semiaberto [entrada, saida)."""
        if not isinstance(data_entrada, date) or not isinstance(data_saida, date):
            raise ValueError("Datas devem ser objetos do tipo date")

        if data_saida <= data_entrada:
            raise ValueError("Data de saída deve ser posterior à data de entrada")

        total = 0.0
        dia = data_entrada

        while dia < data_saida:
            total += self.calcular_diaria(dia)
            dia += timedelta(days=1)

        return total

    def aplicar_desconto(self, total: float, percentual: float) -> float:
        """Aplica um desconto sobre o total da estadia."""
        if isinstance(total, bool) or not isinstance(total, (int, float)) or total < 0:
            raise ValueError("O total deve ser um número não negativo")

        percentual = self.__valida_percentual(percentual, "desconto")

        return total * (1 - percentual)