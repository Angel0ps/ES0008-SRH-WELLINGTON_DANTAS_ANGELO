
import pytest

from app.models.pessoas import Hospede, Pessoa


def criar_hospede(
    id="h1",
    nome="Ana",
    documento="12345678900",
    email="ana@email.com",
    telefone="88999990000",
    **kwargs,
):
    """Cria um hóspede para reutilizar nos testes."""
    return Hospede(
        id=id,
        nome=nome,
        documento=documento,
        email=email,
        telefone=telefone,
        **kwargs,
    )


def test_criar_hospede_valido():
    h = criar_hospede(
        nome="Maria Silva",
        documento="123.456.789-00",
        email="maria@email.com",
        telefone="(88) 99999-0000",
    )

    assert h.nome == "Maria Silva"
    assert h.documento == "12345678900"
    assert h.email == "maria@email.com"


def test_documento_invalido_levanta_erro():
    with pytest.raises(ValueError):
        criar_hospede(documento="123")


def test_email_invalido_levanta_erro():
    with pytest.raises(ValueError):
        criar_hospede(email="email-invalido")


def test_nome_vazio_levanta_erro():
    with pytest.raises(ValueError):
        criar_hospede(nome=" ")


def test_telefone_curto_levanta_erro():
    with pytest.raises(ValueError):
        criar_hospede(telefone="123")


def test_id_vazio_levanta_erro():
    with pytest.raises(ValueError):
        criar_hospede(id=" ")


def test_str_hospede():
    h = criar_hospede(nome="João")

    assert "João" in str(h)


def test_eq_hospede_por_documento():
    h1 = criar_hospede(
        id="h1",
        nome="Maria",
        documento="12345678900",
        email="a@a.com",
    )

    h2 = criar_hospede(
        id="h2",
        nome="Maria Silva",
        documento="123.456.789-00",
        email="b@b.com",
        telefone="88988880000",
    )

    assert h1 == h2


def test_hospede_e_instancia_de_pessoa():
    h = criar_hospede()

    assert isinstance(h, Pessoa)


def test_pessoa_nao_pode_ser_instanciada_diretamente():
    with pytest.raises(TypeError):
        Pessoa(
            id="p1",
            nome="X",
            documento="12345678900",
            email="x@x.com",
            telefone="88999990000",
        )


def test_observacoes_e_acessibilidade_default():
    h = criar_hospede()

    assert h.observacoes == ""
    assert h.acessibilidade is False


def test_observacoes_e_acessibilidade_informadas():
    h = criar_hospede(
        observacoes="prefere andar alto",
        acessibilidade=True,
    )

    assert h.observacoes == "prefere andar alto"
    assert h.acessibilidade is True
    assert "acessibilidade" in str(h)


def test_acessibilidade_tipo_invalido_levanta_erro():
    with pytest.raises(TypeError):
        criar_hospede(acessibilidade="sim")


def test_gerenciar_hospedes_retorna_str():
    h = criar_hospede(nome="Ana")

    resultado = h.gerenciarHospedes()

    assert isinstance(resultado, str)
    assert "Ana" in resultado


def test_requisitar_hospede_retorna_str():
    h = criar_hospede(nome="Ana")

    resultado = h.requisitarHospede()

    assert isinstance(resultado, str)
    assert "Ana" in resultado


# ============ Testes de alteração de estado ============

def test_alterar_observacoes_apos_criacao():
    h = criar_hospede()

    assert h.observacoes == ""

    h.observacoes = "quarto longe do elevador"

    assert h.observacoes == "quarto longe do elevador"


def test_alterar_acessibilidade_apos_criacao():
    h = criar_hospede()

    assert h.acessibilidade is False

    h.acessibilidade = True

    assert h.acessibilidade is True
    assert "acessibilidade" in str(h)


def test_alterar_email_invalido_apos_criacao_levanta_erro():
    h = criar_hospede(email="ana@email.com")

    with pytest.raises(ValueError):
        h.email = "invalido"

    assert h.email == "ana@email.com"
