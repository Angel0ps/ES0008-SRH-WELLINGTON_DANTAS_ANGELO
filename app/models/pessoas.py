# ==================================================== Super Classe Pessoa ====================================================
class Pessoa: # Concentra os dados comuns (nome, documento, email, telefone, id).

    def __init__(
            self,
            id: str, 
            nome: str, 
            documento: str, 
            email: str, 
            telefone: str
            ):
        
        if type(self) is Pessoa:
            raise TypeError(
                "Pessoa é abstrata e não pode ser instanciada diretamente.\n Use Hospede ou Funcionario."
            )
        self.__id = id
        self.__nome = nome
        self.__documento = documento
        self.__email = email
        self.__telefone = telefone

    # =========== id ============
    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, valor: str) -> None:
        if not valor or not str(valor).strip():
            raise ValueError("id não pode ser vazio")
        self.__id = str(valor).strip()

    # ========== nome =============
    @property
    def nome(self):
        return self.__nome

    @nome.setter
    def nome(self, valor: str) -> None:
        if not valor or not valor.strip():
            raise ValueError("Nome não pode ser vazio")
        self.__nome = valor.strip()

    # ========== documento ============
    @property
    def documento(self):
        return self.__documento

    @documento.setter
    def documento(self, valor: str) -> None:
        digitos = "".join(c for c in str(valor) if c.isdigit())
        if len(digitos) not in (11, 14):  # CPF ou CNPJ
            raise ValueError("Documento deve ter 11 (CPF) ou 14 (CNPJ) dígitos")
        self.__documento = digitos

    # =========== email ==============             
    @property
    def email(self):
        return self.__email

    @email.setter
    def email(self, valor: str) -> None:
        valor = str(valor).strip()
        usuario, _, dominio = valor.partition("@")
        if not usuario or "." not in dominio or dominio.startswith(".") or dominio.endswith("."):
            raise ValueError(f"E-mail inválido: {valor!r}")
        self.__email = valor

    # ========== telefone ============
    @property
    def telefone(self):
        return self.__telefone

    @telefone.setter
    def telefone(self, valor: str) -> None:
        digitos = "".join(c for c in str(valor) if c.isdigit())
        if len(digitos) < 10:
            raise ValueError("Telefone deve ter ao menos 10 dígitos (DDD + número)")
        self.__telefone = digitos

    # =========== métodos especiais ============
    def __str__(self):
        return f"{self.nome} ({self.documento})"

    def __repr__(self):
        return (
            f"{type(self).__name__}(nome={self.nome!r},\n documento={self.documento!r})"
        )

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Pessoa):
            return NotImplemented
        return self.documento == outro.documento

    def __hash__(self):
        return hash(self.documento)

# ========================================================== subclasse Hospede ===========================================================        
class Hospede(Pessoa):

    def __init__(
        self,
        id: str,
        nome: str,
        documento: str,
        email: str,
        telefone: str,
        observacoes: str = "",
        acessibilidade: bool = False
    ):
        super().__init__(
            id,
            nome,
            documento,
            email,
            telefone
        )

        self.observacoes = observacoes
        self.acessibilidade = acessibilidade

    # ========== observacoes ==========
    @property
    def observacoes(self) -> str:
        return self.__observacoes

    @observacoes.setter
    def observacoes(self, valor: str) -> None:
        self.__observacoes = str(valor).strip()

    # ========== acessibilidade ==========
    @property
    def acessibilidade(self) -> bool:
        return self.__acessibilidade

    @acessibilidade.setter
    def acessibilidade(self, valor: bool) -> None:
        if not isinstance(valor, bool):
            raise TypeError("Acessibilidade deve ser True ou False")

        self.__acessibilidade = valor

    # ========== métodos do hóspede ==========
    def gerenciarHospedes(self) -> str:
        """Representa a operação de gerenciamento do hóspede (placeholder)."""
        return f"Gerenciando hóspede: {self.nome}"

    def requisitarHospede(self) -> str:
        """Representa a operação de consulta dos dados do hóspede."""
        return f"Requisitando dados do hóspede: {self.nome}"

    def solicitarServico(self, servico: str) -> str:

        if not servico or not servico.strip():
            raise ValueError("O serviço não pode ser vazio")

        return f"Hóspede {self.nome} solicitou: {servico.strip()}"

    def atualizarObservacoes(self, novas_observacoes: str) -> str:

        self.observacoes = novas_observacoes

        return (f"Observações do hóspede {self.nome} atualizadas com sucesso.")

    # ========== métodos especiais ==========
    def __str__(self) -> str:
        acess = " (acessibilidade)" if self.acessibilidade else ""
        return f"Hóspede: {self.nome} ({self.documento}){acess}"

# ================================= Subclasse Funcionário ===============================

class Funcionario(Pessoa):
    """Colaborador do hotel identificado por um cargo."""

    def __init__(self, id, nome, documento, email, telefone, cargo: str):
        super().__init__(id, nome, documento, email, telefone)
        self.cargo = cargo

    # ========== cargo ==========
    @property
    def cargo(self) -> str:
        return self.__cargo

    @cargo.setter
    def cargo(self, valor: str) -> None:
        if not valor or not str(valor).strip():
            raise ValueError("Cargo não pode ser vazio")
        self.__cargo = str(valor).strip()

    def __str__(self) -> str:
        return f"Funcionário: {self.nome} ({self.cargo})"
