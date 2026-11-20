"""Incremento administrativo con SQLite efímero y sesiones HTTP reales."""

import json
from datetime import UTC

import pytest
from sqlalchemy import func, select

from recon_platform.accesos.servicio_puntos import AdministrarPuntos, PermisoPuntoDenegado
from recon_platform.accesos.punto_acceso import PuntoAcceso
from recon_platform.accesos.modelos_puntos import PuntoAccesoModelo
from recon_platform.accesos.repositorio_puntos import RepositorioPuntosSQLAlchemy
from recon_platform.auditoria.modelos import EventoAuditoriaModelo
from recon_platform.auditoria.repositorio import RepositorioEventosSQLAlchemy
from recon_platform.auditoria.unidad_trabajo import UnidadTrabajoSQLAlchemy
from recon_platform.extensions import db
from recon_platform.identidad.servicio_cuentas import CrearUsuarioPlataforma
from recon_platform.identidad.repositorio_cuentas import RepositorioIAMSQLAlchemy
from recon_platform.identidad.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy
from recon_platform.integracion_edge.modelos import DispositivoEdgeModelo
from recon_platform.integracion_edge.repositorio import RepositorioDispositivosSQLAlchemy
from recon_platform.integracion_edge.dispositivo_edge import DispositivoEdge, permite_nueva_autorizacion

from test_autenticacion_http import CLAVE, _login, entorno  # noqa: F401

PUNTOS = "/api/v1/puntos-acceso"
DISPOSITIVOS = "/api/v1/dispositivos-edge"
AUDITORIA = "/api/v1/auditoria/eventos"


# La fixture importada se inyecta por nombre; Ruff ve el parámetro como redefinición.
@pytest.fixture
def entorno_incremento(entorno):  # noqa: F811
    app, cliente, _, superadmin_id, operador_id = entorno
    with app.app_context():
        PuntoAccesoModelo.__table__.create(db.engine)
        DispositivoEdgeModelo.__table__.create(db.engine)
        EventoAuditoriaModelo.__table__.create(db.engine)
        admin = CrearUsuarioPlataforma(
            RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)
        ).ejecutar(actor_id=superadmin_id, login="administrador.ficticio",
                  contrasena=CLAVE, rol_nombre="ADMINISTRADOR")
        admin_id = admin.id_usuario
    return app, cliente, superadmin_id, admin_id, operador_id


def _autenticar(cliente, login="admin.ficticio"):
    estado, csrf = _login(cliente, login)
    assert estado == 200 and csrf
    return {"X-CSRF-Token": csrf}


def _punto(cliente, headers, codigo="P-01"):
    return cliente.post(PUNTOS, json={"codigo": codigo, "nombre": "Acceso principal",
                                     "descripcion": "Bloque 1"}, headers=headers)


def _dispositivo(cliente, headers, id_punto, codigo="D-01", modo="AUTOMATICO"):
    return cliente.post(DISPOSITIVOS, json={"id_punto_acceso": id_punto, "codigo": codigo,
                                           "nombre": "Nodo de prueba", "modo_operacion": modo}, headers=headers)


def _eventos(app):
    with app.app_context():
        return [(e.accion, e.resultado, e.id_usuario_actor, e.recurso_tipo,
                 e.id_recurso_afectado, e.detalle) for e in db.session.scalars(
                     select(EventoAuditoriaModelo).order_by(EventoAuditoriaModelo.id_auditoria)).all()]


