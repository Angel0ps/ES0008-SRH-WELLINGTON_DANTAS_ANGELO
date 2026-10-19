# ============================= Operações no banco de dados relacionados a relatórios ===============================================
from app.database.database import conectar


def relatorio_ocupacao(data_inicio, data_fim):
    """Calcula a ocupação dos quartos no período informado."""

    if data_fim <= data_inicio:
        raise ValueError(
            "A data final deve ser posterior à data inicial."
        )

    with conectar() as conexao:
        total_quartos = conexao.execute(
            "SELECT COUNT(*) FROM quartos"
        ).fetchone()[0]

        quartos_ocupados = conexao.execute(
            """
            SELECT COUNT(DISTINCT quarto_numero)
            FROM reservas
            WHERE status NOT IN ('cancelada', 'cancelado')
              AND data_entrada < ?
              AND data_saida > ?
            """,
            (
                data_fim.isoformat(),
                data_inicio.isoformat(),
            ),
        ).fetchone()[0]

    disponiveis = total_quartos - quartos_ocupados

    percentual = (
        quartos_ocupados / total_quartos * 100
        if total_quartos > 0
        else 0
    )

    return {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "total_quartos": total_quartos,
        "quartos_ocupados": quartos_ocupados,
        "quartos_disponiveis": disponiveis,
        "percentual_ocupacao": round(percentual, 2),
    }
