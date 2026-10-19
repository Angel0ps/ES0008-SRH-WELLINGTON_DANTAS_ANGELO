
import sqlite3
from pathlib import Path

# Caminho do banco de dados
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "srh_wda.db"


def conectar():
    """Abre uma conexão com o banco de dados."""
    conexao = sqlite3.connect(DB_PATH)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas():
    """Cria as tabelas necessárias para o sistema."""

    with conectar() as conexao:
        conexao.executescript("""
            CREATE TABLE IF NOT EXISTS hospedes (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quartos (
                numero TEXT PRIMARY KEY,
                capacidade INTEGER NOT NULL,
                diaria REAL NOT NULL,
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reservas (
                id TEXT PRIMARY KEY,
                hospede_id TEXT NOT NULL,
                quarto_numero TEXT NOT NULL,
                data_reserva TEXT NOT NULL,
                data_entrada TEXT NOT NULL,
                data_saida TEXT NOT NULL,
                qtd_hospedes INTEGER NOT NULL,
                status TEXT NOT NULL,

                FOREIGN KEY (hospede_id) REFERENCES hospedes(id),
                FOREIGN KEY (quarto_numero) REFERENCES quartos(numero),

                CHECK (data_saida > data_entrada),
                CHECK (qtd_hospedes > 0)
            );

            CREATE TABLE IF NOT EXISTS pagamentos (
                id TEXT PRIMARY KEY,
                reserva_id TEXT NOT NULL,
                valor REAL NOT NULL,
                data_pagamento TEXT NOT NULL,
                metodo TEXT NOT NULL,

                FOREIGN KEY (reserva_id) REFERENCES reservas(id),
                CHECK (valor > 0)
            );

            CREATE TABLE IF NOT EXISTS adicionais (
                id TEXT PRIMARY KEY,
                reserva_id TEXT NOT NULL,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                data_lancamento TEXT NOT NULL,

                FOREIGN KEY (reserva_id) REFERENCES reservas(id),
                CHECK (valor >= 0)
            );
        """)


if __name__ == "__main__":
    criar_tabelas()
    print("Banco de dados inicializado.")

