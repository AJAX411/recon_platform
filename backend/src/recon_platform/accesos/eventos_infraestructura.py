"""Adaptadores SQL de EventoAcceso; ninguna operación confirma por sí sola."""

from datetime import UTC, datetime

from sqlalchemy import (CHAR, CheckConstraint, DateTime, ForeignKey, Index, Integer,
                        String, UniqueConstraint, func, select)
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from recon_platform.accesos.eventos_aplicacion import ClaveEnCarrera, PersistenciaAccesoError
from recon_platform.accesos.eventos_dominio import BOGOTA, EventoAcceso
from recon_platform.accesos.infraestructura import PuntoAccesoModelo
from recon_platform.extensions import db
from recon_platform.identidad.infraestructura.modelos import RolModelo, UsuarioPlataformaModelo
from recon_platform.personas.infraestructura.modelos import PersonaModelo

ENTERO_ID = Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
CLAVE_UUID = CHAR(36).with_variant(mysql.CHAR(36, charset="ascii", collation="ascii_bin"), "mysql")
FECHA_UTC = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")
MOVIMIENTO_SQL = String(10).with_variant(mysql.VARCHAR(10, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
RESULTADO_SQL = String(10).with_variant(mysql.VARCHAR(10, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
METODO_SQL = String(10).with_variant(mysql.VARCHAR(10, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
INCIDENCIA_SQL = String(40).with_variant(mysql.VARCHAR(40, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")


def _sin_zona(valor: datetime) -> datetime:
    return valor.astimezone(UTC).replace(tzinfo=None)


def _con_zona(valor: datetime) -> datetime:
    return valor.replace(tzinfo=UTC)


class EventoAccesoModelo(db.Model):
    __tablename__ = "evento_acceso"
    __table_args__ = (
        CheckConstraint("tipo_movimiento IN ('ENTRADA', 'SALIDA')", name="ck_evento_acceso_movimiento"),
        CheckConstraint("resultado IN ('AUTORIZADO', 'RECHAZADO')", name="ck_evento_acceso_resultado"),
        CheckConstraint("metodo_registro IN ('MANUAL', 'FACIAL')", name="ck_evento_acceso_metodo"),
        CheckConstraint("tipo_incidencia_secuencia IS NULL OR tipo_incidencia_secuencia IN "
                        "('ENTRADA_REPETIDA', 'SALIDA_REPETIDA', 'SALIDA_SIN_ENTRADA_DEL_DIA')",
                        name="ck_evento_acceso_incidencia"),
        CheckConstraint("tipo_incidencia_secuencia IS NULL OR resultado = 'AUTORIZADO'",
                        name="ck_evento_acceso_incidencia_autorizada"),
        CheckConstraint("metodo_registro <> 'MANUAL' OR (id_persona IS NOT NULL AND "
                        "id_usuario_registrador IS NOT NULL AND id_dispositivo IS NULL AND "
                        "clave_idempotencia IS NOT NULL)", name="ck_evento_acceso_manual"),
        UniqueConstraint("clave_idempotencia", name="uq_evento_acceso_clave_idempotencia"),
        Index("ix_evento_acceso_secuencia", "id_persona", "resultado",
              "fecha_hora_ocurrencia", "id_evento_acceso"),
        Index("ix_evento_acceso_fecha", "fecha_hora_ocurrencia", "id_evento_acceso"),
        Index("ix_evento_acceso_alertas", "tipo_incidencia_secuencia",
              "fecha_hora_ocurrencia", "id_evento_acceso"),
        Index("ix_evento_acceso_punto_fecha", "id_punto_acceso", "fecha_hora_ocurrencia"),
        Index("ix_evento_acceso_registrador", "id_usuario_registrador"),
        Index("ix_evento_acceso_dispositivo", "id_dispositivo"),
        {"mysql_engine": "InnoDB"},
    )

    id_evento_acceso: Mapped[int] = mapped_column(ENTERO_ID, primary_key=True, autoincrement=True)
    id_persona: Mapped[int | None] = mapped_column(ENTERO_ID, ForeignKey(
        "persona.id_persona", name="fk_evento_acceso_persona", ondelete="RESTRICT"), nullable=True)
    id_punto_acceso: Mapped[int] = mapped_column(ENTERO_ID, ForeignKey(
        "punto_acceso.id_punto_acceso", name="fk_evento_acceso_punto", ondelete="RESTRICT"), nullable=False)
    tipo_movimiento: Mapped[str] = mapped_column(MOVIMIENTO_SQL, nullable=False)
    resultado: Mapped[str] = mapped_column(RESULTADO_SQL, nullable=False)
    metodo_registro: Mapped[str] = mapped_column(METODO_SQL, nullable=False)
    id_usuario_registrador: Mapped[int | None] = mapped_column(ENTERO_ID, ForeignKey(
        "usuario_plataforma.id_usuario", name="fk_evento_acceso_registrador", ondelete="RESTRICT"),
        nullable=True)
    fecha_hora_ocurrencia: Mapped[datetime] = mapped_column(FECHA_UTC, nullable=False)
    tipo_incidencia_secuencia: Mapped[str | None] = mapped_column(INCIDENCIA_SQL, nullable=True)
    id_dispositivo: Mapped[int | None] = mapped_column(ENTERO_ID, ForeignKey(
        "dispositivo_edge.id_dispositivo", name="fk_evento_acceso_dispositivo", ondelete="RESTRICT"),
        nullable=True)
    clave_idempotencia: Mapped[str | None] = mapped_column(CLAVE_UUID, nullable=True)


class RepositorioEventosSQLAlchemy:
    """El bloqueo de Persona precede la primera snapshot de eventos."""

    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def actor_vigente(self, id_usuario: int, rol: str) -> bool:
        fila = self.sesion.execute(select(UsuarioPlataformaModelo.estado, RolModelo.nombre)
            .join(RolModelo, UsuarioPlataformaModelo.id_rol == RolModelo.id_rol)
            .where(UsuarioPlataformaModelo.id_usuario == id_usuario)
            .with_for_update(read=True)).one_or_none()
        return fila is not None and tuple(fila) == ("ACTIVO", rol)

    def bloquear_persona(self, id_persona: int) -> str | None:
        return self.sesion.scalar(select(PersonaModelo.estado).where(
            PersonaModelo.id_persona == id_persona).with_for_update())

    def bloquear_punto(self, id_punto: int) -> str | None:
        return self.sesion.scalar(select(PuntoAccesoModelo.estado).where(
            PuntoAccesoModelo.id_punto_acceso == id_punto).with_for_update(read=True))

    def por_clave(self, clave: str) -> EventoAcceso | None:
        # La transacción empieza limpia. No bloquear una clave ausente evita gap locks
        # entre Personas diferentes; UNIQUE resuelve la carrera al insertar.
        modelo = self.sesion.scalar(select(EventoAccesoModelo).where(
            EventoAccesoModelo.clave_idempotencia == clave)
            .execution_options(populate_existing=True))
        return self._dominio(modelo) if modelo is not None else None

    def ultimo_autorizado(self, id_persona: int, inicio: datetime, fin: datetime) -> str | None:
        return self.sesion.scalar(select(EventoAccesoModelo.tipo_movimiento).where(
            EventoAccesoModelo.id_persona == id_persona,
            EventoAccesoModelo.resultado == "AUTORIZADO",
            EventoAccesoModelo.fecha_hora_ocurrencia >= _sin_zona(inicio),
            EventoAccesoModelo.fecha_hora_ocurrencia < _sin_zona(fin),
        ).order_by(EventoAccesoModelo.fecha_hora_ocurrencia.desc(),
                   EventoAccesoModelo.id_evento_acceso.desc()).limit(1))

    def agregar(self, evento: EventoAcceso) -> EventoAcceso:
        modelo = EventoAccesoModelo(
            id_persona=evento.id_persona, id_punto_acceso=evento.id_punto_acceso,
            tipo_movimiento=evento.tipo_movimiento, resultado=evento.resultado,
            metodo_registro=evento.metodo_registro,
            id_usuario_registrador=evento.id_usuario_registrador,
            fecha_hora_ocurrencia=_sin_zona(evento.fecha_hora_ocurrencia),
            tipo_incidencia_secuencia=evento.tipo_incidencia_secuencia,
            id_dispositivo=evento.id_dispositivo, clave_idempotencia=evento.clave_idempotencia,
        )
        self.sesion.add(modelo)
        try:
            self.sesion.flush()
        except IntegrityError as error:
            codigo = getattr(error.orig, "args", (None,))[0]
            if codigo == 1062 or "UNIQUE constraint failed" in str(error.orig):
                raise ClaveEnCarrera from error
            raise PersistenciaAccesoError("Integridad de EventoAcceso rechazada.") from error
        return self._dominio(modelo)

    def buscar_personas(self, *, criterio: str, valor: str) -> list[dict]:
        consulta = select(PersonaModelo).where(PersonaModelo.estado == "ACTIVO")
        if criterio == "documento":
            consulta = consulta.where(PersonaModelo.numero_documento == valor)
        elif criterio == "institucional":
            consulta = consulta.where(PersonaModelo.identificador_institucional == valor)
        else:
            prefijo = valor.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            consulta = consulta.where(
                PersonaModelo.primer_nombre.ilike(prefijo, escape="\\")
                | PersonaModelo.primer_apellido.ilike(prefijo, escape="\\")
            )
        modelos = self.sesion.scalars(consulta.order_by(PersonaModelo.id_persona).limit(20)).all()
        return [{"id_persona": p.id_persona,
                 "nombre": " ".join(filter(None, (p.primer_nombre, p.segundo_nombre,
                                                    p.primer_apellido, p.segundo_apellido))),
                 "tipo_documento": p.tipo_documento,
                 "documento_final": p.numero_documento[-4:]}
                for p in modelos]

    def historial_operador(self, *, inicio: datetime, fin: datetime,
                           limite: int, desplazamiento: int) -> list[dict]:
        filas = self.sesion.execute(select(
            EventoAccesoModelo.tipo_movimiento, EventoAccesoModelo.resultado,
            EventoAccesoModelo.fecha_hora_ocurrencia,
        ).where(EventoAccesoModelo.fecha_hora_ocurrencia >= _sin_zona(inicio),
                EventoAccesoModelo.fecha_hora_ocurrencia < _sin_zona(fin))
          .order_by(EventoAccesoModelo.fecha_hora_ocurrencia.desc(),
                    EventoAccesoModelo.id_evento_acceso.desc())
          .limit(limite).offset(desplazamiento)).all()
        return [{"tipo_movimiento": movimiento, "resultado": resultado,
                 "hora_local_aproximada": _con_zona(fecha).astimezone(BOGOTA)
                    .replace(minute=0, second=0, microsecond=0).isoformat()}
                for movimiento, resultado, fecha in filas]

    @staticmethod
    def _aplicar_filtros(consulta, filtros: dict):
        columnas = {"id_persona": EventoAccesoModelo.id_persona,
                    "id_punto_acceso": EventoAccesoModelo.id_punto_acceso,
                    "tipo_movimiento": EventoAccesoModelo.tipo_movimiento,
                    "resultado": EventoAccesoModelo.resultado,
                    "tipo_incidencia_secuencia": EventoAccesoModelo.tipo_incidencia_secuencia}
        for nombre, columna in columnas.items():
            if nombre in filtros:
                consulta = consulta.where(columna == filtros[nombre])
        if "desde" in filtros:
            consulta = consulta.where(EventoAccesoModelo.fecha_hora_ocurrencia >= _sin_zona(filtros["desde"]))
        if "hasta" in filtros:
            consulta = consulta.where(EventoAccesoModelo.fecha_hora_ocurrencia < _sin_zona(filtros["hasta"]))
        return consulta

    @staticmethod
    def _ampliado(fila) -> dict:
        evento, persona, punto, actor = fila
        return {"id_evento_acceso": evento.id_evento_acceso,
                "id_persona": evento.id_persona,
                "nombre_persona": (" ".join(filter(None, (persona.primer_nombre,
                    persona.segundo_nombre, persona.primer_apellido, persona.segundo_apellido)))
                    if persona is not None else None),
                "tipo_documento": persona.tipo_documento if persona is not None else None,
                "numero_documento": persona.numero_documento if persona is not None else None,
                "id_punto_acceso": evento.id_punto_acceso, "punto": punto.nombre,
                "id_usuario_registrador": evento.id_usuario_registrador,
                "usuario_registrador": actor.login if actor is not None else None,
                "tipo_movimiento": evento.tipo_movimiento, "resultado": evento.resultado,
                "metodo_registro": evento.metodo_registro,
                "fecha_hora_ocurrencia": _con_zona(evento.fecha_hora_ocurrencia).isoformat(),
                "tipo_incidencia_secuencia": evento.tipo_incidencia_secuencia,
                "id_dispositivo": evento.id_dispositivo}

    def _consulta_ampliada(self):
        return (select(EventoAccesoModelo, PersonaModelo, PuntoAccesoModelo,
                       UsuarioPlataformaModelo)
                .outerjoin(PersonaModelo, EventoAccesoModelo.id_persona == PersonaModelo.id_persona)
                .join(PuntoAccesoModelo,
                      EventoAccesoModelo.id_punto_acceso == PuntoAccesoModelo.id_punto_acceso)
                .outerjoin(UsuarioPlataformaModelo,
                           EventoAccesoModelo.id_usuario_registrador == UsuarioPlataformaModelo.id_usuario))

    def historial_admin(self, *, limite: int, desplazamiento: int, filtros: dict) -> list[dict]:
        consulta = self._aplicar_filtros(self._consulta_ampliada(), filtros)
        filas = self.sesion.execute(consulta.order_by(
            EventoAccesoModelo.fecha_hora_ocurrencia.desc(), EventoAccesoModelo.id_evento_acceso.desc()
        ).limit(limite).offset(desplazamiento)).all()
        return [self._ampliado(fila) for fila in filas]

    def alertas_operador(self, *, inicio: datetime, fin: datetime) -> dict[str, int]:
        filas = self.sesion.execute(select(EventoAccesoModelo.tipo_incidencia_secuencia,
            func.count()).where(
                EventoAccesoModelo.tipo_incidencia_secuencia.is_not(None),
                EventoAccesoModelo.fecha_hora_ocurrencia >= _sin_zona(inicio),
                EventoAccesoModelo.fecha_hora_ocurrencia < _sin_zona(fin),
            ).group_by(EventoAccesoModelo.tipo_incidencia_secuencia)).all()
        return {tipo: cantidad for tipo, cantidad in filas}

    def alertas_admin(self, *, limite: int, desplazamiento: int, filtros: dict) -> list[dict]:
        consulta = self._aplicar_filtros(self._consulta_ampliada().where(
            EventoAccesoModelo.tipo_incidencia_secuencia.is_not(None)), filtros)
        filas = self.sesion.execute(consulta.order_by(
            EventoAccesoModelo.fecha_hora_ocurrencia.desc(), EventoAccesoModelo.id_evento_acceso.desc()
        ).limit(limite).offset(desplazamiento)).all()
        return [self._ampliado(fila) for fila in filas]

    def incidencia_detalle(self, id_evento: int) -> dict | None:
        fila = self.sesion.execute(self._consulta_ampliada().where(
            EventoAccesoModelo.id_evento_acceso == id_evento,
            EventoAccesoModelo.tipo_incidencia_secuencia.is_not(None))).one_or_none()
        return self._ampliado(fila) if fila is not None else None

    @staticmethod
    def _dominio(modelo: EventoAccesoModelo) -> EventoAcceso:
        return EventoAcceso(id_evento_acceso=modelo.id_evento_acceso,
            id_persona=modelo.id_persona, id_punto_acceso=modelo.id_punto_acceso,
            tipo_movimiento=modelo.tipo_movimiento, resultado=modelo.resultado,
            metodo_registro=modelo.metodo_registro,
            id_usuario_registrador=modelo.id_usuario_registrador,
            fecha_hora_ocurrencia=_con_zona(modelo.fecha_hora_ocurrencia),
            tipo_incidencia_secuencia=modelo.tipo_incidencia_secuencia,
            id_dispositivo=modelo.id_dispositivo, clave_idempotencia=modelo.clave_idempotencia)


class UnidadTrabajoEventosSQLAlchemy:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def iniciar(self) -> None:
        # El guard IAM puede haber abierto una transacción de lectura REPEATABLE READ.
        self.sesion.rollback()

    def confirmar(self) -> None:
        self.sesion.commit()

    def revertir(self) -> None:
        self.sesion.rollback()
