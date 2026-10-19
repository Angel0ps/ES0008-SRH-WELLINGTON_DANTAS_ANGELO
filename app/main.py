# teste rápido

from datetime import date

from app.models.registros import Reserva, Pagamento, Adicional

reserva = Reserva(
    id="RES001",
    quarto_relacionado="101",
    data=date(2026, 10, 19),
    tipo="reserva",
    status="ativo",
    data_entrada=date(2026, 10, 20),
    data_saida=date(2026, 10, 23),
    qtd_hospedes=2,
    hospede_id="H001"
)

pagamento = Pagamento(
    id="PAG001",
    valor=200.00,
    data=date(2026, 10, 19),
    metodo="Pix"
)

adicional = Adicional(
    id="ADI001",
    descricao="Consumo do frigobar",
    valor=35.00,
    data=date(2026, 10, 21)
)

reserva.pagamentos.append(pagamento)
reserva.adicionais.append(adicional)

valor_hospedagem = 3 * 150.00

print("Total pago:", reserva.total_pago())
print("Total de adicionais:", reserva.total_adicionais())
print("Total devido:", reserva.total_devido(valor_hospedagem))