def test_creacion_relacion_consulta_estado_y_modo_con_auditoria(entorno_incremento):
    app, cliente, actor_id, _, _ = entorno_incremento
    headers = _autenticar(cliente)
    punto = _punto(cliente, headers)
    assert punto.status_code == 201 and punto.json["estado"] == "ACTIVO"
    id_punto = punto.json["id_punto_acceso"]
    assert punto.headers["Location"] == f"{PUNTOS}/{id_punto}"
    assert cliente.get(f"{PUNTOS}/{id_punto}").json == punto.json
    assert cliente.get(f"{PUNTOS}?codigo=P-01&estado=ACTIVO").json["puntos"] == [punto.json]
    assert cliente.get(f"{PUNTOS}?codigo=OTRO").json["puntos"] == []
    primero = _dispositivo(cliente, headers, id_punto)
    segundo = _dispositivo(cliente, headers, id_punto, "D-02", "SALIDA")
    assert primero.status_code == segundo.status_code == 201
    assert primero.json["estado"] == "INACTIVO"
    assert primero.json["ultima_comunicacion"] is None
    id_dispositivo = primero.json["id_dispositivo"]
    assert cliente.get(f"{DISPOSITIVOS}/{id_dispositivo}").json == primero.json
    assert len(cliente.get(f"{DISPOSITIVOS}?id_punto_acceso={id_punto}").json["dispositivos"]) == 2
    assert len(cliente.get(f"{DISPOSITIVOS}?modo_operacion=SALIDA").json["dispositivos"]) == 1
    assert cliente.patch(f"{PUNTOS}/{id_punto}", json={"nombre": "Acceso Bloque 1"}, headers=headers).status_code == 200
    assert cliente.patch(f"{PUNTOS}/{id_punto}/estado", json={"estado": "INACTIVO"}, headers=headers).status_code == 200
    assert cliente.get(f"{DISPOSITIVOS}/{id_dispositivo}").json["estado"] == "INACTIVO"
    assert cliente.patch(f"{DISPOSITIVOS}/{id_dispositivo}", json={"nombre": "Nodo A"}, headers=headers).status_code == 200
    assert cliente.patch(f"{DISPOSITIVOS}/{id_dispositivo}/estado", json={"estado": "ACTIVO"}, headers=headers).json["estado"] == "ACTIVO"
    modo = cliente.patch(f"{DISPOSITIVOS}/{id_dispositivo}/modo", json={"modo_operacion": "ENTRADA"}, headers=headers)
    assert modo.status_code == 200 and modo.json["modo_operacion"] == "ENTRADA"
    assert cliente.get(f"{PUNTOS}/{id_punto}").json["estado"] == "INACTIVO"
    eventos = _eventos(app)
    assert [e[0] for e in eventos] == ["CREAR_PUNTO_ACCESO", "CREAR_DISPOSITIVO_EDGE",
        "CREAR_DISPOSITIVO_EDGE", "EDITAR_PUNTO_ACCESO", "CAMBIAR_ESTADO_PUNTO",
        "EDITAR_DISPOSITIVO_EDGE", "CAMBIAR_ESTADO_DISPOSITIVO", "CAMBIAR_MODO_DISPOSITIVO"]
    assert all(e[1] == "EXITOSO" and e[2] == actor_id for e in eventos)
    detalle = eventos[-1][5]
    assert detalle is not None
    assert json.loads(detalle) == {"anterior": "AUTOMATICO", "nuevo": "ENTRADA"}


