from datetime import date

import pytest

from app.services.tarifas import Tarifa


def test_diaria_normal_dia_de_semana():
    t = Tarifa(100.0)
    assert t.calcular_diaria(date(2026, 10, 28)) == pytest.approx(100.0)  # quarta


def test_diaria_fim_de_semana():
    t = Tarifa(100.0)
    assert t.calcular_diaria(date(2026, 10, 30)) == pytest.approx(130.0)  # sexta
    assert t.calcular_diaria(date(2026, 10, 31)) == pytest.approx(130.0)  # sábado
    assert t.calcular_diaria(date(2026, 11, 1)) == pytest.approx(100.0)   # domingo


def test_diaria_temporada_alta():
    t = Tarifa(100.0)
    assert t.calcular_diaria(date(2026, 12, 15)) == pytest.approx(150.0)  # dez (terça)


def test_diaria_fim_de_semana_em_temporada_soma_os_dois():
    t = Tarifa(100.0)
    # sexta em dezembro: 100 * 1.30 * 1.50
    assert t.calcular_diaria(date(2026, 12, 4)) == pytest.approx(195.0)


def test_calcular_total_soma_cada_noite():
    t = Tarifa(100.0)
    # sex, sáb, dom = 130 + 130 + 100
    total = t.calcular_total(date(2026, 10, 30), date(2026, 11, 2))
    assert total == pytest.approx(360.0)


def test_aplicar_desconto_sobre_total():
    t = Tarifa(100.0)
    assert t.aplicar_desconto(360.0, 0.10) == pytest.approx(324.0)


def test_diaria_base_deve_ser_positiva():
    with pytest.raises(ValueError):
        Tarifa(0)


def test_acrescimos_devem_ser_percentuais_entre_0_e_1():
    with pytest.raises(ValueError):
        Tarifa(100.0, acrescimo_fds=1.5)
    with pytest.raises(ValueError):
        Tarifa(100.0, acrescimo_temporada=-0.1)


def test_total_com_saida_antes_da_entrada():
    t = Tarifa(100.0)
    with pytest.raises(ValueError):
        t.calcular_total(date(2026, 11, 5), date(2026, 11, 5))