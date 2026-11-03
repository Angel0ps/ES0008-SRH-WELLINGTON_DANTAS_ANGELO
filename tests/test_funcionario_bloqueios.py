from datetime import date

import pytest

from app.database.repositorio import Repositorio
from app.models.pessoas import Funcionario
from app.models.quartos import Simples
from app.models.registros import Bloqueio
from app.services.reservas import ServicoReservas


def test_funcionario_persistido_e_recuperado(tmp_path):
    caminho = tmp_path / "funcionarios.db"
    repo = Repositorio(caminho)
    funcionario = Funcionario(
        id="f1", nome="João Lima", documento="12345678901",
        email="joao@example.com", telefone="88999998888",
        cargo="Recepcionista",
    )
    repo.salvar_funcionario(funcionario)
    repo.fechar()

    reaberto = Repositorio(caminho)
    recuperado = reaberto.obter_funcionario("f1")
    assert recuperado.nome == "João Lima"
    assert recuperado.cargo == "Recepcionista"
    assert reaberto.listar_funcionarios()[0].id == "f1"
    reaberto.fechar()


def test_bloqueio_intervalo_persistido_no_sqlite(tmp_path):
    caminho = tmp_path / "bloqueios.db"
    repo = Repositorio(caminho)
    repo.salvar_quarto(Simples(numero="101", capacidade=2, diaria=100))
    repo.salvar_bloqueio(Bloqueio(
        id="b1", quarto_relacionado="101", data=date(2026, 12, 10),
        data_fim=date(2026, 12, 12), tipo="manutencao", status="ativo",
        motivo="Reparo hidráulico",
    ))
    repo.fechar()

    reaberto = Repositorio(caminho)
    bloqueio = reaberto.obter_bloqueio("b1")
    assert bloqueio.data == date(2026, 12, 10)
    assert bloqueio.data_fim == date(2026, 12, 12)
    assert bloqueio.motivo == "Reparo hidráulico"
    assert reaberto.obter_quarto("101").bloqueios[0].id == "b1"
    reaberto.fechar()


def test_bloqueio_rejeita_data_final_anterior():
    with pytest.raises(ValueError, match="não pode anteceder"):
        Bloqueio(
            id="b1", quarto_relacionado="101", data=date(2026, 12, 12),
            data_fim=date(2026, 12, 10), tipo="manutencao", status="ativo",
        )


def test_bloqueio_impede_reserva_sobreposta_mas_nao_fora_do_periodo():
    repo = Repositorio(":memory:")
    try:
        repo.salvar_quarto(Simples(numero="101", capacidade=2, diaria=100))
        from app.models.pessoas import Hospede
        repo.salvar_hospede(Hospede(
            id="h1", nome="Ana Souza", documento="12345678901",
            email="ana@example.com", telefone="88999998888",
        ))
        repo.salvar_bloqueio(Bloqueio(
            id="b1", quarto_relacionado="101", data=date(2026, 12, 10),
            data_fim=date(2026, 12, 12), tipo="manutencao", status="ativo",
        ))
        servico = ServicoReservas(repo)
        with pytest.raises(ValueError, match="bloqueado"):
            servico.criar_reserva(
                id="r-bloqueada", numero_quarto="101",
                data_entrada=date(2026, 12, 12), data_saida=date(2026, 12, 14),
                hospedes_ids=["h1"], qtd_hospedes=1,
            )
        reserva = servico.criar_reserva(
            id="r-livre", numero_quarto="101",
            data_entrada=date(2026, 12, 13), data_saida=date(2026, 12, 15),
            hospedes_ids=["h1"], qtd_hospedes=1,
        )
        assert reserva.id == "r-livre"
    finally:
        repo.fechar()


def test_migracao_de_pagamentos_e_bloqueios_legados(tmp_path):
    import sqlite3

    caminho = tmp_path / "banco_legado.db"
    conexao = sqlite3.connect(caminho)
    conexao.executescript(
        """
        CREATE TABLE pagamentos (
            id TEXT PRIMARY KEY, reserva_id TEXT NOT NULL, valor REAL NOT NULL,
            data_pagamento TEXT NOT NULL, forma TEXT NOT NULL DEFAULT 'Não informado',
            metodo TEXT NOT NULL DEFAULT 'Não informado'
        );
        CREATE TABLE bloqueios (
            id TEXT PRIMARY KEY, quarto_numero TEXT NOT NULL,
            data_bloqueio TEXT NOT NULL, tipo TEXT NOT NULL, status TEXT NOT NULL
        );
        INSERT INTO bloqueios VALUES
            ('b-legado', '101', '2026-12-10', 'manutencao', 'ativo');
        """
    )
    conexao.commit()
    conexao.close()

    repo = Repositorio(caminho)
    try:
        bloqueio = repo.obter_bloqueio("b-legado")
        assert bloqueio.data_fim == date(2026, 12, 10)
        assert bloqueio.motivo == ""
        colunas_pagamento = {
            linha["name"] for linha in repo.conn.execute("PRAGMA table_info(pagamentos)")
        }
        assert "categoria" in colunas_pagamento
        tabelas = {
            linha["name"] for linha in repo.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert "funcionarios" in tabelas
    finally:
        repo.fechar()


def test_seed_cria_sete_quartos_sem_duplicar(tmp_path):
    from app.database.seed import executar_seed
    caminho = str(tmp_path / "seed.db")
    assert executar_seed(caminho) == 7
    assert executar_seed(caminho) == 0
    repo = Repositorio(caminho)
    try:
        assert len(repo.listar_quartos()) == 7
    finally:
        repo.fechar()


def test_migracao_reserva_legada_adiciona_origem_padrao(tmp_path):
    import sqlite3
    caminho = tmp_path / "reservas_legado.db"
    conexao = sqlite3.connect(caminho)
    conexao.executescript("""
        CREATE TABLE quartos (
            numero TEXT PRIMARY KEY, capacidade INTEGER NOT NULL,
            diaria REAL NOT NULL, status TEXT NOT NULL
        );
        CREATE TABLE hospedes (
            id TEXT PRIMARY KEY, nome TEXT NOT NULL
        );
        CREATE TABLE reservas (
            id TEXT PRIMARY KEY, quarto_numero TEXT NOT NULL,
            data_reserva TEXT NOT NULL, data_entrada TEXT NOT NULL,
            data_saida TEXT NOT NULL, qtd_hospedes INTEGER NOT NULL,
            status TEXT NOT NULL, tipo TEXT NOT NULL, hospede_id TEXT
        );
        INSERT INTO quartos VALUES ('101', 2, 100, 'disponivel');
        INSERT INTO hospedes VALUES ('h1', 'Ana');
        INSERT INTO reservas VALUES (
            'r1', '101', '2026-10-01', '2026-12-10', '2026-12-12',
            1, 'Confirmada', 'reserva', 'h1'
        );
    """)
    conexao.commit()
    conexao.close()
    repo = Repositorio(caminho)
    try:
        reserva = repo.obter_reserva("r1")
        assert reserva.origem == "balcao"
        assert "origem" in {
            c["name"] for c in repo.conn.execute("PRAGMA table_info(reservas)")
        }
    finally:
        repo.fechar()
