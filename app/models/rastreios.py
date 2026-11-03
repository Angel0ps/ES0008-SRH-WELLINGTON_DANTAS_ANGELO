"""Responsabilidade de auditoria e rastreabilidade dos modelos do SRH.

A classe mantém os metadados e o histórico em memória. O Repositorio é
responsável por persistir e restaurar esses dados no SQLite.
"""

from datetime import date
from uuid import uuid4


# ==================================================== Classe Rastreabilidade ====================================================

class Rastreabilidade:
    """
    Registra a criação e as alterações realizadas em um objeto.
    Os metadados e eventos são mantidos no objeto; o Repositorio
    persiste e restaura essas informações no SQLite.
    Resolve meu problema de herança múltipla.
    """

    def __init__(self, criado_por: str = "sistema"):
        self.criado_em = date.today()
        self.editado_em = None
        self.criado_por = criado_por
        self.editado_por = None
        self.__historico = []

        self.rastrearCriacao()

    # ================= criado_em =====================

    @property
    def criado_em(self):
        return self.__criado_em

    @criado_em.setter
    def criado_em(self, valor: date):
        if not isinstance(valor, date):
            raise ValueError("Data de criação deve ser do tipo date")

        self.__criado_em = valor

    # ================= editado_em =====================

    @property
    def editado_em(self):
        return self.__editado_em

    @editado_em.setter
    def editado_em(self, valor: date | None):
        if valor is not None and not isinstance(valor, date):
            raise ValueError("Data de edição deve ser do tipo date")

        self.__editado_em = valor

    # ================= criado_por =====================

    @property
    def criado_por(self):
        return self.__criado_por

    @criado_por.setter
    def criado_por(self, valor: str):
        if not valor or not str(valor).strip():
            raise ValueError("Responsável pela criação não pode ser vazio")

        self.__criado_por = str(valor).strip()

    # ================= editado_por =====================

    @property
    def editado_por(self):
        return self.__editado_por

    @editado_por.setter
    def editado_por(self, valor: str | None):
        if valor is not None and not str(valor).strip():
            raise ValueError("Responsável pela edição não pode ser vazio")

        self.__editado_por = (
            str(valor).strip() if valor is not None else None
        )

    # ================= histórico =====================

    @property
    def historico(self):
        # Retorna cópias para impedir alterações externas no histórico.
        return [evento.copy() for evento in self.__historico]

    # ================= registrar evento =====================

    def registrar_evento(
        self,
        acao: str,
        responsavel: str,
        descricao: str = ""
    ):
        if not acao or not str(acao).strip():
            raise ValueError("Ação não pode ser vazia")

        if not responsavel or not str(responsavel).strip():
            raise ValueError("Responsável não pode ser vazio")

        evento = {
            "id": str(uuid4()),
            "acao": str(acao).strip(),
            "data": date.today(),
            "responsavel": str(responsavel).strip(),
            "descricao": str(descricao).strip()
        }

        self.__historico.append(evento)

        return evento.copy()

    def carregar_rastreabilidade(
        self,
        criado_em: date,
        editado_em: date | None,
        criado_por: str,
        editado_por: str | None,
        historico: list
    ):
        """Restaura do SQLite os metadados e eventos já persistidos."""
        self.criado_em = criado_em
        self.editado_em = editado_em
        self.criado_por = criado_por
        self.editado_por = editado_por
        self.__historico = [evento.copy() for evento in historico]

    # ================= rastrear criação =====================

    def rastrearCriacao(self):
        return self.registrar_evento(
            acao="criacao",
            responsavel=self.criado_por,
            descricao="Registro criado."
        )

    # ================= rastrear edição =====================

    def rastrearEdicao(
        self,
        editado_por: str = "sistema",
        descricao: str = "Registro atualizado."
    ):
        self.editado_em = date.today()
        self.editado_por = editado_por

        return self.registrar_evento(
            acao="edicao",
            responsavel=editado_por,
            descricao=descricao
        )


