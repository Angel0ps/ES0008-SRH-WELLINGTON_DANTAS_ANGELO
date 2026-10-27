"""Repositório SQLite do Sistema de Reservas de Hotel.

Responsabilidades:
- criar/garantir o esquema do banco;
- converter linhas SQLite em objetos de domínio;
- persistir quartos, hóspedes, reservas, pagamentos e adicionais.

Uso:
    repo = Repositorio("srh_wda.db")
    ...
    repo.fechar()

A conexão é persistente e protegida por RLock, o que permite reutilizá-la
com ThreadingHTTPServer e também permite testes com banco ":memory:".
"""

import sqlite3
import threading
from datetime import date
from pathlib import Path

from app.models.quartos import Simples, Duplo, Luxo
from app.models.pessoas import Hospede
from app.models.registros import Reserva, Pagamento, Adicional

# Caminho do banco de dados
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "srh_wda.db"

def conectar():
    """Abre uma conexão com o banco de dados."""
    conexao = sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao

TIPOS_QUARTO = {
    "Simples": Simples,
    "Duplo": Duplo,
    "Luxo": Luxo,
}


class Repositorio:
    """Camada de persistência do SRH."""

    def __init__(self, caminho_db: str | Path = "srh_wda.db"):
        self.caminho_db = str(caminho_db)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(
            self.caminho_db,
            check_same_thread=False,
            timeout=30,
        )
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._criar_tabelas()

    def _criar_tabelas(self) -> None:
        """Cria o esquema necessário sem apagar dados existentes."""
        with self._lock, self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS quartos (
                    numero TEXT PRIMARY KEY,
                    tipo TEXT NOT NULL DEFAULT 'Simples',
                    capacidade INTEGER NOT NULL CHECK (capacidade > 0),
                    diaria REAL NOT NULL CHECK (diaria > 0),
                    status TEXT NOT NULL DEFAULT 'disponivel',
                    observacoes TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS hospedes (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    documento TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    telefone TEXT NOT NULL DEFAULT '',
                    observacoes TEXT NOT NULL DEFAULT '',
                    acessibilidade INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS reservas (
                    id TEXT PRIMARY KEY,
                    quarto_numero TEXT NOT NULL,
                    data_reserva TEXT NOT NULL,
                    data_entrada TEXT NOT NULL,
                    data_saida TEXT NOT NULL,
                    qtd_hospedes INTEGER NOT NULL CHECK (qtd_hospedes > 0),
                    status TEXT NOT NULL,
                    tipo TEXT NOT NULL DEFAULT 'reserva',
                    hospede_id TEXT,
                    FOREIGN KEY (quarto_numero) REFERENCES quartos(numero),
                    FOREIGN KEY (hospede_id) REFERENCES hospedes(id),
                    CHECK (data_saida > data_entrada)
                );

                CREATE TABLE IF NOT EXISTS reserva_hospedes (
                    reserva_id TEXT NOT NULL,
                    hospede_id TEXT NOT NULL,
                    PRIMARY KEY (reserva_id, hospede_id),
                    FOREIGN KEY (reserva_id) REFERENCES reservas(id) ON DELETE CASCADE,
                    FOREIGN KEY (hospede_id) REFERENCES hospedes(id)
                );

                CREATE TABLE IF NOT EXISTS pagamentos (
                    id TEXT PRIMARY KEY,
                    reserva_id TEXT NOT NULL,
                    valor REAL NOT NULL CHECK (valor > 0),
                    data_pagamento TEXT NOT NULL,
                    forma TEXT NOT NULL DEFAULT 'Não informado',
                    metodo TEXT NOT NULL DEFAULT 'Não informado',
                    FOREIGN KEY (reserva_id) REFERENCES reservas(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS adicionais (
                    id TEXT PRIMARY KEY,
                    reserva_id TEXT NOT NULL,
                    descricao TEXT NOT NULL,
                    valor REAL NOT NULL CHECK (valor >= 0),
                    data_lancamento TEXT NOT NULL,
                    FOREIGN KEY (reserva_id) REFERENCES reservas(id) ON DELETE CASCADE
                );
                """
            )
            # Migração simples para bancos criados por versões anteriores.
            self._adicionar_coluna_se_ausente("quartos", "tipo", "TEXT NOT NULL DEFAULT 'Simples'")
            self._adicionar_coluna_se_ausente("quartos", "observacoes", "TEXT NOT NULL DEFAULT ''")
            self._adicionar_coluna_se_ausente("hospedes", "documento", "TEXT NOT NULL DEFAULT ''")
            self._adicionar_coluna_se_ausente("hospedes", "email", "TEXT NOT NULL DEFAULT ''")
            self._adicionar_coluna_se_ausente("hospedes", "telefone", "TEXT NOT NULL DEFAULT ''")
            self._adicionar_coluna_se_ausente("hospedes", "observacoes", "TEXT NOT NULL DEFAULT ''")
            self._adicionar_coluna_se_ausente("hospedes", "acessibilidade", "INTEGER NOT NULL DEFAULT 0")
            self._adicionar_coluna_se_ausente("reservas", "tipo", "TEXT NOT NULL DEFAULT 'reserva'")
            self._adicionar_coluna_se_ausente("reservas", "hospede_id", "TEXT")
            self._adicionar_coluna_se_ausente("pagamentos", "forma", "TEXT NOT NULL DEFAULT 'Não informado'")
            self._adicionar_coluna_se_ausente("pagamentos", "metodo", "TEXT NOT NULL DEFAULT 'Não informado'")
            # Mantém o valor legado disponível após a migração.
            self.conn.execute(
                "UPDATE pagamentos SET forma = metodo WHERE forma = 'Não informado' AND metodo != 'Não informado'"
            )
            self.conn.execute(
                "UPDATE pagamentos SET metodo = forma WHERE metodo = 'Não informado' AND forma != 'Não informado'"
            )

            # Copia relacionamento legado singular para a tabela associativa.
            self.conn.execute(
                """
                INSERT OR IGNORE INTO reserva_hospedes (reserva_id, hospede_id)
                SELECT id, hospede_id FROM reservas WHERE hospede_id IS NOT NULL
                """
            )

    def _adicionar_coluna_se_ausente(
        self, tabela: str, coluna: str, definicao: str
    ) -> None:
        colunas = {
            linha["name"]
            for linha in self.conn.execute(f"PRAGMA table_info({tabela})").fetchall()
        }
        if coluna not in colunas:
            self.conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")

    @staticmethod
    def _data(valor) -> date:
        if isinstance(valor, date):
            return valor
        return date.fromisoformat(str(valor))

    # ------------------------------ quartos ------------------------------
    def salvar_quarto(self, quarto) -> None:
        with self._lock, self.conn:
            self.conn.execute(
                """
                INSERT INTO quartos (numero, tipo, capacidade, diaria, status, observacoes)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(numero) DO UPDATE SET
                    tipo=excluded.tipo,
                    capacidade=excluded.capacidade,
                    diaria=excluded.diaria,
                    status=excluded.status,
                    observacoes=excluded.observacoes
                """,
                (
                    str(quarto.numero),
                    type(quarto).__name__,
                    quarto.capacidade,
                    quarto.diaria,
                    quarto.status,
                    getattr(quarto, "observacoes", ""),
                ),
            )

    def obter_quarto(self, numero: str):
        with self._lock:
            linha = self.conn.execute(
                "SELECT * FROM quartos WHERE numero = ?", (str(numero),)
            ).fetchone()
            return self._quarto_de_linha(linha) if linha else None

    def listar_quartos(self) -> list:
        with self._lock:
            linhas = self.conn.execute(
                "SELECT * FROM quartos ORDER BY numero"
            ).fetchall()
            return [self._quarto_de_linha(linha) for linha in linhas]

    @staticmethod
    def _quarto_de_linha(linha):
        classe = TIPOS_QUARTO.get(linha["tipo"], Simples)
        return classe(
            numero=linha["numero"],
            capacidade=linha["capacidade"],
            diaria=linha["diaria"],
            status=linha["status"],
            observacoes=linha["observacoes"],
        )

    # ------------------------------ hóspedes -----------------------------
    def salvar_hospede(self, hospede) -> None:
        with self._lock, self.conn:
            self.conn.execute(
                """
                INSERT INTO hospedes
                    (id, nome, documento, email, telefone, observacoes, acessibilidade)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    nome=excluded.nome,
                    documento=excluded.documento,
                    email=excluded.email,
                    telefone=excluded.telefone,
                    observacoes=excluded.observacoes,
                    acessibilidade=excluded.acessibilidade
                """,
                (
                    hospede.id,
                    hospede.nome,
                    getattr(hospede, "documento", ""),
                    getattr(hospede, "email", ""),
                    getattr(hospede, "telefone", ""),
                    getattr(hospede, "observacoes", ""),
                    int(bool(getattr(hospede, "acessibilidade", False))),
                ),
            )

    def obter_hospede(self, hospede_id: str):
        with self._lock:
            linha = self.conn.execute(
                "SELECT * FROM hospedes WHERE id = ?", (str(hospede_id),)
            ).fetchone()
            return self._hospede_de_linha(linha) if linha else None

    def listar_hospedes(self) -> list:
        with self._lock:
            linhas = self.conn.execute(
                "SELECT * FROM hospedes ORDER BY nome"
            ).fetchall()
            return [self._hospede_de_linha(linha) for linha in linhas]

    @staticmethod
    def _hospede_de_linha(linha):
        return Hospede(
            id=linha["id"],
            nome=linha["nome"],
            documento=linha["documento"],
            email=linha["email"],
            telefone=linha["telefone"],
            observacoes=linha["observacoes"],
            acessibilidade=bool(linha["acessibilidade"]),
        )

    # ------------------------------ reservas -----------------------------
    def salvar_reserva(self, reserva) -> None:
        hospedes_ids = list(
            getattr(reserva, "hospedes_ids", [])
            or ([reserva.hospede_id] if getattr(reserva, "hospede_id", None) else [])
        )
        hospede_principal = hospedes_ids[0] if hospedes_ids else getattr(reserva, "hospede_id", None)

        with self._lock, self.conn:
            self.conn.execute(
                """
                INSERT INTO reservas
                    (id, quarto_numero, data_reserva, data_entrada, data_saida,
                     qtd_hospedes, status, tipo, hospede_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    quarto_numero=excluded.quarto_numero,
                    data_reserva=excluded.data_reserva,
                    data_entrada=excluded.data_entrada,
                    data_saida=excluded.data_saida,
                    qtd_hospedes=excluded.qtd_hospedes,
                    status=excluded.status,
                    tipo=excluded.tipo,
                    hospede_id=excluded.hospede_id
                """,
                (
                    reserva.id,
                    reserva.quarto_relacionado,
                    self._data(reserva.data).isoformat(),
                    self._data(reserva.data_entrada).isoformat(),
                    self._data(reserva.data_saida).isoformat(),
                    reserva.qtd_hospedes,
                    reserva.status,
                    getattr(reserva, "tipo", "reserva"),
                    hospede_principal,
                ),
            )

            self.conn.execute(
                "DELETE FROM reserva_hospedes WHERE reserva_id = ?", (reserva.id,)
            )
            for hospede_id in hospedes_ids:
                self.conn.execute(
                    "INSERT OR IGNORE INTO reserva_hospedes (reserva_id, hospede_id) VALUES (?, ?)",
                    (reserva.id, hospede_id),
                )

            self.conn.execute("DELETE FROM pagamentos WHERE reserva_id = ?", (reserva.id,))
            for pagamento in getattr(reserva, "pagamentos", []):
                self._salvar_pagamento_no_contexto(reserva.id, pagamento)

            self.conn.execute("DELETE FROM adicionais WHERE reserva_id = ?", (reserva.id,))
            for adicional in getattr(reserva, "adicionais", []):
                self._salvar_adicional_no_contexto(reserva.id, adicional)

    def obter_reserva(self, reserva_id: str):
        with self._lock:
            linha = self.conn.execute(
                "SELECT * FROM reservas WHERE id = ?", (str(reserva_id),)
            ).fetchone()
            return self._reserva_de_linha(linha) if linha else None

    def listar_reservas(self) -> list:
        with self._lock:
            linhas = self.conn.execute(
                "SELECT * FROM reservas ORDER BY data_entrada, id"
            ).fetchall()
            return [self._reserva_de_linha(linha) for linha in linhas]

    def _reserva_de_linha(self, linha):
        hospedes = self.conn.execute(
            "SELECT hospede_id FROM reserva_hospedes WHERE reserva_id = ? ORDER BY hospede_id",
            (linha["id"],),
        ).fetchall()
        hospedes_ids = [item["hospede_id"] for item in hospedes]
        if not hospedes_ids and linha["hospede_id"]:
            hospedes_ids = [linha["hospede_id"]]

        pagamentos_linhas = self.conn.execute(
            "SELECT * FROM pagamentos WHERE reserva_id = ? ORDER BY data_pagamento, id",
            (linha["id"],),
        ).fetchall()
        adicionais_linhas = self.conn.execute(
            "SELECT * FROM adicionais WHERE reserva_id = ? ORDER BY data_lancamento, id",
            (linha["id"],),
        ).fetchall()

        pagamentos = [
            self._pagamento_de_linha(item) for item in pagamentos_linhas
        ]
        adicionais = [
            self._adicional_de_linha(item) for item in adicionais_linhas
        ]

        reserva = Reserva(
            id=linha["id"],
            quarto_relacionado=linha["quarto_numero"],
            data=self._data(linha["data_reserva"]),
            tipo=linha["tipo"],
            status=linha["status"],
            data_entrada=self._data(linha["data_entrada"]),
            data_saida=self._data(linha["data_saida"]),
            qtd_hospedes=linha["qtd_hospedes"],
            adicionais=adicionais,
            pagamentos=pagamentos,
            hospede_id=linha["hospede_id"],
        )
        # O modelo atual pode ainda não declarar hospedes_ids; a API precisa
        # desse atributo para representar reservas com vários hóspedes.
        reserva.hospedes_ids = hospedes_ids
        return reserva

    # ------------------------- pagamentos/adicionais ----------------------
    def _salvar_pagamento_no_contexto(self, reserva_id: str, pagamento) -> None:
        forma = getattr(pagamento, "forma", getattr(pagamento, "metodo", "Não informado"))
        self.conn.execute(
            """
            INSERT INTO pagamentos (id, reserva_id, valor, data_pagamento, forma, metodo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                pagamento.id,
                reserva_id,
                pagamento.valor,
                self._data(pagamento.data).isoformat(),
                forma,
                forma,
            ),
        )

    def _salvar_adicional_no_contexto(self, reserva_id: str, adicional) -> None:
        self.conn.execute(
            """
            INSERT INTO adicionais (id, reserva_id, descricao, valor, data_lancamento)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                adicional.id,
                reserva_id,
                adicional.descricao,
                adicional.valor,
                self._data(getattr(adicional, "data", date.today())).isoformat(),
            ),
        )

    @staticmethod
    def _pagamento_de_linha(linha):
        pagamento = Pagamento(
            id=linha["id"],
            valor=linha["valor"],
            data=Repositorio._data(linha["data_pagamento"]),
            metodo=linha["forma"],
        )
        # Compatibilidade com a API/serviço que chama a forma de pagamento "forma".
        pagamento.forma = linha["forma"]
        pagamento.reserva_id = linha["reserva_id"]
        return pagamento

    @staticmethod
    def _adicional_de_linha(linha):
        adicional = Adicional(
            id=linha["id"],
            descricao=linha["descricao"],
            valor=linha["valor"],
            data=Repositorio._data(linha["data_lancamento"]),
        )
        adicional.reserva_id = linha["reserva_id"]
        return adicional

    # ------------------------------ encerramento -------------------------
    def fechar(self) -> None:
        with self._lock:
            self.conn.close()
