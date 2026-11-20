"""Reporting P0 contra SQLite en memoria y dobles; nunca MySQL."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import mysql

from recon_platform.accesos.lecturas import LecturaAccesosSQLAlchemy
from recon_platform.accesos.modelos_eventos import EventoAccesoModelo
from recon_platform.consultas import controlador as api
from recon_platform.consultas.dto import representar_dashboard
from recon_platform.consultas.unidad_lectura import UnidadLecturaSQLAlchemy
from recon_platform.consultas.servicio import ConsultarDashboard
from recon_platform.extensions import db
from recon_platform.personas.lecturas import LecturaPersonasSQLAlchemy
from recon_platform.personas.modelos import PersonaModelo

from test_eventos_acceso_0006 import escenario, _cliente, _registrar  # noqa: F401
from test_autenticacion_http import entorno  # noqa: F401

BASE = "/api/v1/consultas/dashboard"


@pytest.fixture
def datos(escenario, monkeypatch):  # noqa: F811
    app, _, reloj, personas, punto, super_id, admin_id, operador_id = escenario
    monkeypatch.setattr(api, "_reloj", lambda: reloj[0])
    return app, reloj, personas, punto, super_id, admin_id, operador_id


def agregar(app, persona, punto, actor, fecha, movimiento="ENTRADA", resultado="AUTORIZADO", incidencia=None):
    with app.app_context():
        db.session.add(EventoAccesoModelo(id_persona=persona, id_punto_acceso=punto,
            id_usuario_registrador=actor, tipo_movimiento=movimiento, resultado=resultado,
            metodo_registro="FACIAL", fecha_hora_ocurrencia=fecha.replace(tzinfo=None),
            tipo_incidencia_secuencia=incidencia))
        db.session.commit()
    # FACIAL es solo fixture sintética del enumerado; no ejecuta ruta biométrica.


def test_agregados_corte_cruce_bogota_y_empate_sin_resta(datos):
    app, reloj, personas, punto, actor, _, _ = datos
    reloj[0] = datetime(2026, 10, 23, 5, 10, 12, tzinfo=UTC)
    inicio = datetime(2026, 10, 23, 5, tzinfo=UTC)
    agregar(app, personas[0], punto, actor, inicio - timedelta(seconds=1))
    agregar(app, personas[0], punto, actor, inicio, incidencia="ENTRADA_REPETIDA")
    agregar(app, personas[0], punto, actor, inicio, "SALIDA")  # ID mayor gana empate.
    agregar(app, personas[1], punto, actor, inicio, "SALIDA", incidencia="SALIDA_SIN_ENTRADA_DEL_DIA")
    agregar(app, personas[1], punto, actor, reloj[0])  # corte inclusivo
    agregar(app, personas[1], punto, actor, reloj[0], "SALIDA", "RECHAZADO")
    agregar(app, personas[1], punto, actor, reloj[0] + timedelta(microseconds=1), "SALIDA")
    cliente, _ = _cliente(app)
    respuesta = cliente.get(BASE)
    assert respuesta.status_code == 200
    d = respuesta.get_json()
    assert d["metricas"] == {"entradas_hoy": 2, "salidas_hoy": 2,
        "dentro_segun_registros": 1, "personas_registradas": 2}
    assert d["incidencias_hoy"] == 2
    assert d["jornada"] == "2026-10-23"
    assert len(d["ultimos_movimientos"]) == 6
    assert respuesta.headers["Cache-Control"] == "no-store"
    assert d["calidad_datos"]["estado_ocupacion"] == "ESTIMACION"


def test_entrada_nocturna_inactivos_y_dos_puntos_se_conservan(datos):
    from recon_platform.accesos.modelos_puntos import PuntoAccesoModelo

    app, reloj, personas, punto, actor, _, _ = datos
    with app.app_context():
        otro = PuntoAccesoModelo(codigo="P-FICTICIO-2", nombre="Otro punto ficticio", estado="ACTIVO")
        db.session.add(otro)
        db.session.commit()
        segundo = otro.id_punto_acceso
    agregar(app, personas[0], punto, actor, reloj[0] - timedelta(days=1))
    agregar(app, personas[0], segundo, actor, reloj[0] - timedelta(hours=1), incidencia="ENTRADA_REPETIDA")
    agregar(app, personas[1], punto, actor, reloj[0] - timedelta(days=1))
    with app.app_context():
        persona_db = db.session.get(PersonaModelo, personas[1])
        punto_db = db.session.get(PuntoAccesoModelo, punto)
        assert persona_db is not None
        assert punto_db is not None
        persona_db.estado = "INACTIVO"
        punto_db.estado = "INACTIVO"
        db.session.commit()
    cliente, _ = _cliente(app)
    d = cliente.get(BASE).get_json()
    assert d["metricas"]["dentro_segun_registros"] == 2
    assert d["metricas"]["entradas_hoy"] == 1
    assert d["metricas"]["personas_registradas"] == 2


def test_sin_historial_no_equivale_a_fuera_y_calidad_parcial(datos):
    app, reloj, personas, punto, actor, _, _ = datos
    cliente, _ = _cliente(app)
    d = cliente.get(BASE).get_json()
    assert d["metricas"]["entradas_hoy"] == 0
    assert d["metricas"]["dentro_segun_registros"] is None
    assert d["calidad_datos"]["personas_sin_historial"] == 2
    agregar(app, personas[0], punto, actor, reloj[0], "SALIDA", incidencia="SALIDA_SIN_ENTRADA_DEL_DIA")
    d = cliente.get(BASE).get_json()
    assert d["metricas"]["dentro_segun_registros"] == 0
    assert d["calidad_datos"]["personas_sin_historial"] == 1
    assert d["calidad_datos"]["cobertura"] == "HISTORIAL_DISPONIBLE_NO_CERTIFICADO"


def test_base_vacia_cero_comprobado(datos):
    app, _, _, _, _, _, _ = datos
    with app.app_context():
        db.session.query(PersonaModelo).delete()
        db.session.commit()
    cliente, _ = _cliente(app)
    assert cliente.get(BASE).get_json()["metricas"] == {"entradas_hoy": 0, "salidas_hoy": 0,
        "dentro_segun_registros": 0, "personas_registradas": 0}


def test_replay_manual_no_aumenta_contadores_y_limite_diez(datos):
    app, reloj, personas, punto, _, _, _ = datos
    cliente, headers = _cliente(app)
    clave = "11111111-1111-4111-8111-111111111111"
    assert _registrar(cliente, headers, personas[0], punto, clave=clave).status_code == 201
    assert _registrar(cliente, headers, personas[0], punto, clave=clave).status_code == 200
    assert cliente.get(BASE).get_json()["metricas"]["entradas_hoy"] == 1
    for _ in range(11):
        assert _registrar(cliente, headers, personas[0], punto).status_code == 201
    d = cliente.get(BASE).get_json()
    assert d["metricas"]["entradas_hoy"] == 12
    assert d["metricas"]["dentro_segun_registros"] == 1
    assert d["incidencias_hoy"] == 11  # No se toma el tamaño de la página.
    assert len(d["ultimos_movimientos"]) == 10


def test_operador_http_dto_no_identifican_ni_consultan_agregados(datos, monkeypatch):
    app, reloj, personas, punto, actor, _, _ = datos
    agregar(app, personas[0], punto, actor, reloj[0] - timedelta(days=1))
    agregar(app, personas[0], punto, actor, reloj[0], incidencia="ENTRADA_REPETIDA")
    monkeypatch.setattr(LecturaAccesosSQLAlchemy, "resumen", Mock(side_effect=AssertionError("No permitido")))
    monkeypatch.setattr(LecturaPersonasSQLAlchemy, "total", Mock(side_effect=AssertionError("No permitido")))
    cliente, _ = _cliente(app, "operador.ficticio")
    d = cliente.get(BASE).get_json()
    assert "metricas" not in d and d["incidencias_hoy"] == 1
    assert d["calidad_datos"] == {"cobertura": "JORNADA_ACTUAL", "precision_temporal": "HORA"}
    assert len(d["ultimos_movimientos"]) == 1
    assert set(d["ultimos_movimientos"][0]) == {"tipo_movimiento", "resultado", "hora_local_aproximada"}
    assert datetime.fromisoformat(d["generado_en"]).minute == 0
    assert datetime.fromisoformat(d["ultimos_movimientos"][0]["hora_local_aproximada"]).minute == 0
    assert cliente.get(BASE + "?id_persona=1").status_code == 400


def test_sesion_actual_transporte_filtros_y_errores_no_filtran_sql(datos, monkeypatch):
    app, _, _, _, _, _, _ = datos
    assert app.test_client().get(BASE).status_code == 401
    cliente, _ = _cliente(app)
    assert cliente.get(BASE + "?desde=2026-10-22").status_code == 400
    assert cliente.get(BASE, environ_overrides={"REMOTE_ADDR": "192.0.2.20"}).status_code == 403
    monkeypatch.setattr(LecturaPersonasSQLAlchemy, "total", Mock(side_effect=RuntimeError("SQL privado")))
    respuesta = cliente.get(BASE)
    assert respuesta.status_code == 503 and "SQL" not in respuesta.get_data(as_text=True)


def test_servicio_finaliza_lectura_y_dto_lista_blanca(datos):
    app, reloj, _, _, _, _, _ = datos
    with app.app_context():
        unidad = UnidadLecturaSQLAlchemy(db.session)
        servicio = ConsultarDashboard(LecturaAccesosSQLAlchemy(db.session),
            LecturaPersonasSQLAlchemy(db.session), unidad, lambda: reloj[0])
        d = servicio.ejecutar(rol="ADMINISTRADOR")
        assert not db.session().in_transaction()
        # Un adaptador que añade campos nunca amplía la serialización O.
        fila = {"tipo_movimiento": "ENTRADA", "resultado": "AUTORIZADO",
                "hora_local_aproximada": "2026-10-22T09:00:00-05:00", "id_persona": 99,
                "numero_documento": "FICTICIO", "credencial": "NO-SERIALIZAR"}
        resultado = representar_dashboard(replace(d, reducido=True, movimientos=[fila]))
        assert set(resultado["ultimos_movimientos"][0]) == {"tipo_movimiento", "resultado", "hora_local_aproximada"}
        with pytest.raises(PermissionError):
            servicio.ejecutar(rol="OTRO")


def test_consultas_mismo_corte_rollback_y_cobertura_inconsistente():
    from recon_platform.accesos.contratos_consultas import ResumenAccesos

    accesos, personas, unidad = Mock(), Mock(), Mock()
    corte = datetime(2026, 10, 22, 15, 9, 45, tzinfo=UTC)
    accesos.incidencias.return_value = {}
    accesos.movimientos.return_value = []
    accesos.resumen.return_value = ResumenAccesos(0, 0, 3, 3)
    personas.total.return_value = 2
    servicio = ConsultarDashboard(accesos, personas, unidad, lambda: corte)
    d = representar_dashboard(servicio.ejecutar(rol="SUPERADMIN"))
    assert d["metricas"]["dentro_segun_registros"] is None
    assert d["calidad_datos"]["cobertura"] == "INCONSISTENTE"
    assert accesos.resumen.call_args.args == accesos.incidencias.call_args.args
    accesos.movimientos.side_effect = RuntimeError("fallo ficticio")
    with pytest.raises(RuntimeError):
        servicio.ejecutar(rol="SUPERADMIN")
    assert unidad.terminar.call_count == 2


def test_cambio_de_rol_y_desactivacion_se_aplican_a_la_misma_sesion(datos):
    from recon_platform.identidad.servicio_cuentas import CambiarEstadoUsuario, CambiarRolUsuario
    from recon_platform.identidad.repositorio_cuentas import RepositorioIAMSQLAlchemy
    from recon_platform.identidad.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy

    app, _, _, _, super_id, admin_id, _ = datos
    cliente, _ = _cliente(app, "administrador.0006")
    assert "metricas" in cliente.get(BASE).get_json()
    with app.app_context():
        CambiarRolUsuario(RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session))\
            .ejecutar(actor_id=super_id, usuario_id=admin_id, rol_nombre="OPERADOR")
    d = cliente.get(BASE).get_json()
    assert d["alcance"] == "JORNADA_ACTUAL_REDUCIDA" and "metricas" not in d
    with app.app_context():
        CambiarEstadoUsuario(RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session))\
            .ejecutar(actor_id=super_id, usuario_id=admin_id, estado="INACTIVO")
    assert cliente.get(BASE).status_code == 401


def test_openapi_dashboard_y_campos_de_respuesta(datos):
    app, _, _, _, _, _, _ = datos
    contrato = json.loads((Path(__file__).parents[2] / "openapi.json").read_text(encoding="utf-8"))
    schemas = contrato["components"]["schemas"]
    for login, nombre in [("admin.ficticio", "DashboardAdministrativo"),
                          ("operador.ficticio", "DashboardOperador")]:
        cliente, _ = _cliente(app, login)
        d = cliente.get(BASE).get_json()
        assert set(d) == set(schemas[nombre]["required"]) == set(schemas[nombre]["properties"])
    assert "get" in contrato["paths"]["/consultas/dashboard"]


def test_agregados_compilan_mysql_sin_abrir_conexion():
    sesion = Mock()
    sesion.execute.return_value.one.side_effect = [(0, 0), (0, 0)]
    corte = datetime(2026, 10, 22, tzinfo=UTC)
    LecturaAccesosSQLAlchemy(sesion).resumen(corte, corte + timedelta(days=1), corte)
    sql = [str(c.args[0].compile(dialect=mysql.dialect())) for c in sesion.execute.call_args_list]
    assert "EXISTS" in sql[1] and "id_evento_acceso" in sql[1]
    assert "LIMIT" not in sql[0] and "LIMIT" not in sql[1]
