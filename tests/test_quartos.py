import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.quartos import Quarto, Simples, Luxo


def test_criar_quarto_valido():
    q = Quarto(numero="101", capacidade=2, diaria=150.0)
    assert q.numero == "101"
    assert q.capacidade == 2
    assert q.diaria == 150.0
    assert q.status == "disponivel"


def test_diaria_invalida_levanta_erro():
    with pytest.raises(ValueError):
        Quarto(numero="101", capacidade=2, diaria=-10)


def test_capacidade_invalida_levanta_erro():
    with pytest.raises(ValueError):
        Quarto(numero="101", capacidade=0, diaria=100)


def test_status_invalido_levanta_erro():
    with pytest.raises(ValueError):
        Quarto(numero="101", capacidade=2, diaria=100, status="inexistente")


def test_numero_vazio_levanta_erro():
    with pytest.raises(ValueError):
        Quarto(numero="  ", capacidade=2, diaria=100)


def test_str_quarto():
    q = Quarto(numero="202", capacidade=2, diaria=200.0)
    assert "202" in str(q)
    assert "200.00" in str(q)


def test_lt_quarto_compara_por_diaria():
    barato = Quarto(numero="101", capacidade=2, diaria=100)
    caro = Quarto(numero="102", capacidade=2, diaria=300)
    assert barato < caro
    assert not (caro < barato)


def test_sorted_lista_de_quartos():
    q1 = Quarto(numero="A", capacidade=2, diaria=300)
    q2 = Quarto(numero="B", capacidade=2, diaria=100)
    q3 = Quarto(numero="C", capacidade=2, diaria=200)
    ordenados = sorted([q1, q2, q3])
    assert [q.numero for q in ordenados] == ["B", "C", "A"]


def test_subclasses_herdam_validacao():
    with pytest.raises(ValueError):
        Simples(numero="S1", capacidade=1, diaria=-5)
    luxo = Luxo(numero="L1", capacidade=4, diaria=500)
    assert luxo.diaria == 500


# ---------- Testes de manipulação (objeto já criado, alterando estado) ----------

def test_alterar_status_apos_criacao():
    q = Quarto(numero="101", capacidade=2, diaria=150.0)
    assert q.status == "disponivel"
    q.status = "ocupado"
    assert q.status == "ocupado"


def test_alterar_diaria_apos_criacao():
    q = Quarto(numero="101", capacidade=2, diaria=150.0)
    q.diaria = 180.0
    assert q.diaria == 180.0


def test_alterar_diaria_invalida_apos_criacao_levanta_erro():
    q = Quarto(numero="101", capacidade=2, diaria=150.0)
    with pytest.raises(ValueError):
        q.diaria = -10
    assert q.diaria == 150.0  # valor antigo preservado, mudança rejeitada


def test_alterar_status_invalido_apos_criacao_levanta_erro():
    q = Quarto(numero="101", capacidade=2, diaria=150.0)
    with pytest.raises(ValueError):
        q.status = "inexistente"
    assert q.status == "disponivel"  # não mudou