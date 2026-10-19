import pytest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.pessoas import Hospede, Pessoa


def test_criar_hospede_valido():
    h = Hospede(id="h1", nome="Maria Silva", documento="123.456.789-00",
                email="maria@email.com", telefone="(88) 99999-0000")
    assert h.nome == "Maria Silva"
    assert h.documento == "12345678900"  # normalizado, só dígitos
    assert h.email == "maria@email.com"


def test_documento_invalido_levanta_erro():
    with pytest.raises(ValueError):
        Hospede(id="h1", nome="Maria", documento="123", email="m@e.com",
                 telefone="88999990000")


def test_email_invalido_levanta_erro():
    with pytest.raises(ValueError):
        Hospede(id="h1", nome="Maria", documento="12345678900", email="email-invalido",
                 telefone="88999990000")


def test_nome_vazio_levanta_erro():
    with pytest.raises(ValueError):
        Hospede(id="h1", nome="   ", documento="12345678900", email="m@e.com",
                 telefone="88999990000")


def test_telefone_curto_levanta_erro():
    with pytest.raises(ValueError):
        Hospede(id="h1", nome="Maria", documento="12345678900", email="m@e.com",
                 telefone="123")


def test_id_vazio_levanta_erro():
    with pytest.raises(ValueError):
        Hospede(id="  ", nome="Maria", documento="12345678900", email="m@e.com",
                 telefone="88999990000")


def test_str_hospede():
    h = Hospede(id="h1", nome="João", documento="12345678900", email="j@e.com",
                telefone="88999990000")
    assert "João" in str(h)


def test_eq_hospede_por_documento():
    h1 = Hospede(id="h1", nome="Maria", documento="12345678900", email="a@a.com",
                 telefone="88999990000")
    h2 = Hospede(id="h2", nome="Maria Silva", documento="123.456.789-00", email="b@b.com",
                 telefone="88988880000")
    assert h1 == h2  # mesmo documento, dados diferentes


def test_hospede_e_instancia_de_pessoa():
    h = Hospede(id="h1", nome="Ana", documento="12345678900", email="a@a.com",
                telefone="88999990000")
    assert isinstance(h, Pessoa)


def test_pessoa_nao_pode_ser_instanciada_diretamente():
    with pytest.raises(TypeError):
        Pessoa(id="p1", nome="X", documento="12345678900", email="x@x.com",
               telefone="88999990000")


def test_observacoes_e_acessibilidade_default():
    h = Hospede(id="h1", nome="Ana", documento="12345678900", email="a@a.com",
                telefone="88999990000")
    assert h.observacoes == ""
    assert h.acessibilidade is False


def test_observacoes_e_acessibilidade_informadas():
    h = Hospede(id="h1", nome="Ana", documento="12345678900", email="a@a.com",
                telefone="88999990000", observacoes="prefere andar alto",
                acessibilidade=True)
    assert h.observacoes == "prefere andar alto"
    assert h.acessibilidade is True
    assert "acessibilidade" in str(h)


def test_acessibilidade_tipo_invalido_levanta_erro():
    with pytest.raises(TypeError):
        Hospede(id="h1", nome="Ana", documento="12345678900", email="a@a.com",
                telefone="88999990000", acessibilidade="sim")  # deveria ser bool


def test_gerenciar_hospedes_retorna_str():
    h = Hospede(id="h1", nome="Ana", documento="12345678900", email="a@a.com",
                telefone="88999990000")
    resultado = h.gerenciarHospedes()
    assert isinstance(resultado, str)
    assert "Ana" in resultado


def test_requisitar_hospede_retorna_str():
    h = Hospede(id="h1", nome="Ana", documento="12345678900", email="a@a.com",
                telefone="88999990000")
    resultado = h.requisitarHospede()
    assert isinstance(resultado, str)
    assert "Ana" in resultado


# =================================Testes de manipulação (objeto já criado, alterando estado) =================================

def test_alterar_observacoes_apos_criacao():
    h = Hospede(id="h1", nome="Ana", documento="12345678900", email="a@a.com",
                telefone="88999990000")
    assert h.observacoes == ""
    h.observacoes = "quarto longe do elevador"
    assert h.observacoes == "quarto longe do elevador"


def test_alterar_acessibilidade_apos_criacao():
    h = Hospede(id="h1", nome="Ana", documento="12345678900", email="a@a.com",
                telefone="88999990000")
    assert h.acessibilidade is False
    h.acessibilidade = True
    assert h.acessibilidade is True
    assert "acessibilidade" in str(h)


def test_alterar_email_invalido_apos_criacao_levanta_erro():
    h = Hospede(id="h1", nome="Ana", documento="12345678900", email="a@a.com",
                telefone="88999990000")
    with pytest.raises(ValueError):
        h.email = "invalido"
    assert h.email == "a@a.com"  # não mudou