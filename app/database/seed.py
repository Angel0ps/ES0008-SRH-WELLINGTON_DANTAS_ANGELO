"""Carga inicial idempotente de quartos para demonstração.

Execute na raiz: python -m app.database.seed
As três temporadas são mantidas em settings.json.
"""
from app.database.repositorio import Repositorio
from app.models.quartos import Simples, Duplo, Luxo


QUARTOS_INICIAIS = (
    Simples("101", 1, 120.0),
    Simples("102", 1, 120.0),
    Simples("103", 1, 130.0),
    Duplo("201", 2, 180.0),
    Duplo("202", 2, 190.0),
    Duplo("203", 2, 200.0),
    Luxo("301", 4, 350.0),
)


def executar_seed(caminho_db: str = "srh_wda.db") -> int:
    """Insere somente quartos inexistentes e retorna a quantidade criada."""
    repo = Repositorio(caminho_db)
    criados = 0
    try:
        for quarto in QUARTOS_INICIAIS:
            if repo.obter_quarto(quarto.numero) is None:
                repo.salvar_quarto(quarto)
                criados += 1
    finally:
        repo.fechar()
    return criados


if __name__ == "__main__":
    quantidade = executar_seed()
    print(f"Seed concluído: {quantidade} quarto(s) inserido(s).")
