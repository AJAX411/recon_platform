"""Una confirmación o reversión por caso de uso IAM."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from recon_platform.identidad.infraestructura.repositorios import _traducir_integridad


class UnidadTrabajoIAMSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def confirmar(self) -> None:
        try:
            self.sesion.commit()
        except IntegrityError as error:
            raise _traducir_integridad(error) from error

    def revertir(self) -> None:
        self.sesion.rollback()