def test_matriz_de_permisos_y_denegaciones_auditadas(entorno_incremento):
    app, cliente, _, admin_id, operador_id = entorno_incremento
    headers = _autenticar(cliente)
    id_punto = _punto(cliente, headers).json["id_punto_acceso"]
    id_dispositivo = _dispositivo(cliente, headers, id_punto).json["id_dispositivo"]
    admin = app.test_client()
    admin_headers = _autenticar(admin, "administrador.ficticio")
    assert admin.post(PUNTOS, json={"codigo": "P-02", "nombre": "Otro"}, headers=admin_headers).status_code == 201
    assert admin.patch(f"{DISPOSITIVOS}/{id_dispositivo}", json={"nombre": "Nuevo"}, headers=admin_headers).status_code == 200
    assert admin.get(AUDITORIA).status_code == 200
    operador = app.test_client()
    op_headers = _autenticar(operador, "operador.ficticio")
    assert operador.get(PUNTOS).status_code == 200
    assert operador.get(DISPOSITIVOS).status_code == 200
    assert operador.post(PUNTOS, json={"codigo": "P-03", "nombre": "Denegado"}, headers=op_headers).status_code == 403
    assert operador.post(DISPOSITIVOS, json={"id_punto_acceso": id_punto, "codigo": "D-03",
        "nombre": "Denegado", "modo_operacion": "SALIDA"}, headers=op_headers).status_code == 403
    assert operador.patch(f"{PUNTOS}/{id_punto}", json={"nombre": "Denegado"}, headers=op_headers).status_code == 403
    assert operador.patch(f"{DISPOSITIVOS}/{id_dispositivo}", json={"nombre": "Denegado"}, headers=op_headers).status_code == 403
    assert operador.patch(f"{PUNTOS}/{id_punto}/estado", json={"estado": "INACTIVO"}, headers=op_headers).status_code == 200
    assert operador.patch(f"{DISPOSITIVOS}/{id_dispositivo}/estado", json={"estado": "ACTIVO"}, headers=op_headers).status_code == 200
    assert operador.patch(f"{DISPOSITIVOS}/{id_dispositivo}/modo", json={"modo_operacion": "SALIDA"}, headers=op_headers).status_code == 200
    assert operador.get(AUDITORIA).status_code == 403
    eventos = _eventos(app)
    fallos = [e for e in eventos if e[1] == "FALLIDO"]
    assert len(fallos) == 5 and all(e[2] == operador_id for e in fallos)
    assert {e[0] for e in fallos} == {"CREAR_PUNTO_ACCESO", "CREAR_DISPOSITIVO_EDGE",
                                      "EDITAR_PUNTO_ACCESO", "EDITAR_DISPOSITIVO_EDGE",
                                      "CONSULTAR_AUDITORIA"}
    assert all(e[5] == "PERMISO_DENEGADO" for e in fallos)
    with app.app_context():
        assert db.session.scalar(select(PuntoAccesoModelo.nombre).where(
            PuntoAccesoModelo.id_punto_acceso == id_punto)) == "Acceso principal"


def test_validacion_duplicados_fk_y_campos_inmutables(entorno_incremento):
    app, cliente, _, _, _ = entorno_incremento
    headers = _autenticar(cliente)
    id_punto = _punto(cliente, headers).json["id_punto_acceso"]
    id_dispositivo = _dispositivo(cliente, headers, id_punto).json["id_dispositivo"]
    assert _punto(cliente, headers).status_code == 409
    assert _dispositivo(cliente, headers, id_punto).status_code == 409
    assert _dispositivo(cliente, headers, 999, "D-99").status_code == 400
    assert cliente.post(DISPOSITIVOS, json={"id_punto_acceso": id_punto, "codigo": "D-03",
        "nombre": "Sin modo"}, headers=headers).status_code == 400
    for datos in ({"codigo": "P-99"}, {"id_punto_acceso": 999}, {"estado": "INACTIVO"}):
        assert cliente.patch(f"{PUNTOS}/{id_punto}", json=datos, headers=headers).status_code == 400
    for datos in ({"codigo": "D-99"}, {"id_punto_acceso": 999}, {"ultima_comunicacion": "2026-10-20"}):
        assert cliente.patch(f"{DISPOSITIVOS}/{id_dispositivo}", json=datos, headers=headers).status_code == 400
    assert cliente.patch(f"{DISPOSITIVOS}/{id_dispositivo}/modo", json={"modo_operacion": []}, headers=headers).status_code == 400
    assert cliente.patch(f"{DISPOSITIVOS}/{id_dispositivo}/estado", json={"estado": []}, headers=headers).status_code == 400
    assert cliente.patch(f"{PUNTOS}/{id_punto}/estado", json={"estado": []}, headers=headers).status_code == 400
    assert cliente.get(f"{PUNTOS}/{id_punto}").json["codigo"] == "P-01"
    assert cliente.get(f"{DISPOSITIVOS}/{id_dispositivo}").json["id_punto_acceso"] == id_punto
    fallos = [e for e in _eventos(app) if e[1] == "FALLIDO"]
    assert len(fallos) >= 10
    fallo_modo = [e for e in fallos if e[0] == "CAMBIAR_MODO_DISPOSITIVO"]
    detalle = fallo_modo[0][5]
    assert detalle is not None
    assert json.loads(detalle) == {"anterior": "AUTOMATICO", "nuevo": None,
                                            "motivo": "DATOS_INVALIDOS"}


