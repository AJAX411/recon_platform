"""Composición de puertos y adaptadores de las nuevas capacidades."""

from recon_platform.accesos.aplicacion import AdministrarPuntos
from recon_platform.accesos.infraestructura import RepositorioPuntosSQLAlchemy
from recon_platform.auditoria.aplicacion import AuditoriaGeneral
from recon_platform.auditoria.infraestructura import RepositorioEventosSQLAlchemy, UnidadTrabajoSQLAlchemy
from recon_platform.extensions import db
from recon_platform.integracion_edge.aplicacion import AdministrarDispositivos
from recon_platform.integracion_edge.infraestructura import ConsultaPuntosSQLAlchemy, RepositorioDispositivosSQLAlchemy


def auditoria() -> AuditoriaGeneral:
    return AuditoriaGeneral(RepositorioEventosSQLAlchemy(db.session), UnidadTrabajoSQLAlchemy(db.session))


def puntos() -> AdministrarPuntos:
    return AdministrarPuntos(RepositorioPuntosSQLAlchemy(db.session),
                            RepositorioEventosSQLAlchemy(db.session), UnidadTrabajoSQLAlchemy(db.session))


def dispositivos() -> AdministrarDispositivos:
    return AdministrarDispositivos(RepositorioDispositivosSQLAlchemy(db.session),
                                  ConsultaPuntosSQLAlchemy(db.session),
                                  RepositorioEventosSQLAlchemy(db.session), UnidadTrabajoSQLAlchemy(db.session))
