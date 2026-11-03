from datetime import date, timedelta

from app.config import carregar_configuracoes

# ==================================================== Serviço de Tarifa ====================================================
class Tarifa:
    """Calcula o valor da diária de um quarto.

    Regras (acumulativas, aplicadas sobre a diária base):
    - fim de semana (pernoites de sexta e sábado): +30% por padrão;
    - temporadas: multiplicadores e intervalos lidos de settings.json;
    - desconto: aplicado sobre o TOTAL da estadia (aplicar_desconto).
    """

    DIAS_FIM_DE_SEMANA = (4, 5)  # noites de sexta e sábado

    def __init__(
        self,
        diaria_base: float,
        acrescimo_fds: float | None = None,
        acrescimo_temporada: float | None = None,
        configuracoes: dict | None = None,
    ):
        self.configuracoes = configuracoes or carregar_configuracoes()
        self.diaria_base = diaria_base
        self.acrescimo_fds = (
            float(self.configuracoes["tarifas"]["multiplicador_fim_semana"]) - 1
            if acrescimo_fds is None else acrescimo_fds
        )
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
    def acrescimo_temporada(self) -> float | None:
        return self.__acrescimo_temporada

    @acrescimo_temporada.setter
    def acrescimo_temporada(self, valor: float | None) -> None:
        self.__acrescimo_temporada = (
            None if valor is None
            else self.__valida_percentual(valor, "acréscimo de temporada")
        )

    @staticmethod
    def __valida_percentual(valor: float, nome: str) -> float:
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0 <= valor <= 1:
            raise ValueError(f"O {nome} deve ser um percentual entre 0 e 1")

        return float(valor)

    # ========== regras de calendário ==========
    def eh_fim_de_semana(self, data: date) -> bool:
        """Sexta e sábado são noites de fim de semana."""
        return data.weekday() in self.DIAS_FIM_DE_SEMANA

    def temporada_da_data(self, data: date) -> dict | None:
        """Retorna a temporada configurada que contém a data, se houver."""
        for temporada in self.configuracoes["tarifas"].get("temporadas", []):
            inicio = date.fromisoformat(temporada["inicio"])
            fim = date.fromisoformat(temporada["fim"])
            if inicio <= data <= fim:
                return temporada
        return None

    def eh_temporada_alta(self, data: date) -> bool:
        """Indica se a data pertence a uma temporada configurada."""
        return self.temporada_da_data(data) is not None

    # ========== cálculos ==========
    def calcular_diaria(self, data: date) -> float:
        """Diária de UMA noite (a noite de 'data' até 'data + 1 dia')."""
        if not isinstance(data, date):
            raise ValueError("Data deve ser um objeto do tipo date")

        valor = self.diaria_base

        if self.eh_fim_de_semana(data):
            valor *= 1 + self.acrescimo_fds

        temporada = self.temporada_da_data(data)
        if temporada is not None:
            multiplicador = (
                1 + self.acrescimo_temporada
                if self.acrescimo_temporada is not None
                else float(temporada["multiplicador"])
            )
            valor *= multiplicador

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