def test_longitudes_requeridos_y_metodos_no_permitidos(entorno_incremento):
    app, cliente, _, _, _ = entorno_incremento
    headers = _autenticar(cliente)
    for datos in (
        {"codigo": "", "nombre": "Nombre"},
        {"codigo": "X" * 21, "nombre": "Nombre"},
        {"codigo": "P-01", "nombre": "N" * 101},
        {"codigo": "P-01", "nombre": "Nombre", "descripcion": "D" * 151},
        {"codigo": "P\n01", "nombre": "Nombre"},
        {"codigo": "P-01"},
        [],
    ):
        assert cliente.post(PUNTOS, json=datos, headers=headers).status_code == 400
    punto = _punto(cliente, headers)
    assert punto.status_code == 201
    id_punto = punto.json["id_punto_acceso"]
    for datos in (
        {"id_punto_acceso": id_punto, "codigo": "X" * 21,
         "nombre": "Nodo", "modo_operacion": "ENTRADA"},
        {"id_punto_acceso": id_punto, "codigo": "D-01",
         "nombre": "N" * 101, "modo_operacion": "ENTRADA"},
        {"id_punto_acceso": id_punto, "codigo": "D-01",
         "nombre": "Nodo", "modo_operacion": "OTRO"},
    ):
        assert cliente.post(DISPOSITIVOS, json=datos, headers=headers).status_code == 400
    assert cliente.delete(f"{PUNTOS}/{id_punto}", headers=headers).status_code == 405
    assert cliente.delete(DISPOSITIVOS, headers=headers).status_code == 405
    with app.app_context():
        assert db.session.scalar(select(DispositivoEdgeModelo.id_dispositivo)) is None


def test_rollback_si_falla_auditoria_y_fallos_sin_mutacion(entorno_incremento, monkeypatch):
    app, cliente, _, _, _ = entorno_incremento
    headers = _autenticar(cliente)
    original = RepositorioEventosSQLAlchemy.agregar
    def fallar(*_args, **_kwargs):
        raise RuntimeError("detalle-secreto-ficticio")
    monkeypatch.setattr(RepositorioEventosSQLAlchemy, "agregar", fallar)
    respuesta = _punto(cliente, headers)
    assert respuesta.status_code == 503
    assert "detalle-secreto-ficticio" not in respuesta.get_data(as_text=True)
    with app.app_context():
        assert db.session.scalar(select(PuntoAccesoModelo.id_punto_acceso)) is None
    monkeypatch.setattr(RepositorioEventosSQLAlchemy, "agregar", original)
    punto = _punto(cliente, headers)
    assert punto.status_code == 201
    id_punto = punto.json["id_punto_acceso"]
    assert cliente.patch(f"{PUNTOS}/{id_punto}/estado", json={"estado": "ILEGAL"}, headers=headers).status_code == 400
    assert cliente.get(f"{PUNTOS}/{id_punto}").json["estado"] == "ACTIVO"
    assert _eventos(app)[-1][1] == "FALLIDO"


