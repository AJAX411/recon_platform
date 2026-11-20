"""Allowlists de respuesta; nunca serializar objetos/dicts completos por accidente."""

from recon_platform.accesos.evento_acceso import BOGOTA, INCIDENCIAS
from recon_platform.consultas.servicio import Dashboard

REDUCIDOS = ("tipo_movimiento", "resultado", "hora_local_aproximada")
AMPLIADOS = ("id_evento_acceso", "fecha_hora_ocurrencia", "nombre_persona", "punto",
             "tipo_movimiento", "resultado", "tipo_incidencia_secuencia", "usuario_registrador")


def representar_dashboard(d: Dashboard) -> dict:
    conteos = {k: v for k, v in d.incidencias.items() if k in INCIDENCIAS}
    corte = d.corte.astimezone(BOGOTA)
    datos = {"zona_horaria": "America/Bogota",
        "jornada": d.inicio.astimezone(BOGOTA).date().isoformat(),
        "generado_en": (corte.replace(minute=0, second=0, microsecond=0)
                        if d.reducido else corte).isoformat(),
        "alcance": "JORNADA_ACTUAL_REDUCIDA" if d.reducido else "HISTORICO_ADMINISTRATIVO",
        "incidencias_hoy": sum(conteos.values()),
        "conteos_por_incidencia": conteos,
        "ultimos_movimientos": [{k: fila.get(k) for k in (REDUCIDOS if d.reducido else AMPLIADOS)}
                                for fila in d.movimientos[:10]]}
    if d.reducido:
        datos["calidad_datos"] = {"cobertura": "JORNADA_ACTUAL", "precision_temporal": "HORA"}
        return datos
    r, total = d.resumen, d.personas
    if r is None or total is None:
        raise ValueError("Agregados administrativos no disponibles.")
    consistente = 0 <= r.dentro <= r.personas_con_historial <= total
    disponible = consistente and (r.personas_con_historial > 0 or total == 0)
    datos["metricas"] = {"entradas_hoy": r.entradas, "salidas_hoy": r.salidas,
        "personas_registradas": total, "dentro_segun_registros": r.dentro if disponible else None}
    datos["calidad_datos"] = {
        "cobertura": "HISTORIAL_DISPONIBLE_NO_CERTIFICADO" if consistente else "INCONSISTENTE",
        "personas_con_historial": r.personas_con_historial,
        "personas_sin_historial": total - r.personas_con_historial if consistente else None,
        "estado_ocupacion": "ESTIMACION" if disponible else "NO_DISPONIBLE",
        "motivo": ("Estimación del historial disponible; no certifica presencia física ni cobertura inicial."
                   if disponible else "Sin historial autorizado suficiente o cobertura inconsistente."),
    }
    return datos
