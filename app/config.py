"""Carregamento e validação das configurações do SRH-WDA."""

import json
from pathlib import Path

CAMINHO_CONFIGURACAO = Path(__file__).resolve().parents[1] / "settings.json"

_CONFIG_PADRAO = {
    "checkin": {"horario": "14:00", "tolerancia_antecipada_minutos": 30},
    "checkout": {"horario": "12:00", "tolerancia_atraso_minutos": 0},
    "no_show": {"tolerancia_minutos": 60},
    "cancelamento": {"prazo_gratuito_horas": 48, "multa_percentual": 1.0},
    "tarifas": {"multiplicador_fim_semana": 1.3, "temporadas": []},
}


def carregar_configuracoes(caminho: str | Path | None = None) -> dict:
    """Carrega settings.json, validando os campos essenciais."""
    arquivo = Path(caminho) if caminho else CAMINHO_CONFIGURACAO
    if not arquivo.exists():
        return json.loads(json.dumps(_CONFIG_PADRAO))
    with arquivo.open(encoding="utf-8") as fp:
        dados = json.load(fp)
    if not isinstance(dados, dict):
        raise ValueError("settings.json deve conter um objeto JSON")
    config = json.loads(json.dumps(_CONFIG_PADRAO))
    for chave, valor in dados.items():
        if isinstance(valor, dict) and isinstance(config.get(chave), dict):
            config[chave].update(valor)
        else:
            config[chave] = valor
    _validar_configuracoes(config)
    return config


def _validar_configuracoes(config: dict) -> None:
    from datetime import date

    for secao, campo in (("checkin", "horario"), ("checkout", "horario")):
        try:
            hora, minuto = map(int, config[secao][campo].split(":"))
            if not (0 <= hora <= 23 and 0 <= minuto <= 59):
                raise ValueError
        except (AttributeError, TypeError, ValueError):
            raise ValueError(f"Horário inválido em {secao}.{campo}")

    campos_nao_negativos = (
        ("checkin", "tolerancia_antecipada_minutos"),
        ("checkout", "tolerancia_atraso_minutos"),
        ("no_show", "tolerancia_minutos"),
        ("cancelamento", "prazo_gratuito_horas"),
    )
    for secao, campo in campos_nao_negativos:
        try:
            valor = int(config[secao][campo])
        except (KeyError, TypeError, ValueError):
            raise ValueError(f"Configuração inválida: {secao}.{campo}")
        if valor < 0:
            raise ValueError(f"{secao}.{campo} não pode ser negativo")

    try:
        multa = float(config["cancelamento"]["multa_percentual"])
        multiplicador_fds = float(config["tarifas"]["multiplicador_fim_semana"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Percentuais e multiplicadores de tarifas devem ser numéricos")
    if not 0 <= multa <= 1:
        raise ValueError("multa_percentual deve estar entre 0 e 1")
    if multiplicador_fds <= 0:
        raise ValueError("multiplicador_fim_semana deve ser maior que zero")

    temporadas = config["tarifas"].get("temporadas", [])
    if len(temporadas) != 3:
        raise ValueError("settings.json deve definir exatamente três períodos de temporada")
    intervalos = []
    for temporada in temporadas:
        try:
            inicio = date.fromisoformat(temporada["inicio"])
            fim = date.fromisoformat(temporada["fim"])
            multiplicador = float(temporada["multiplicador"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Temporada possui datas ou multiplicador inválido")
        if fim < inicio or multiplicador <= 0:
            raise ValueError("Temporada possui período ou multiplicador inválido")
        intervalos.append((inicio, fim))

    intervalos.sort()
    for anterior, atual in zip(intervalos, intervalos[1:]):
        if atual[0] <= anterior[1]:
            raise ValueError("Os períodos de temporada não podem se sobrepor")
