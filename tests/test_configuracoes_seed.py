from datetime import date

from app.config import carregar_configuracoes
from app.database.seed import executar_seed
from app.database.repositorio import Repositorio
from app.services.tarifas import Tarifa


def test_settings_possui_tres_temporadas():
    config = carregar_configuracoes()
    assert len(config["tarifas"]["temporadas"]) == 3
    assert config["checkin"]["horario"] == "14:00"
    assert config["checkout"]["horario"] == "12:00"


def test_tarifa_usa_multiplicadores_de_settings():
    tarifa = Tarifa(100)
    # 2026-12-04 é sexta-feira e pertence à alta temporada.
    assert tarifa.calcular_diaria(date(2026, 12, 4)) == 195.0
    # 2026-10-07 está no intervalo configurado sem acréscimo sazonal.
    assert tarifa.calcular_diaria(date(2026, 10, 7)) == 100.0


def test_seed_povoa_seis_a_oito_quartos_e_e_idempotente(tmp_path):
    caminho = str(tmp_path / "seed-final.db")
    assert executar_seed(caminho) == 7
    assert executar_seed(caminho) == 0
    repo = Repositorio(caminho)
    try:
        quartos = repo.listar_quartos()
        assert 6 <= len(quartos) <= 8
        assert {type(q).__name__ for q in quartos} == {"Simples", "Duplo", "Luxo"}
    finally:
        repo.fechar()