def test_auditoria_consulta_filtros_paginacion_y_solo_lectura(entorno_incremento):
    app, cliente, actor_id, _, _ = entorno_incremento
    headers = _autenticar(cliente)
    id_punto = _punto(cliente, headers).json["id_punto_acceso"]
    _dispositivo(cliente, headers, id_punto)
    assert cliente.get(AUDITORIA + "?limite=1").status_code == 200
    pagina = cliente.get(AUDITORIA + "?limite=1").json
    assert pagina["limite"] == 1 and len(pagina["eventos"]) == 1
    assert pagina["eventos"][0]["accion"] == "CREAR_DISPOSITIVO_EDGE"
    assert cliente.get(AUDITORIA + "?desplazamiento=1&limite=1").json["eventos"][0]["accion"] == "CREAR_PUNTO_ACCESO"
    assert len(cliente.get(AUDITORIA + f"?id_usuario_actor={actor_id}&resultado=EXITOSO").json["eventos"]) == 2
    assert len(cliente.get(AUDITORIA + "?recurso_tipo=PUNTO_ACCESO").json["eventos"]) == 1
    assert cliente.get(AUDITORIA + "?desde=2020-01-01T00:00:00%2B00:00").status_code == 200
    for query in ("?limite=0", "?desplazamiento=-1", "?resultado=OTRO",
                  "?desde=2026-10-20", "?accion=x&accion=y", "?desconocido=1"):
        assert cliente.get(AUDITORIA + query).status_code == 400
    assert cliente.post(AUDITORIA, json={"accion": "FALSO"}, headers=headers).status_code == 405
    assert cliente.patch(AUDITORIA, json={"accion": "FALSO"}, headers=headers).status_code == 405
    assert cliente.delete(AUDITORIA, headers=headers).status_code == 405
    assert len(_eventos(app)) == 2


def test_filtros_auditoria_conservan_hasta_inclusivo_y_actor_convertido(entorno_incremento):
    app, cliente, actor_id, _, _ = entorno_incremento
    headers = _autenticar(cliente)
    assert _punto(cliente, headers).status_code == 201
    with app.app_context():
        fecha = db.session.scalar(select(EventoAuditoriaModelo.fecha_hora).where(
            EventoAuditoriaModelo.accion == "CREAR_PUNTO_ACCESO"))
        assert fecha is not None
        corte = fecha.replace(tzinfo=UTC).isoformat()
    respuesta = cliente.get(AUDITORIA, query_string={
        "id_usuario_actor": str(actor_id), "desde": corte, "hasta": corte})
    assert respuesta.status_code == 200
    assert len(respuesta.json["eventos"]) == 1
    assert respuesta.json["eventos"][0]["accion"] == "CREAR_PUNTO_ACCESO"
    assert respuesta.json["eventos"][0]["id_usuario_actor"] == actor_id


def test_sesion_y_csrf_no_generan_auditoria_general(entorno_incremento):
    app, cliente, _, _, _ = entorno_incremento
    assert cliente.get(PUNTOS).status_code == 401
    assert cliente.post(PUNTOS, json={"codigo": "P-01", "nombre": "X"}).status_code == 403
    headers = _autenticar(cliente)
    assert cliente.post(PUNTOS, json={"codigo": "P-01", "nombre": "X"}).status_code == 403
    assert _eventos(app) == []
    assert _punto(cliente, headers).status_code == 201


def test_denegacion_no_se_disfraza_si_falla_auditoria(entorno_incremento, monkeypatch):
    app, _, _, _, _ = entorno_incremento
    operador = app.test_client()
    headers = _autenticar(operador, "operador.ficticio")
    def fallar(*_args, **_kwargs):
        raise RuntimeError("Detalle interno ficticio")
    monkeypatch.setattr("recon_platform.auditoria.servicio.AuditoriaGeneral.registrar_fallo", fallar)
    respuesta = operador.post(PUNTOS, json={"codigo": "P-01", "nombre": "Denegado"}, headers=headers)
    assert respuesta.status_code == 503
    assert "Detalle interno ficticio" not in respuesta.get_data(as_text=True)
    with app.app_context():
        assert db.session.scalar(select(PuntoAccesoModelo.id_punto_acceso)) is None


