# ======================= Operações de persitência para lançamentos ==================================

from app.database.database import conectar


def salvar_pagamento(pagamento, reserva_id):
    """Persiste um pagamento associado a uma reserva."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO pagamentos (
                id, reserva_id, valor, data_pagamento, metodo
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                pagamento.id,
                reserva_id,
                pagamento.valor,
                pagamento.data.isoformat(),
                pagamento.metodo,
            ),
        )


def salvar_adicional(adicional, reserva_id):
    """Persiste um adicional associado a uma reserva."""
    with conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO adicionais (
                id, reserva_id, descricao, valor, data_lancamento
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                adicional.id,
                reserva_id,
                adicional.descricao,
                adicional.valor,
                adicional.data.isoformat(),
            ),
        )
