"""Una confirmación o reversión por caso de uso IAM."""

from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy.session import Session as SesionFlask
from sqlalchemy.orm import Session, scoped_session

from recon_platform.identidad.repositorio_cuentas import _traducir_integridad


class UnidadTrabajoIAMSQLAlchemy:
    def __init__(self, sesion: Session | scoped_session[SesionFlask]) -> None:
        self.sesion = sesion

    def confirmar(self) -> None:
        try:
            self.sesion.commit()
        except IntegrityError as error:
            raise _traducir_integridad(error) from error

    def revertir(self) -> None:
        self.sesion.rollback()
