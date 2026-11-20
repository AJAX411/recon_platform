"""Fotografía transaccional explícita; libera lecturas mediante rollback."""


class UnidadLecturaSQLAlchemy:
    def __init__(self, sesion) -> None:
        self.sesion = sesion

    def iniciar(self) -> None:
        self.sesion.rollback()  # Descarta la snapshot implícita del guard IAM.
        dialecto = self.sesion.get_bind().dialect.name
        aislamiento = {"mysql": "REPEATABLE READ", "sqlite": "SERIALIZABLE"}.get(dialecto)
        if aislamiento is None:
            raise RuntimeError("Motor de lectura no admitido.")
        self.sesion.connection(execution_options={"isolation_level": aislamiento})

    def terminar(self) -> None:
        self.sesion.rollback()
