# Serviço = Relatório 

from datetime import date, timedelta
from app.database.database import conectar


def relatorio_ocupacao(data_inicio: date, data_fim: date) -> list[dict]:
    """Gera um relatório de ocupação dos quartos por período."""

    if not isinstance(data_inicio, date) or not isinstance(data_fim, date):
        raise ValueError("As datas devem ser objetos do tipo date")

    if data_inicio > data_fim:
        raise ValueError("A data inicial não pode ser posterior à data final")

    relatorio = []

    with conectar() as conexao:
        total_quartos = conexao.execute("""
            SELECT COUNT(*) AS total
            FROM quartos
        """).fetchone()["total"]

        dia = data_inicio

        while dia <= data_fim:
            quartos_ocupados = conexao.execute("""
                SELECT COUNT(DISTINCT quarto_numero) AS total
                FROM reservas
                WHERE data_entrada <= ?
                  AND data_saida > ?
                  AND LOWER(status) NOT IN (
                      'cancelada', 'cancelado', 'cancelled', 'cancel'
                  )
            """, (dia.isoformat(), dia.isoformat())).fetchone()["total"]

            if total_quartos > 0:
                percentual = (quartos_ocupados / total_quartos) * 100
            else:
                percentual = 0.0

            relatorio.append({
                "data": dia,
                "quartos_ocupados": quartos_ocupados,
                "total_quartos": total_quartos,
                "percentual_ocupacao": round(percentual, 2)
            })

            dia += timedelta(days=1)

    return relatorio
