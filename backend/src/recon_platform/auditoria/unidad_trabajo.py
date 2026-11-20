"""Unidad de trabajo existente."""

from flask_sqlalchemy.session import Session as SesionFlask
from sqlalchemy.orm import Session, scoped_session


class UnidadTrabajoSQLAlchemy:
    def __init__(self, sesion: Session | scoped_session[SesionFlask]) -> None:
        self.sesion = sesion

    def confirmar(self) -> None:
        self.sesion.commit()

    def revertir(self) -> None:
        self.sesion.rollback()
