# ======================================= Operações no banco de dados relacionados a reserva ================================
from app.database.database import conectar


def salvar_reserva(reserva, hospede_id):
    """Persiste uma reserva no banco de dados."""

    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO reservas (
                id,
                hospede_id,
                quarto_numero,
                data_reserva,
                data_entrada,
                data_saida,
                qtd_hospedes,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reserva.id,
                hospede_id,
                reserva.quarto_relacionado,
                reserva.data.isoformat(),
                reserva.data_entrada.isoformat(),
                reserva.data_saida.isoformat(),
                reserva.qtd_hospedes,
                reserva.status,
            ),
        )
