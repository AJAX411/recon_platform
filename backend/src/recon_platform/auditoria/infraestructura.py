"""Modelo y repositorio SQLAlchemy de auditoría general."""

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, select
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, Session, mapped_column

from recon_platform.auditoria.dominio import EventoAuditoria
from recon_platform.extensions import db

ENTERO_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _utc(valor: datetime) -> datetime:
    return valor.replace(tzinfo=UTC) if valor.tzinfo is None else valor.astimezone(UTC)


class EventoAuditoriaModelo(db.Model):
    __tablename__ = "evento_auditoria"
    __table_args__ = (
        CheckConstraint("tipo_actor IN ('USUARIO', 'SISTEMA')", name="ck_evento_auditoria_tipo_actor"),
        CheckConstraint("resultado IN ('EXITOSO', 'FALLIDO')", name="ck_evento_auditoria_resultado"),
        CheckConstraint("(tipo_actor = 'USUARIO' AND id_usuario_actor IS NOT NULL) OR (tipo_actor = 'SISTEMA' AND id_usuario_actor IS NULL)", name="ck_evento_auditoria_actor"),
        Index("ix_evento_auditoria_recurso", "recurso_tipo", "id_recurso_afectado"),
    )

    id_auditoria: Mapped[int] = mapped_column(ENTERO_ID, primary_key=True, autoincrement=True)
    id_usuario_actor: Mapped[int | None] = mapped_column(ENTERO_ID, ForeignKey(
        "usuario_plataforma.id_usuario", name="fk_evento_auditoria_actor", ondelete="RESTRICT"), nullable=True, index=True)
    tipo_actor: Mapped[str] = mapped_column(String(20), nullable=False)
    accion: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    recurso_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    id_recurso_afectado: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=_ahora, index=True)


class RepositorioEventosSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
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


class UnidadTrabajoSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def confirmar(self) -> None:
        self.sesion.commit()

    def revertir(self) -> None:
        self.sesion.rollback()
