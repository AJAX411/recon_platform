"""Construcción por petición de casos de uso y adaptadores; no abre transacciones."""

from collections.abc import Callable
from datetime import datetime

from recon_platform.accesos.servicio_puntos import AdministrarPuntos
from recon_platform.accesos.servicio_eventos import ConsultarEventosAcceso, RegistrarEventoManual
from recon_platform.accesos.repositorio_puntos import RepositorioPuntosSQLAlchemy
from recon_platform.accesos.repositorio_eventos import RepositorioEventosSQLAlchemy
from recon_platform.accesos.unidad_trabajo_eventos import UnidadTrabajoEventosSQLAlchemy
from recon_platform.auditoria.servicio import AuditoriaGeneral
from recon_platform.auditoria.repositorio import RepositorioEventosSQLAlchemy as RepositorioAuditoria
from recon_platform.auditoria.unidad_trabajo import UnidadTrabajoSQLAlchemy
from recon_platform.extensions import db
from recon_platform.identidad.servicio_sesiones import GestionSesiones
from recon_platform.identidad.repositorio_cuentas import RepositorioIAMSQLAlchemy
from recon_platform.identidad.repositorio_sesiones import RepositorioSesionesSQLAlchemy
from recon_platform.identidad.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy
from recon_platform.integracion_edge.servicio import AdministrarDispositivos
from recon_platform.integracion_edge.repositorio import ConsultaPuntosSQLAlchemy, RepositorioDispositivosSQLAlchemy
from recon_platform.personas.servicio import AdministrarPersonas
from recon_platform.personas.repositorio import RepositorioPersonasSQLAlchemy, RepositorioTiposPersonaSQLAlchemy
from recon_platform.personas.unidad_trabajo import UnidadTrabajoSQLAlchemy as UnidadTrabajoPersonasSQLAlchemy
from recon_platform.accesos.lecturas import LecturaAccesosSQLAlchemy
from recon_platform.personas.lecturas import LecturaPersonasSQLAlchemy
from recon_platform.consultas.unidad_lectura import UnidadLecturaSQLAlchemy
from recon_platform.consultas.servicio import ConsultarDashboard


def auditoria() -> AuditoriaGeneral:
    return AuditoriaGeneral(RepositorioAuditoria(db.session), UnidadTrabajoSQLAlchemy(db.session))


def puntos() -> AdministrarPuntos:
    return AdministrarPuntos(RepositorioPuntosSQLAlchemy(db.session),
                            RepositorioAuditoria(db.session), UnidadTrabajoSQLAlchemy(db.session))


def dispositivos() -> AdministrarDispositivos:
    return AdministrarDispositivos(RepositorioDispositivosSQLAlchemy(db.session),
                                  ConsultaPuntosSQLAlchemy(db.session),
                                  RepositorioAuditoria(db.session), UnidadTrabajoSQLAlchemy(db.session))


def crear_gestor_sesiones(clave_csrf: str) -> GestionSesiones:
    return GestionSesiones(
        RepositorioSesionesSQLAlchemy(db.session),
        RepositorioIAMSQLAlchemy(db.session),
        UnidadTrabajoIAMSQLAlchemy(db.session),
        clave_csrf,
    )


def crear_dependencias_iam() -> tuple[RepositorioIAMSQLAlchemy, UnidadTrabajoIAMSQLAlchemy]:
    """Inyecta repositorio y unidad IAM con la misma sesión de petición."""
    return RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)


def crear_administracion_personas() -> AdministrarPersonas:
    return AdministrarPersonas(RepositorioPersonasSQLAlchemy(db.session),
                              RepositorioTiposPersonaSQLAlchemy(db.session),
                              UnidadTrabajoPersonasSQLAlchemy(db.session))


def crear_consulta_eventos(reloj: Callable[[], datetime]) -> ConsultarEventosAcceso:
    return ConsultarEventosAcceso(RepositorioEventosSQLAlchemy(db.session), reloj)


def crear_registro_manual(reloj: Callable[[], datetime]) -> RegistrarEventoManual:
    """Compone registro manual con repositorio, auditoría y unidad transaccional."""
    return RegistrarEventoManual(RepositorioEventosSQLAlchemy(db.session),
        RepositorioAuditoria(db.session), UnidadTrabajoEventosSQLAlchemy(db.session), reloj)


def crear_dashboard(reloj: Callable[[], datetime]) -> ConsultarDashboard:
    return ConsultarDashboard(LecturaAccesosSQLAlchemy(db.session),
        LecturaPersonasSQLAlchemy(db.session), UnidadLecturaSQLAlchemy(db.session), reloj)
