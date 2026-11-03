"""Ponto de entrada ASGI do SRH-WDA (FastAPI)."""

import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import router
from app.database.repositorio import Repositorio


def create_app(
    repositorio: Repositorio | None = None,
    caminho_db: str | Path | None = None,
) -> FastAPI:
    """Cria a aplicação e permite injetar um repositório nos testes."""
    repositorio_proprio = repositorio is None
    repositorio_app = repositorio or Repositorio(
        caminho_db or os.environ.get("HOTEL_DB", "srh_wda.db")
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        if repositorio_proprio:
            app.state.repositorio.fechar()

    app = FastAPI(
        title="SRH-WDA — Sistema de Reservas de Hotel",
        description=(
            "API para gerenciamento de quartos, hóspedes, funcionários, reservas, "
            "bloqueios, pagamentos e relatórios."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.repositorio = repositorio_app
    app.include_router(router)

    @app.exception_handler(ValueError)
    async def tratar_regra_negocio(_: Request, erro: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(erro)})

    @app.exception_handler(sqlite3.IntegrityError)
    async def tratar_integridade(_: Request, erro: sqlite3.IntegrityError):
        return JSONResponse(
            status_code=409,
            content={"detail": f"Violação de integridade: {erro}"},
        )

    return app


app = create_app()
