"""Agregado de Personas sobre el modelo propio, sin filtrar estado."""

from sqlalchemy import func, select

from recon_platform.personas.modelos import PersonaModelo


class LecturaPersonasSQLAlchemy:
    def __init__(self, sesion) -> None:
        self.sesion = sesion

    def total(self) -> int:
        return self.sesion.scalar(select(func.count()).select_from(PersonaModelo))
