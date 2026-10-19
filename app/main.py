from datetime import date
from app.services.relatorios import relatorio_ocupacao

relatorio = relatorio_ocupacao(
    date(2026, 10, 19),
    date(2026, 10, 23)
)

for dia in relatorio:
    print(f"Data: {dia['data']}")
    print(
        f"Quartos ocupados: "
        f"{dia['quartos_ocupados']}/{dia['total_quartos']}"
    )
    print(f"Ocupação: {dia['percentual_ocupacao']}%")
    print("-" * 30)