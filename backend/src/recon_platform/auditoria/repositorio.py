"""Adaptador SQLAlchemy de auditoría general.
Agrega/consulta eventos y hace flush; la unidad de trabajo decide confirmar."""

from datetime import UTC, datetime

from sqlalchemy import select
from flask_sqlalchemy.session import Session as SesionFlask
from sqlalchemy.orm import Session, scoped_session

from recon_platform.auditoria.modelos import EventoAuditoriaModelo
from recon_platform.auditoria.evento_auditoria import EventoAuditoria


def _utc(valor: datetime) -> datetime:
    return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


class RepositorioEventosSQLAlchemy:
    def __init__(self, sesion: Session | scoped_session[SesionFlask]) -> None:
        self.sesion = sesion

    def agregar(self, evento: EventoAuditoria) -> EventoAuditoria:
        modelo = EventoAuditoriaModelo(
            id_usuario_actor=evento.id_usuario_actor, tipo_actor=evento.tipo_actor,
            accion=evento.accion, recurso_tipo=evento.recurso_tipo,
            id_recurso_afectado=evento.id_recurso_afectado, resultado=evento.resultado,
            detalle=evento.detalle,
        )
        self.sesion.add(modelo)
        self.sesion.flush()
        return self._dominio(modelo)

    def listar(self, *, limite: int, desplazamiento: int, filtros: dict) -> list[EventoAuditoria]:
        consulta = select(EventoAuditoriaModelo)
        for campo in ("accion", "resultado", "recurso_tipo", "id_usuario_actor"):
            if campo in filtros:
                consulta = consulta.where(getattr(EventoAuditoriaModelo, campo) == filtros[campo])
        if "desde" in filtros:
            consulta = consulta.where(EventoAuditoriaModelo.fecha_hora >= filtros["desde"].astimezone(UTC).replace(tzinfo=None))
        if "hasta" in filtros:
            consulta = consulta.where(EventoAuditoriaModelo.fecha_hora <= filtros["hasta"].astimezone(UTC).replace(tzinfo=None))
        modelos = self.sesion.scalars(consulta.order_by(
            EventoAuditoriaModelo.fecha_hora.desc(), EventoAuditoriaModelo.id_auditoria.desc()
        ).limit(limite).offset(desplazamiento)).all()
        return [self._dominio(modelo) for modelo in modelos]

    @staticmethod
    def _dominio(modelo: EventoAuditoriaModelo) -> EventoAuditoria:
        return EventoAuditoria(id_auditoria=modelo.id_auditoria,
                               id_usuario_actor=modelo.id_usuario_actor,
                               tipo_actor=modelo.tipo_actor, accion=modelo.accion,
                               recurso_tipo=modelo.recurso_tipo,
                               id_recurso_afectado=modelo.id_recurso_afectado,
                               resultado=modelo.resultado, detalle=modelo.detalle,
                               fecha_hora=_utc(modelo.fecha_hora))
