"""Unidad de trabajo existente."""

from flask_sqlalchemy.session import Session as SesionFlask
from sqlalchemy.orm import Session, scoped_session


class UnidadTrabajoEventosSQLAlchemy:
    def __init__(self, sesion: Session | scoped_session[SesionFlask]) -> None:
        self.sesion = sesion

    def iniciar(self) -> None:
        # El guard IAM puede haber abierto una transacción de lectura REPEATABLE READ.
        self.sesion.rollback()

    def confirmar(self) -> None:
        self.sesion.commit()

    def revertir(self) -> None:
        self.sesion.rollback()