def test_caso_de_uso_revalida_permiso_fuera_de_http(entorno_incremento):
    app, _, _, _, operador_id = entorno_incremento
    with app.app_context():
        caso = AdministrarPuntos(RepositorioPuntosSQLAlchemy(db.session),
            RepositorioEventosSQLAlchemy(db.session), UnidadTrabajoSQLAlchemy(db.session))
        with pytest.raises(PermisoPuntoDenegado):
            caso.crear(actor_id=operador_id, rol="OPERADOR", punto=PuntoAcceso(codigo="P-01", nombre="X"))
        assert db.session.scalar(select(PuntoAccesoModelo.id_punto_acceso)) is None


def test_estado_administrativo_prepara_regla_de_autorizacion():
    punto = PuntoAcceso(id_punto_acceso=1, codigo="P-01", nombre="Punto")
    dispositivo = DispositivoEdge(id_punto_acceso=1, codigo="D-01", nombre="Nodo",
                                  modo_operacion="AUTOMATICO", estado="ACTIVO")
    assert permite_nueva_autorizacion(punto, dispositivo)
    punto.estado = "INACTIVO"
    assert not permite_nueva_autorizacion(punto, dispositivo)
    punto.estado = "ACTIVO"
    dispositivo.estado = "INACTIVO"
    assert not permite_nueva_autorizacion(punto, dispositivo)
    dispositivo.estado = "ACTIVO"
    dispositivo.id_punto_acceso = 2
    assert not permite_nueva_autorizacion(punto, dispositivo)


@pytest.mark.parametrize("recurso", ["punto", "dispositivo"])
def test_alta_sin_id_devuelto_revierte_recurso_y_auditoria(entorno_incremento, monkeypatch, recurso):
    app, cliente, _, _, _ = entorno_incremento
    headers = _autenticar(cliente)
    original_punto = RepositorioPuntosSQLAlchemy.agregar
    original_dispositivo = RepositorioDispositivosSQLAlchemy.agregar
    id_punto: int | None = None
    if recurso == "punto":
        def punto_sin_id(self: RepositorioPuntosSQLAlchemy, punto: PuntoAcceso) -> PuntoAcceso:
            guardado = original_punto(self, punto)
            guardado.id_punto_acceso = None
            return guardado

        monkeypatch.setattr(RepositorioPuntosSQLAlchemy, "agregar", punto_sin_id)
    else:
        punto = _punto(cliente, headers)
        assert punto.status_code == 201
        id_punto = punto.json["id_punto_acceso"]
        assert isinstance(id_punto, int)

        def dispositivo_sin_id(
            self: RepositorioDispositivosSQLAlchemy, dispositivo: DispositivoEdge,
        ) -> DispositivoEdge:
            guardado = original_dispositivo(self, dispositivo)
            guardado.id_dispositivo = None
            return guardado

        monkeypatch.setattr(RepositorioDispositivosSQLAlchemy, "agregar", dispositivo_sin_id)

    def solicitar():
        if recurso == "punto":
            return _punto(cliente, headers, codigo="SIN-ID-FASE1")
        assert id_punto is not None
        return _dispositivo(cliente, headers, id_punto, codigo="SIN-ID-FASE1")

    auditorias_antes = len(_eventos(app))
    respuesta = solicitar()
    assert respuesta.status_code == 503
    assert respuesta.json == {"error": "La administración no está disponible."}
    with app.app_context():
        modelo = PuntoAccesoModelo if recurso == "punto" else DispositivoEdgeModelo
        assert db.session.scalar(select(func.count()).select_from(modelo).where(
            modelo.codigo == "SIN-ID-FASE1")) == 0
    assert len(_eventos(app)) == auditorias_antes
    monkeypatch.setattr(RepositorioPuntosSQLAlchemy, "agregar", original_punto)
    monkeypatch.setattr(RepositorioDispositivosSQLAlchemy, "agregar", original_dispositivo)
    assert solicitar().status_code == 201
