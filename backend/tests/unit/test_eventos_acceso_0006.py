"""Comportamiento funcional y HTTP de 0006 con SQLite efímero."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from recon_platform.accesos import eventos_api
from recon_platform.accesos.eventos_aplicacion import ActorAcceso, RegistrarEventoManual
from recon_platform.accesos.eventos_dominio import incidencia_secuencia, jornada_utc
from recon_platform.accesos.eventos_infraestructura import (
    EventoAccesoModelo, RepositorioEventosSQLAlchemy, UnidadTrabajoEventosSQLAlchemy,
)
from recon_platform.auditoria.infraestructura import (
    EventoAuditoriaModelo, RepositorioEventosSQLAlchemy as RepositorioAuditoria,
)
from recon_platform.accesos.infraestructura import PuntoAccesoModelo
from recon_platform.extensions import db
from recon_platform.identidad.aplicacion.casos_de_uso import CrearUsuarioPlataforma
from recon_platform.identidad.infraestructura.modelos import UsuarioPlataformaModelo
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy
from recon_platform.personas.infraestructura.modelos import PersonaModelo, TipoPersonaModelo

from test_autenticacion_http import CLAVE, _login, entorno  # noqa: F401

BASE = "/api/v1/eventos-acceso"


# La fixture importada se inyecta por nombre; Ruff ve el parámetro como redefinición.
@pytest.fixture
def escenario(entorno, monkeypatch):  # noqa: F811
    app, cliente, _, superadmin_id, operador_id = entorno
    reloj = [datetime(2026, 10, 22, 14, 0, tzinfo=UTC)]
    monkeypatch.setattr(eventos_api, "_reloj", lambda: reloj[0])
    with app.app_context():
        db.create_all()
        db.session.add(TipoPersonaModelo(nombre="VISITANTE", estado="ACTIVO"))
        db.session.commit()
        tipo_id = db.session.scalar(select(TipoPersonaModelo.id_tipo_persona))
        db.session.add_all([
            PersonaModelo(id_tipo_persona=tipo_id, primer_nombre="Ana", primer_apellido="Ficticia",
                tipo_documento="CC", numero_documento="FICTICIO-0001", estado="ACTIVO"),
            PersonaModelo(id_tipo_persona=tipo_id, primer_nombre="Ana", primer_apellido="Ficticia",
                tipo_documento="TI", numero_documento="FICTICIO-0002", estado="ACTIVO"),
            PuntoAccesoModelo(codigo="P-0006", nombre="Punto ficticio", estado="ACTIVO"),
        ])
        db.session.commit()
        personas = db.session.scalars(select(PersonaModelo.id_persona).order_by(PersonaModelo.id_persona)).all()
        punto = db.session.scalar(select(PuntoAccesoModelo.id_punto_acceso))
        admin = CrearUsuarioPlataforma(RepositorioIAMSQLAlchemy(db.session),
            UnidadTrabajoIAMSQLAlchemy(db.session)).ejecutar(actor_id=superadmin_id,
                login="administrador.0006", contrasena=CLAVE, rol_nombre="ADMINISTRADOR")
    return app, cliente, reloj, personas, punto, superadmin_id, admin.id_usuario, operador_id


def _cliente(app, login="admin.ficticio"):
    cliente = app.test_client()
    estado, csrf = _login(cliente, login)
    assert estado == 200 and csrf
    return cliente, {"X-CSRF-Token": csrf}


def _registrar(cliente, headers, persona, punto, movimiento="ENTRADA", clave=None):
    return cliente.post(BASE + "/manual", json={"id_persona": persona,
        "id_punto_acceso": punto, "tipo_movimiento": movimiento},
        headers={**headers, "Idempotency-Key": clave or str(uuid4())})


def _conteo(app, modelo):
    with app.app_context():
        return db.session.scalar(select(func.count()).select_from(modelo))


@pytest.mark.parametrize("ultimo,nuevo,esperado", [
    (None, "ENTRADA", None), (None, "SALIDA", "SALIDA_SIN_ENTRADA_DEL_DIA"),
    ("ENTRADA", "ENTRADA", "ENTRADA_REPETIDA"), ("ENTRADA", "SALIDA", None),
    ("SALIDA", "ENTRADA", None), ("SALIDA", "SALIDA", "SALIDA_REPETIDA"),
])
def test_regla_de_secuencia(ultimo, nuevo, esperado):
    assert incidencia_secuencia(ultimo, nuevo) == esperado


def test_jornada_bogota_en_cruce_utc():
    antes = datetime(2026, 10, 23, 4, 59, 59, tzinfo=UTC)
    despues = datetime(2026, 10, 23, 5, 0, tzinfo=UTC)
    assert jornada_utc(antes) == (datetime(2026, 10, 22, 5, tzinfo=UTC),
                                  datetime(2026, 10, 23, 5, tzinfo=UTC))
    assert jornada_utc(despues) == (datetime(2026, 10, 23, 5, tzinfo=UTC),
                                    datetime(2026, 10, 24, 5, tzinfo=UTC))


def test_tres_roles_secuencia_y_auditoria(escenario):
    app, _, reloj, personas, punto, _, _, _ = escenario
    superadmin, h_super = _cliente(app)
    admin, h_admin = _cliente(app, "administrador.0006")
    operador, h_operador = _cliente(app, "operador.ficticio")
    clientes = [(superadmin, h_super), (admin, h_admin), (operador, h_operador)]
    movimientos = ["ENTRADA", "SALIDA", "ENTRADA", "ENTRADA", "SALIDA", "SALIDA"]
    incidencias = [None, None, None, "ENTRADA_REPETIDA", None, "SALIDA_REPETIDA"]
    for (cliente, headers), movimiento, incidencia in zip(
        (clientes * 2), movimientos, incidencias, strict=True
    ):
        respuesta = _registrar(cliente, headers, personas[0], punto, movimiento)
        assert respuesta.status_code == 201
        assert respuesta.json["resultado"] == "AUTORIZADO"
        assert respuesta.json["metodo_registro"] == "MANUAL"
        assert respuesta.json["id_dispositivo"] is None
        assert respuesta.json["tipo_incidencia_secuencia"] == incidencia
    reloj[0] = datetime(2026, 10, 23, 5, 0, tzinfo=UTC)
    assert _registrar(superadmin, h_super, personas[0], punto).json["tipo_incidencia_secuencia"] is None
    assert _conteo(app, EventoAccesoModelo) == 7
    with app.app_context():
        exitos = db.session.scalars(select(EventoAuditoriaModelo).where(
            EventoAuditoriaModelo.accion == "REGISTRAR_EVENTO_ACCESO_MANUAL",
            EventoAuditoriaModelo.resultado == "EXITOSO")).all()
        assert len(exitos) == 7


def test_reintento_tras_cambio_de_estado_y_clave_de_otro_actor(escenario):
    app, _, _, personas, punto, _, _, operador_id = escenario
    operador, headers = _cliente(app, "operador.ficticio")
    clave = str(uuid4())
    primera = _registrar(operador, headers, personas[0], punto, clave=clave)
    assert primera.status_code == 201
    with app.app_context():
        db.session.get(PersonaModelo, personas[0]).estado = "INACTIVO"
        db.session.get(PuntoAccesoModelo, punto).estado = "INACTIVO"
        db.session.commit()
    repetida = _registrar(operador, headers, personas[0], punto, clave=clave)
    assert repetida.status_code == 200 and repetida.json == primera.json
    assert repetida.headers["Idempotent-Replay"] == "true"
    assert _registrar(operador, headers, personas[0], punto).status_code == 404
    assert _registrar(operador, headers, personas[1], punto).status_code == 404
    assert _registrar(operador, headers, personas[0], punto, "SALIDA", clave).status_code == 409
    admin, h_admin = _cliente(app)
    assert _registrar(admin, h_admin, personas[0], punto, clave=clave).status_code == 409
    assert operador.post(BASE + "/manual", json={"id_persona": personas[0],
        "id_punto_acceso": punto, "tipo_movimiento": "ENTRADA"},
        headers={"Idempotency-Key": clave}).status_code == 403
    assert _conteo(app, EventoAccesoModelo) == 1
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(EventoAuditoriaModelo).where(
            EventoAuditoriaModelo.accion == "REGISTRAR_EVENTO_ACCESO_MANUAL",
            EventoAuditoriaModelo.resultado == "EXITOSO")) == 1
        db.session.get(UsuarioPlataformaModelo, operador_id).estado = "INACTIVO"
        db.session.commit()
    assert _registrar(operador, headers, personas[0], punto, clave=clave).status_code == 401


def test_salidas_iniciales_y_rechazado_no_cambia_secuencia(escenario):
    app, _, _, personas, punto, _, _, _ = escenario
    cliente, headers = _cliente(app)
    salida = _registrar(cliente, headers, personas[0], punto, "SALIDA")
    assert salida.status_code == 201
    assert salida.json["tipo_incidencia_secuencia"] == "SALIDA_SIN_ENTRADA_DEL_DIA"
    with app.app_context():
        db.session.add(EventoAccesoModelo(id_persona=personas[1], id_punto_acceso=punto,
            tipo_movimiento="SALIDA", resultado="RECHAZADO", metodo_registro="FACIAL",
            fecha_hora_ocurrencia=datetime(2026, 10, 22, 13, 30)))
        db.session.commit()
    segunda = _registrar(cliente, headers, personas[1], punto, "SALIDA")
    assert segunda.status_code == 201
    assert segunda.json["tipo_incidencia_secuencia"] == "SALIDA_SIN_ENTRADA_DEL_DIA"


def test_entrada_de_ayer_no_fabrica_salida_al_iniciar_hoy(escenario):
    app, _, reloj, personas, punto, _, _, _ = escenario
    cliente, headers = _cliente(app)
    primera = _registrar(cliente, headers, personas[0], punto)
    assert primera.status_code == 201
    reloj[0] = datetime(2026, 10, 23, 5, 0, tzinfo=UTC)
    segunda = _registrar(cliente, headers, personas[0], punto)
    assert segunda.status_code == 201
    assert segunda.json["tipo_incidencia_secuencia"] is None
    assert _conteo(app, EventoAccesoModelo) == 2


def test_busqueda_homonimos_y_validaciones_de_registro(escenario):
    app, _, _, personas, punto, _, _, _ = escenario
    operador, headers = _cliente(app, "operador.ficticio")
    busqueda = operador.get(BASE + "/personas-elegibles?criterio=nombre&valor=Ana")
    assert busqueda.status_code == 200
    assert {p["id_persona"] for p in busqueda.json["personas"]} == set(personas)
    assert all("numero_documento" not in p for p in busqueda.json["personas"])
    assert operador.get("/api/v1/personas").status_code == 403
    for campo, valor in (("resultado", "AUTORIZADO"), ("metodo_registro", "FACIAL"),
                         ("id_usuario_registrador", 999), ("fecha_hora_ocurrencia", "2020-01-01T00:00:00Z"),
                         ("id_dispositivo", 1)):
        cuerpo = {"id_persona": personas[0], "id_punto_acceso": punto,
                  "tipo_movimiento": "ENTRADA", campo: valor}
        assert operador.post(BASE + "/manual", json=cuerpo,
            headers={**headers, "Idempotency-Key": str(uuid4())}).status_code == 400
    for invalido in ("OTRO", [], None):
        assert operador.post(BASE + "/manual", json={"id_persona": personas[0],
            "id_punto_acceso": punto, "tipo_movimiento": invalido},
            headers={**headers, "Idempotency-Key": str(uuid4())}).status_code == 400
    assert _registrar(operador, headers, 999999, punto).status_code == 404
    assert _registrar(operador, headers, personas[0], 999999).status_code == 404
    assert _conteo(app, EventoAccesoModelo) == 0


def test_historial_y_alertas_privados_con_detalle_admin(escenario):
    app, _, _, personas, punto, _, _, _ = escenario
    operador, headers = _cliente(app, "operador.ficticio")
    evento = _registrar(operador, headers, personas[0], punto, "SALIDA")
    assert evento.status_code == 201
    historial = operador.get(BASE + "/historial")
    assert historial.status_code == 200
    fila = historial.json["eventos"][0]
    assert set(fila) == {"tipo_movimiento", "resultado",
                         "hora_local_aproximada"}
    assert fila["hora_local_aproximada"].endswith("09:00:00-05:00")
    alerta = operador.get(BASE + "/alertas")
    assert alerta.json["conteos_por_incidencia"] == {"SALIDA_SIN_ENTRADA_DEL_DIA": 1}
    for ruta in (BASE + "/historial?desde=2020-01-01T00:00:00Z",
                 BASE + "/historial?id_persona=" + str(personas[0]),
                 BASE + "/alertas?id_persona=" + str(personas[0]),
                 BASE + "/incidencias/" + str(evento.json["id_evento_acceso"])):
        assert operador.get(ruta).status_code in {400, 403}
    admin, _ = _cliente(app, "administrador.0006")
    detalle = admin.get(BASE + "/incidencias/" + str(evento.json["id_evento_acceso"]))
    assert detalle.status_code == 200
    assert detalle.json["id_persona"] == personas[0]
    assert detalle.json["id_usuario_registrador"] is not None
    assert admin.get(BASE + "/historial?limite=1").json["eventos"][0]["id_persona"] == personas[0]


def test_operador_solo_historial_del_dia_y_admin_historico(escenario):
    app, _, reloj, personas, punto, _, _, _ = escenario
    operador, headers = _cliente(app, "operador.ficticio")
    assert _registrar(operador, headers, personas[0], punto).status_code == 201
    reloj[0] = datetime(2026, 10, 23, 5, 0, tzinfo=UTC)
    hoy = operador.get(BASE + "/historial")
    assert hoy.status_code == 200 and hoy.json["eventos"] == []
    assert operador.get(BASE + "/alertas").json["conteos_por_incidencia"] == {}
    admin, _ = _cliente(app, "administrador.0006")
    historico = admin.get(BASE + "/historial")
    assert historico.status_code == 200 and len(historico.json["eventos"]) == 1


def test_fallo_auditoria_revierte_evento_y_clave_reutilizable(escenario, monkeypatch):
    app, _, _, personas, punto, _, _, _ = escenario
    cliente, headers = _cliente(app)
    clave = str(uuid4())
    original = RepositorioAuditoria.agregar
    monkeypatch.setattr(RepositorioAuditoria, "agregar",
                        lambda *_: (_ for _ in ()).throw(RuntimeError("fallo ficticio")))
    assert _registrar(cliente, headers, personas[0], punto, clave=clave).status_code == 503
    assert _conteo(app, EventoAccesoModelo) == 0
    monkeypatch.setattr(RepositorioAuditoria, "agregar", original)
    assert _registrar(cliente, headers, personas[0], punto, clave=clave).status_code == 201


def test_caso_de_uso_revalida_rol_actual_sin_confiar_en_actor_de_entrada(escenario):
    app, _, _, personas, punto, _, _, operador_id = escenario
    with app.app_context():
        caso = RegistrarEventoManual(RepositorioEventosSQLAlchemy(db.session),
            RepositorioAuditoria(db.session),
            UnidadTrabajoEventosSQLAlchemy(db.session))
        with pytest.raises(PermissionError):
            caso.ejecutar(actor=ActorAcceso(operador_id, "SUPERADMIN"),
                id_persona=personas[0], id_punto_acceso=punto,
                tipo_movimiento="ENTRADA", clave=str(uuid4()))
        assert db.session.scalar(select(func.count()).select_from(EventoAccesoModelo)) == 0
