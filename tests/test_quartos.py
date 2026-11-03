
import pytest

from app.models.quartos import Quarto, Simples, Duplo, Luxo


def test_criar_quarto_valido():
    q = Simples(numero="101", capacidade=2, diaria=150.0)

    assert q.numero == "101"
    assert q.capacidade == 2
    assert q.diaria == 150.0
    assert q.status == "disponivel"


def test_diaria_invalida_levanta_erro():
    with pytest.raises(ValueError):
        Simples(numero="101", capacidade=2, diaria=-10)


def test_capacidade_invalida_levanta_erro():
    with pytest.raises(ValueError):
        Simples(numero="101", capacidade=0, diaria=100)


def test_status_invalido_levanta_erro():
    with pytest.raises(ValueError):
        Simples(
            numero="101",
            capacidade=2,
            diaria=100,
            status="inexistente",
        )


def test_numero_vazio_levanta_erro():
    with pytest.raises(ValueError):
        Simples(numero=" ", capacidade=2, diaria=100)


def test_str_quarto():
    q = Simples(numero="202", capacidade=2, diaria=200.0)

    assert "202" in str(q)
    assert "200.00" in str(q)


def test_lt_quarto_compara_por_diaria():
    barato = Simples(numero="101", capacidade=2, diaria=100)
    caro = Simples(numero="102", capacidade=2, diaria=300)

    assert barato < caro
    assert not (caro < barato)


def test_sorted_lista_de_quartos():
    q1 = Simples(numero="A", capacidade=2, diaria=300)
    q2 = Simples(numero="B", capacidade=2, diaria=100)
    q3 = Simples(numero="C", capacidade=2, diaria=200)

    ordenados = sorted([q1, q2, q3])

    assert [q.numero for q in ordenados] == ["B", "C", "A"]


def test_subclasses_herdam_validacao():
    with pytest.raises(ValueError):
        Simples(numero="S1", capacidade=1, diaria=-5)

    luxo = Luxo(numero="L1", capacidade=4, diaria=500)

    assert luxo.diaria == 500


# ============ Testes de alteração de estado ============

def test_alterar_status_apos_criacao():
    q = Simples(numero="101", capacidade=2, diaria=150.0)

    assert q.status == "disponivel"

    q.status = "ocupado"

    assert q.status == "ocupado"


def test_alterar_diaria_apos_criacao():
    q = Simples(numero="101", capacidade=2, diaria=150.0)

    q.diaria = 180.0

    assert q.diaria == 180.0


def test_alterar_diaria_invalida_apos_criacao_levanta_erro():
    q = Simples(numero="101", capacidade=2, diaria=150.0)

    with pytest.raises(ValueError):
        q.diaria = -10

    assert q.diaria == 150.0


def test_alterar_status_invalido_apos_criacao_levanta_erro():
    q = Simples(numero="101", capacidade=2, diaria=150.0)

    with pytest.raises(ValueError):
        q.status = "inexistente"

    assert q.status == "disponivel"


# ============ Métodos definidos no UML ============

def test_subclasses_implementam_diferencial_e_observacoes():
    simples = Simples(numero="S1", capacidade=1, diaria=100,
                      diferencial="Acomodação econômica",
                      observacoes="Próximo à recepção")
    duplo = Duplo(
        numero="D1", capacidade=2, diaria=180, diferencial="Duas camas"
    )
    luxo = Luxo(numero="L1", capacidade=4, diaria=500, diferencial="Vista panorâmica")

    assert simples.diferenciarSimples() == "Acomodação econômica"
    assert simples.observacoesSimples() == "Próximo à recepção"
    assert duplo.diferenciarDuplo() == "Duas camas"
    assert "duplo" in duplo.observacoesDuplo().lower()
    assert luxo.diferenciarLuxo() == "Vista panorâmica"
    assert "luxo" in luxo.observacoesLuxo().lower()


def test_requisitar_quarto_retorna_resumo():
    quarto = Simples(numero="101", capacidade=2, diaria=150)

    resumo = quarto.requisitarQuarto()

    assert "101" in resumo
    assert "Simples" in resumo
    assert "150.00" in resumo


def test_diferencial_deve_ser_string():
    with pytest.raises(ValueError):
        Simples(numero="S1", capacidade=1, diaria=100, diferencial=123)


def test_quarto_persiste_diferencial_no_sqlite(tmp_path):
    from app.database.repositorio import Repositorio

    repo = Repositorio(tmp_path / "quartos.db")
    try:
        quarto = Luxo(
            numero="L10", capacidade=3, diaria=450,
            diferencial="Varanda", observacoes="Andar superior"
        )
        repo.salvar_quarto(quarto)

        recuperado = repo.obter_quarto("L10")

        assert isinstance(recuperado, Luxo)
        assert recuperado.diferencial == "Varanda"
        assert recuperado.observacoes == "Andar superior"
    finally:
        repo.fechar()


def test_quarto_carrega_bloqueios_persistidos(tmp_path):
    from datetime import date
    from app.database.repositorio import Repositorio
    from app.models.registros import Bloqueio

    repo = Repositorio(tmp_path / "bloqueios_quarto.db")
    try:
        repo.salvar_quarto(Simples(numero="101", capacidade=2, diaria=150))
        bloqueio = Bloqueio(
            id="B1", quarto_relacionado="101", data=date(2026, 12, 1),
            tipo="manutencao", status="ativo"
        )
        repo.salvar_bloqueio(bloqueio)

        quarto = repo.obter_quarto("101")

        assert len(quarto.bloqueios) == 1
        assert quarto.bloqueios[0].id == "B1"
        assert quarto.bloqueios[0].tipo == "manutencao"
    finally:
        repo.fechar()


def test_quarto_e_abstrata_conforme_uml():
    with pytest.raises(TypeError):
        Quarto(numero="101", capacidade=2, diaria=150)


def test_migracao_adiciona_diferencial_em_banco_legado(tmp_path):
    import sqlite3
    from app.database.repositorio import Repositorio

    caminho = tmp_path / "legado.db"
    conexao = sqlite3.connect(caminho)
    conexao.execute(
        """CREATE TABLE quartos (
            numero TEXT PRIMARY KEY,
            tipo TEXT NOT NULL DEFAULT 'Simples',
            capacidade INTEGER NOT NULL,
            diaria REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'disponivel',
            observacoes TEXT NOT NULL DEFAULT ''
        )"""
    )
    conexao.execute(
        "INSERT INTO quartos (numero, tipo, capacidade, diaria, status, observacoes) "
        "VALUES ('101', 'Simples', 2, 150, 'disponivel', '')"
    )
    conexao.commit()
    conexao.close()

    repo = Repositorio(caminho)
    try:
        colunas = {
            linha["name"]
            for linha in repo.conn.execute("PRAGMA table_info(quartos)").fetchall()
        }
        assert "diferencial" in colunas
        assert repo.obter_quarto("101").diferencial == ""
    finally:
        repo.fechar()
