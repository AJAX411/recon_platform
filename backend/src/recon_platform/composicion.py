"""Construcción por petición de casos de uso y adaptadores; no abre transacciones."""

from collections.abc import Callable
from datetime import datetime

from recon_platform.accesos.servicios.puntos import AdministrarPuntos
from recon_platform.accesos.servicios.eventos import ConsultarEventosAcceso, RegistrarEventoManual
from recon_platform.accesos.infraestructura.repositorios_puntos import RepositorioPuntosSQLAlchemy
from recon_platform.accesos.infraestructura.repositorios_eventos import RepositorioEventosSQLAlchemy
from recon_platform.accesos.infraestructura.unidad_trabajo_eventos import UnidadTrabajoEventosSQLAlchemy
from recon_platform.auditoria.servicios.eventos import AuditoriaGeneral
from recon_platform.auditoria.infraestructura.repositorios import RepositorioEventosSQLAlchemy as RepositorioAuditoria
from recon_platform.auditoria.infraestructura.unidad_trabajo import UnidadTrabajoSQLAlchemy
from recon_platform.extensions import db
from recon_platform.identidad.servicios.sesiones import GestionSesiones
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.repositorios_sesiones import RepositorioSesionesSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy
from recon_platform.integracion_edge.servicios.dispositivos import AdministrarDispositivos
from recon_platform.integracion_edge.infraestructura.repositorios import ConsultaPuntosSQLAlchemy, RepositorioDispositivosSQLAlchemy
from recon_platform.personas.servicios.personas import AdministrarPersonas
from recon_platform.personas.infraestructura.repositorios import RepositorioPersonasSQLAlchemy, RepositorioTiposPersonaSQLAlchemy
from recon_platform.personas.infraestructura.unidad_trabajo import UnidadTrabajoSQLAlchemy as UnidadTrabajoPersonasSQLAlchemy


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
    return RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)


def crear_administracion_personas() -> AdministrarPersonas:
    return AdministrarPersonas(RepositorioPersonasSQLAlchemy(db.session),
                              RepositorioTiposPersonaSQLAlchemy(db.session),
                              UnidadTrabajoPersonasSQLAlchemy(db.session))


def crear_consulta_eventos(reloj: Callable[[], datetime]) -> ConsultarEventosAcceso:
    return ConsultarEventosAcceso(RepositorioEventosSQLAlchemy(db.session), reloj)


def crear_registro_manual(reloj: Callable[[], datetime]) -> RegistrarEventoManual:
    return RegistrarEventoManual(RepositorioEventosSQLAlchemy(db.session),
        RepositorioAuditoria(db.session), UnidadTrabajoEventosSQLAlchemy(db.session), reloj)
