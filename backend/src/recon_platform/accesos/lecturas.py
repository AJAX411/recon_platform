"""Consultas acotadas de Accesos para el puerto público de reporting."""

from datetime import datetime

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import aliased

from recon_platform.accesos.modelos_eventos import EventoAccesoModelo as Evento
from recon_platform.accesos.repositorio_eventos import RepositorioEventosSQLAlchemy, _sin_zona
from recon_platform.accesos.contratos_consultas import ResumenAccesos


class LecturaAccesosSQLAlchemy:
    def __init__(self, sesion) -> None:
        self.sesion = sesion

    @staticmethod
    def _jornada(inicio: datetime, fin: datetime, corte: datetime):
        return (Evento.fecha_hora_ocurrencia >= _sin_zona(inicio),
                Evento.fecha_hora_ocurrencia < _sin_zona(fin),
                Evento.fecha_hora_ocurrencia <= _sin_zona(corte))

    def resumen(self, inicio: datetime, fin: datetime, corte: datetime) -> ResumenAccesos:
        entradas, salidas = self.sesion.execute(select(
            func.coalesce(func.sum(case((Evento.tipo_movimiento == "ENTRADA", 1), else_=0)), 0),
            func.coalesce(func.sum(case((Evento.tipo_movimiento == "SALIDA", 1), else_=0)), 0),
        ).where(Evento.resultado == "AUTORIZADO", *self._jornada(inicio, fin, corte))).one()
        posterior = aliased(Evento)
        # Anti-exists: un único último autorizado por Persona, inclusive en empates.
        hay_posterior = exists(select(posterior.id_evento_acceso).where(
            posterior.id_persona == Evento.id_persona,
            posterior.resultado == "AUTORIZADO",
            posterior.fecha_hora_ocurrencia <= _sin_zona(corte),
            or_(posterior.fecha_hora_ocurrencia > Evento.fecha_hora_ocurrencia,
                and_(posterior.fecha_hora_ocurrencia == Evento.fecha_hora_ocurrencia,
                     posterior.id_evento_acceso > Evento.id_evento_acceso)),
        ))
        conocidos, dentro = self.sesion.execute(select(
            func.count(),
            func.coalesce(func.sum(case((Evento.tipo_movimiento == "ENTRADA", 1), else_=0)), 0),
        ).where(Evento.resultado == "AUTORIZADO", Evento.id_persona.is_not(None),
                Evento.fecha_hora_ocurrencia <= _sin_zona(corte), ~hay_posterior)).one()
        return ResumenAccesos(int(entradas), int(salidas), int(dentro), int(conocidos))

    def incidencias(self, inicio: datetime, fin: datetime, corte: datetime) -> dict[str, int]:
        filas = self.sesion.execute(select(Evento.tipo_incidencia_secuencia, func.count())
            .where(Evento.tipo_incidencia_secuencia.is_not(None),
                   *self._jornada(inicio, fin, corte))
            .group_by(Evento.tipo_incidencia_secuencia)).all()
        return dict(filas)

    def movimientos(self, inicio: datetime, fin: datetime, corte: datetime,
                    *, reducido: bool) -> list[dict]:
        eventos = RepositorioEventosSQLAlchemy(self.sesion)
        # Los instantes del esquema tienen precisión de microsegundos. El límite
        # inclusivo se aplica directamente en SQL, sin sumar un microsegundo a t.
        if reducido:
            from recon_platform.accesos.evento_acceso import BOGOTA
            from recon_platform.accesos.repositorio_eventos import _con_zona

            filas = self.sesion.execute(select(Evento.tipo_movimiento, Evento.resultado,
                Evento.fecha_hora_ocurrencia).where(*self._jornada(inicio, fin, corte))
                .order_by(Evento.fecha_hora_ocurrencia.desc(), Evento.id_evento_acceso.desc())
                .limit(10)).all()
            return [{"tipo_movimiento": m, "resultado": r,
                     "hora_local_aproximada": _con_zona(f).astimezone(BOGOTA)
                         .replace(minute=0, second=0, microsecond=0).isoformat()}
                    for m, r, f in filas]
        filas = self.sesion.execute(eventos._consulta_ampliada()
            .where(Evento.fecha_hora_ocurrencia <= _sin_zona(corte))
            .order_by(Evento.fecha_hora_ocurrencia.desc(), Evento.id_evento_acceso.desc())
            .limit(10)).all()
        return [eventos._ampliado(fila) for fila in filas]
