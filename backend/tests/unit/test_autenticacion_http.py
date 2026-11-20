"""Flujo HTTP completo con SQLite efímero; no abre conexiones MySQL."""

from datetime import datetime, timedelta
import hashlib
from collections.abc import Iterator

import pytest
from flask import Flask, jsonify, session
from flask.testing import FlaskClient
from sqlalchemy import select

from recon_platform import create_app
from recon_platform.extensions import db
from recon_platform.identidad import seguridad_http as seguridad
from recon_platform.identidad.servicio_cuentas import BootstrapSuperadmin, CambiarEstadoUsuario, CambiarRolUsuario, ConsultarUsuarioPlataforma, CrearUsuarioPlataforma, ListarRoles, ListarUsuariosPlataforma, PermisoDenegado, RestablecerContrasenaUsuario
from recon_platform.identidad.modelos import AuditoriaIAMModelo, RolModelo, SesionUsuarioModelo, UsuarioPlataformaModelo
from recon_platform.identidad.repositorio_cuentas import RepositorioIAMSQLAlchemy
from recon_platform.identidad.repositorio_sesiones import RepositorioSesionesSQLAlchemy
from recon_platform.identidad.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy

CLAVE = "Clave-Ficticia-Prueba-2026!"
INICIO = datetime(2026, 10, 16, 10, 0)


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Flask, FlaskClient, list[datetime], int, int]]:
    monkeypatch.setattr("recon_platform.obtener_uri_mysql", lambda **_: "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "clave-ficticia-unitaria-de-32-caracteres-o-mas")
    monkeypatch.setenv("RECON_LOCAL_HTTP", "1")
    monkeypatch.setenv("RECON_SESSION_COOKIE_SECURE", "0")
    reloj = [INICIO]
    monkeypatch.setattr(seguridad, "ahora_utc", lambda: reloj[0])
    aplicacion = create_app(pruebas=True)

    @aplicacion.get("/api/v1/prueba-admin")
    @seguridad.requerir_roles("SUPERADMIN")
    def solo_superadmin():
        return jsonify({"estado": "permitido"})

    @aplicacion.post("/api/v1/prueba-admin")
    @seguridad.requerir_roles("SUPERADMIN")
    def cambio_superadmin():
        return jsonify({"estado": "permitido"})

    with aplicacion.app_context():
        RolModelo.__table__.create(db.engine)
        UsuarioPlataformaModelo.__table__.create(db.engine)
        AuditoriaIAMModelo.__table__.create(db.engine)
        SesionUsuarioModelo.__table__.create(db.engine)
        db.session.add_all(RolModelo(nombre=nombre) for nombre in (
            "SUPERADMIN", "ADMINISTRADOR", "OPERADOR"
        ))
        db.session.commit()
        repo = RepositorioIAMSQLAlchemy(db.session)
        unidad = UnidadTrabajoIAMSQLAlchemy(db.session)
        admin = BootstrapSuperadmin(repo, unidad).ejecutar(
            login="admin.ficticio", contrasena=CLAVE
        ).usuario
        assert admin.id_usuario is not None
        operador = CrearUsuarioPlataforma(repo, unidad).ejecutar(
            actor_id=admin.id_usuario, login="operador.ficticio",
            contrasena=CLAVE, rol_nombre="OPERADOR",
        )
        assert operador.id_usuario is not None
        ids = admin.id_usuario, operador.id_usuario
    yield aplicacion, aplicacion.test_client(), reloj, *ids


def _csrf(cliente: FlaskClient) -> str:
    respuesta = cliente.get("/api/v1/auth/csrf")
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert isinstance(datos, dict)
    token = datos["csrf_token"]
    assert isinstance(token, str)
    return token


def _login(cliente: FlaskClient, usuario: str, clave: str = CLAVE) -> tuple[int, str | None]:
    csrf = _csrf(cliente)
    respuesta = cliente.post(
        "/api/v1/auth/login", json={"login": usuario, "contrasena": clave},
        headers={"X-CSRF-Token": csrf},
    )
    return respuesta.status_code, respuesta.headers.get("X-CSRF-Token")


def test_login_me_y_cookie_opaca_guardada_solo_como_digest(entorno) -> None:
    aplicacion, cliente, _, admin_id, _ = entorno
    assert cliente.get("/api/v1/auth/me").status_code == 401
    estado, csrf_nuevo = _login(cliente, "admin.ficticio")
    assert estado == 200 and csrf_nuevo is not None
    respuesta = cliente.get("/api/v1/auth/me")
    assert respuesta.json == {
        "id_usuario": admin_id, "login": "admin.ficticio", "rol": "SUPERADMIN"
    }
    cookie = cliente.get_cookie("recon_session", path="/api/v1")
    assert cookie is not None and cookie.http_only and cookie.same_site == "Lax"
    assert not cookie.secure  # Excepción local explícita del fixture.
    with aplicacion.app_context():
        sesiones = db.session.scalars(select(SesionUsuarioModelo)).all()
        assert len(sesiones) == 2
        assert sesiones[0].fecha_revocacion is not None
        assert sesiones[1].digest == hashlib.sha256(cookie.value.encode("ascii")).hexdigest()
        assert cookie.value not in sesiones[1].digest
        assert sesiones[1].id_usuario == admin_id


def test_preparar_csrf_reutiliza_token_valido_y_reemplaza_un_token_invalido(entorno) -> None:
    app, cliente, _, _, _ = entorno
    primera = cliente.get("/api/v1/auth/csrf")
    assert primera.status_code == 200
    cookie = cliente.get_cookie("recon_session", path="/api/v1")
    assert cookie is not None
    token_anterior = cookie.value
    segunda = cliente.get("/api/v1/auth/csrf")
    assert segunda.status_code == 200 and segunda.json == primera.json
    conservada = cliente.get_cookie("recon_session", path="/api/v1")
    assert conservada is not None and conservada.value == token_anterior
    cliente.set_cookie("recon_session", "invalida", path="/api/v1")
    nueva = cliente.get("/api/v1/auth/csrf")
    assert nueva.status_code == 200
    reemplazo = cliente.get_cookie("recon_session", path="/api/v1")
    assert reemplazo is not None and reemplazo.value != token_anterior
    assert reemplazo.http_only and reemplazo.same_site == "Lax"
    with app.app_context():
        assert len(db.session.scalars(select(SesionUsuarioModelo)).all()) == 2


def test_login_con_cuenta_sin_id_falla_503_sin_crear_sesion_autenticada(entorno, monkeypatch):
    app, cliente, _, _, _ = entorno
    csrf = _csrf(cliente)
    original = RepositorioIAMSQLAlchemy.obtener_por_login

    def obtener_sin_id(self: RepositorioIAMSQLAlchemy, login: str):
        cuenta = original(self, login)
        if cuenta is not None:
            cuenta.id_usuario = None
        return cuenta

    monkeypatch.setattr(RepositorioIAMSQLAlchemy, "obtener_por_login", obtener_sin_id)
    respuesta = cliente.post("/api/v1/auth/login",
        json={"login": "admin.ficticio", "contrasena": CLAVE}, headers={"X-CSRF-Token": csrf})
    assert respuesta.status_code == 503
    assert respuesta.json == {"error": "No se pudo completar la autenticación."}
    with app.app_context():
        sesiones = db.session.scalars(select(SesionUsuarioModelo)).all()
        assert len(sesiones) == 1 and sesiones[0].id_usuario is None
    monkeypatch.setattr(RepositorioIAMSQLAlchemy, "obtener_por_login", original)
    assert _login(cliente, "admin.ficticio")[0] == 200


def test_csrf_protege_login_logout_y_cambio_de_estado(entorno) -> None:
    _, cliente, _, _, _ = entorno
    assert cliente.post("/api/v1/auth/login", json={"login": "admin.ficticio", "contrasena": CLAVE}).status_code == 403
    csrf = _csrf(cliente)
    assert cliente.post(
        "/api/v1/auth/login", json={"login": "admin.ficticio", "contrasena": CLAVE},
        headers={"X-CSRF-Token": "0" * 64},
    ).status_code == 403
    assert cliente.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 401
    estado, csrf_autenticado = _login(cliente, "admin.ficticio")
    assert estado == 200
    assert csrf_autenticado is not None
    assert csrf_autenticado != csrf  # Rotación tras login.
    assert cliente.post("/api/v1/prueba-admin").status_code == 403
    assert cliente.post("/api/v1/prueba-admin", headers={"X-CSRF-Token": csrf_autenticado}).status_code == 200
    assert cliente.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 403
    assert cliente.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_autenticado}).status_code == 200
    assert cliente.get("/api/v1/auth/me").status_code == 401


def test_credenciales_erroneas_e_inactivo_no_abren_sesion(entorno) -> None:
    aplicacion, cliente, _, admin_id, operador_id = entorno
    assert _login(cliente, "usuario.inexistente")[0] == 401
    assert _login(cliente, "operador.ficticio", "incorrecta")[0] == 401
    with aplicacion.app_context():
        CambiarEstadoUsuario(
            RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)
        ).ejecutar(actor_id=admin_id, usuario_id=operador_id, estado="INACTIVO")
    assert _login(cliente, "operador.ficticio")[0] == 401
    assert cliente.get("/api/v1/auth/me").status_code == 401


def test_autorizacion_consulta_rol_y_estado_vigentes(entorno) -> None:
    aplicacion, cliente, _, admin_id, operador_id = entorno
    assert cliente.get("/api/v1/prueba-admin").status_code == 401
    assert _login(cliente, "operador.ficticio")[0] == 200
    assert cliente.get("/api/v1/prueba-admin").status_code == 403
    with aplicacion.app_context():
        CambiarRolUsuario(
            RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)
        ).ejecutar(actor_id=admin_id, usuario_id=operador_id, rol_nombre="ADMINISTRADOR")
    assert cliente.get("/api/v1/auth/me").json["rol"] == "ADMINISTRADOR"
    with aplicacion.app_context():
        CambiarEstadoUsuario(
            RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)
        ).ejecutar(actor_id=admin_id, usuario_id=operador_id, estado="INACTIVO")
    assert cliente.get("/api/v1/auth/me").status_code == 401
    with aplicacion.app_context():
        CambiarEstadoUsuario(
            RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)
        ).ejecutar(actor_id=admin_id, usuario_id=operador_id, estado="ACTIVO")
    assert cliente.get("/api/v1/auth/me").status_code == 401


def test_restablecer_clave_revoca_sesiones_previas(entorno) -> None:
    aplicacion, cliente, _, admin_id, operador_id = entorno
    assert _login(cliente, "operador.ficticio")[0] == 200
    with aplicacion.app_context():
        RestablecerContrasenaUsuario(
            RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)
        ).ejecutar(
            actor_id=admin_id, usuario_id=operador_id,
            nueva_contrasena="Otra-Clave-Ficticia-2026!",
        )
    assert cliente.get("/api/v1/auth/me").status_code == 401
    assert _login(cliente, "operador.ficticio")[0] == 401
    assert _login(cliente, "operador.ficticio", "Otra-Clave-Ficticia-2026!")[0] == 200


def test_inactividad_y_duracion_maxima(entorno) -> None:
    _, cliente, reloj, _, _ = entorno
    assert _login(cliente, "admin.ficticio")[0] == 200
    reloj[0] += timedelta(minutes=29)
    assert cliente.get("/api/v1/auth/me").status_code == 200
    reloj[0] += timedelta(minutes=30)
    assert cliente.get("/api/v1/auth/me").status_code == 401

    otro = entorno[0].test_client()
    reloj[0] = INICIO
    assert _login(otro, "admin.ficticio")[0] == 200
    for cuarto in range(1, 32):
        reloj[0] = INICIO + timedelta(minutes=15 * cuarto)
        assert otro.get("/api/v1/auth/me").status_code == 200
    reloj[0] = INICIO + timedelta(hours=8)
    assert otro.get("/api/v1/auth/me").status_code == 401


def test_sesiones_independientes_y_revocacion_selectiva(entorno) -> None:
    aplicacion, primero, _, _, _ = entorno
    segundo = aplicacion.test_client()
    assert _login(primero, "admin.ficticio")[0] == 200
    _, csrf_segundo = _login(segundo, "admin.ficticio")
    assert csrf_segundo is not None
    assert primero.get("/api/v1/auth/me").status_code == 200
    assert segundo.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_segundo}).status_code == 200
    assert segundo.get("/api/v1/auth/me").status_code == 401
    assert primero.get("/api/v1/auth/me").status_code == 200


def test_limite_basico_de_intentos(entorno) -> None:
    _, cliente, reloj, _, _ = entorno
    csrf = _csrf(cliente)
    for _ in range(10):
        respuesta = cliente.post(
            "/api/v1/auth/login", json={"login": "admin.ficticio", "contrasena": "incorrecta"},
            headers={"X-CSRF-Token": csrf},
        )
        assert respuesta.status_code == 401
    bloqueada = cliente.post(
        "/api/v1/auth/login", json={"login": "admin.ficticio", "contrasena": CLAVE},
        headers={"X-CSRF-Token": csrf},
    )
    assert bloqueada.status_code == 429
    assert bloqueada.headers["Retry-After"] == "300"
    reloj[0] += timedelta(minutes=5)
    assert cliente.post(
        "/api/v1/auth/login", json={"login": "admin.ficticio", "contrasena": CLAVE},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200


def test_cookie_segura_por_defecto_y_configuracion_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RECON_SESSION_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("RECON_LOCAL_HTTP", raising=False)
    assert create_app().config["RECON_COOKIE_SECURE"] is True
    monkeypatch.setenv("RECON_SESSION_COOKIE_SECURE", "0")
    with pytest.raises(ValueError, match="desarrollo local"):
        create_app()


def test_cookie_secure_y_ausencia_de_clave_fallan_cerrado(entorno) -> None:
    aplicacion, _, _, _, _ = entorno
    aplicacion.config["RECON_COOKIE_SECURE"] = True
    cliente = aplicacion.test_client()
    assert cliente.get("/api/v1/auth/csrf").status_code == 403
    assert cliente.get("/api/v1/auth/csrf", base_url="https://localhost").status_code == 200
    cookie = cliente.get_cookie("recon_session", path="/api/v1")
    assert cookie is not None and cookie.secure and cookie.http_only
    aplicacion.config["SECRET_KEY"] = None
    assert cliente.get("/api/v1/auth/csrf", base_url="https://localhost").status_code == 503
    assert cliente.get("/api/v1/auth/me", base_url="https://localhost").status_code == 503


@pytest.mark.parametrize(
    ("ruta", "metodo"),
    [
        ("/api/v1/auth/me", "get"),
        ("/api/v1/prueba-admin", "get"),
        ("/api/v1/prueba-admin", "post"),
        ("/api/v1/auth/login", "post"),
        ("/api/v1/auth/logout", "post"),
    ],
)
def test_fallo_de_persistencia_es_503_sin_revelar_detalles(
    entorno, monkeypatch: pytest.MonkeyPatch, ruta: str, metodo: str
) -> None:
    _, cliente, _, _, _ = entorno
    estado, csrf = _login(cliente, "admin.ficticio")
    assert estado == 200 and csrf is not None

    def fallar(_repositorio, _digest):
        raise RuntimeError("detalle-privado-de-conexion")

    monkeypatch.setattr(RepositorioSesionesSQLAlchemy, "obtener", fallar)
    parametros = {"headers": {"X-CSRF-Token": csrf}}
    if ruta.endswith("/login"):
        parametros["json"] = {"login": "admin.ficticio", "contrasena": CLAVE}
    respuesta = getattr(cliente, metodo)(ruta, **parametros)
    assert respuesta.status_code == 503
    assert "detalle-privado-de-conexion" not in respuesta.get_data(as_text=True)
    assert CLAVE not in respuesta.get_data(as_text=True)


def test_fallo_al_consultar_cuenta_tambien_es_503(
    entorno, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, cliente, _, _, _ = entorno
    assert _login(cliente, "admin.ficticio")[0] == 200

    def fallar(_repositorio, _id_usuario):
        raise RuntimeError("detalle-privado-de-cuenta")

    monkeypatch.setattr(RepositorioIAMSQLAlchemy, "obtener_por_id", fallar)
    respuesta = cliente.get("/api/v1/auth/me")
    assert respuesta.status_code == 503
    assert "detalle-privado-de-cuenta" not in respuesta.get_data(as_text=True)


def test_fallo_al_verificar_credenciales_es_503_sin_filtrar_detalles(
    entorno, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, cliente, _, _, _ = entorno
    csrf = _csrf(cliente)

    def fallar(_repositorio, _login):
        raise RuntimeError("detalle-privado-de-autenticacion")

    monkeypatch.setattr(RepositorioIAMSQLAlchemy, "obtener_por_login", fallar)
    respuesta = cliente.post(
        "/api/v1/auth/login", json={"login": "admin.ficticio", "contrasena": CLAVE},
        headers={"X-CSRF-Token": csrf},
    )
    assert respuesta.status_code == 503
    assert "detalle-privado-de-autenticacion" not in respuesta.get_data(as_text=True)
    assert CLAVE not in respuesta.get_data(as_text=True)


def test_excepcion_http_local_rechaza_cliente_remoto(entorno) -> None:
    _, cliente, _, _, _ = entorno
    respuesta = cliente.get(
        "/api/v1/auth/csrf", environ_overrides={"REMOTE_ADDR": "192.0.2.9"}
    )
    assert respuesta.status_code == 403
    assert cliente.get_cookie("recon_session", path="/api/v1") is None


def test_flask_no_admite_sesion_firmada_del_lado_del_cliente(entorno) -> None:
    aplicacion, _, _, _, _ = entorno
    with aplicacion.test_request_context("/"):
        with pytest.raises(RuntimeError):
            session["usuario"] = "valor-ficticio"


def test_fallo_al_confirmar_sesion_revierte_sin_persistir(entorno, monkeypatch) -> None:
    aplicacion, cliente, _, _, _ = entorno

    def fallar(_unidad) -> None:
        raise RuntimeError("fallo ficticio")

    monkeypatch.setattr(UnidadTrabajoIAMSQLAlchemy, "confirmar", fallar)
    assert cliente.get("/api/v1/auth/csrf").status_code == 503
    with aplicacion.app_context():
        assert db.session.scalar(select(SesionUsuarioModelo.digest)) is None
    monkeypatch.setenv("RECON_LOCAL_HTTP", "1")
    monkeypatch.setenv("DB_HOST", "otro-servidor")
    with pytest.raises(ValueError, match="desarrollo local"):
        create_app()


def test_admin_consulta_roles_y_cuentas_sin_campos_sensibles(entorno) -> None:
    _, cliente, _, admin_id, operador_id = entorno
    assert _login(cliente, "admin.ficticio")[0] == 200
    roles = cliente.get("/api/v1/iam/roles")
    assert roles.status_code == 200
    assert {rol["nombre"] for rol in roles.json["roles"]} == {
        "SUPERADMIN", "ADMINISTRADOR", "OPERADOR"
    }
    assert next(rol for rol in roles.json["roles"] if rol["nombre"] == "SUPERADMIN")["asignable"] is False
    listado = cliente.get("/api/v1/iam/usuarios?limite=1&desplazamiento=1")
    assert listado.status_code == 200
    assert listado.json == {
        "usuarios": [{
            "id_usuario": operador_id, "login": "operador.ficticio",
            "rol": "OPERADOR", "estado": "ACTIVO",
        }], "limite": 1, "desplazamiento": 1,
    }
    detalle = cliente.get(f"/api/v1/iam/usuarios/{admin_id}")
    assert detalle.status_code == 200
    assert detalle.json == {
        "id_usuario": admin_id, "login": "admin.ficticio",
        "rol": "SUPERADMIN", "estado": "ACTIVO",
    }
    assert all(respuesta.headers["Cache-Control"] == "no-store" for respuesta in (roles, listado, detalle))


def test_casos_de_consulta_tambien_exigen_superadmin(entorno) -> None:
    aplicacion, _, _, admin_id, operador_id = entorno
    with aplicacion.app_context():
        repo = RepositorioIAMSQLAlchemy(db.session)
        unidad = UnidadTrabajoIAMSQLAlchemy(db.session)
        with pytest.raises(PermisoDenegado):
            ListarRoles(repo, unidad).ejecutar(actor_id=operador_id)
        with pytest.raises(PermisoDenegado):
            ListarUsuariosPlataforma(repo, unidad).ejecutar(actor_id=operador_id)
        with pytest.raises(PermisoDenegado):
            ConsultarUsuarioPlataforma(repo, unidad).ejecutar(
                actor_id=operador_id, usuario_id=admin_id
            )
        assert len(ListarRoles(repo, unidad).ejecutar(actor_id=admin_id)) == 3
        assert ConsultarUsuarioPlataforma(repo, unidad).ejecutar(
            actor_id=admin_id, usuario_id=operador_id
        ).login == "operador.ficticio"


def test_admin_crea_cambia_rol_y_estado_con_auditoria_y_revocacion(entorno) -> None:
    aplicacion, cliente, _, admin_id, _ = entorno
    estado, csrf = _login(cliente, "admin.ficticio")
    assert estado == 200 and csrf is not None
    cabeceras = {"X-CSRF-Token": csrf}
    creada = cliente.post(
        "/api/v1/iam/usuarios",
        json={"login": " Nueva.Cuenta ", "contrasena": CLAVE, "rol": "OPERADOR"},
        headers=cabeceras,
    )
    assert creada.status_code == 201
    id_cuenta = creada.json["id_usuario"]
    assert creada.json == {
        "id_usuario": id_cuenta, "login": "nueva.cuenta",
        "rol": "OPERADOR", "estado": "ACTIVO",
    }
    assert creada.headers["Location"] == f"/api/v1/iam/usuarios/{id_cuenta}"
    assert CLAVE not in creada.get_data(as_text=True)
    cliente_cuenta = aplicacion.test_client()
    assert _login(cliente_cuenta, "nueva.cuenta")[0] == 200
    cambio = cliente.patch(
        f"/api/v1/iam/usuarios/{id_cuenta}/rol",
        json={"rol": "ADMINISTRADOR"}, headers=cabeceras,
    )
    assert cambio.status_code == 200
    assert cambio.json["id_usuario"] == id_cuenta
    assert cambio.json["rol"] == "ADMINISTRADOR"
    desactivada = cliente.patch(
        f"/api/v1/iam/usuarios/{id_cuenta}/estado",
        json={"estado": "INACTIVO"}, headers=cabeceras,
    )
    assert desactivada.status_code == 200
    assert desactivada.json["estado"] == "INACTIVO"
    assert cliente_cuenta.get("/api/v1/auth/me").status_code == 401
    with aplicacion.app_context():
        eventos = db.session.scalars(
            select(AuditoriaIAMModelo).where(AuditoriaIAMModelo.usuario_id == id_cuenta)
            .order_by(AuditoriaIAMModelo.id_auditoria)
        ).all()
        assert [(e.accion, e.actor_id) for e in eventos] == [
            ("CREAR_CUENTA", admin_id), ("CAMBIAR_ROL", admin_id),
            ("CAMBIAR_ESTADO", admin_id),
        ]
        assert all(e.resultado == "EXITO" and CLAVE not in repr(e.__dict__) for e in eventos)
    reactivada = cliente.patch(
        f"/api/v1/iam/usuarios/{id_cuenta}/estado",
        json={"estado": "ACTIVO"}, headers=cabeceras,
    )
    assert reactivada.status_code == 200
    assert cliente_cuenta.get("/api/v1/auth/me").status_code == 401


def test_admin_rechaza_login_duplicado_y_superadmin_adicional(entorno) -> None:
    aplicacion, cliente, _, admin_id, _ = entorno
    _, csrf = _login(cliente, "admin.ficticio")
    cabeceras = {"X-CSRF-Token": csrf}
    duplicada = cliente.post(
        "/api/v1/iam/usuarios",
        json={"login": " OPERADOR.FICTICIO ", "contrasena": CLAVE, "rol": "OPERADOR"},
        headers=cabeceras,
    )
    assert duplicada.status_code == 409
    adicional = cliente.post(
        "/api/v1/iam/usuarios",
        json={"login": "otro.superadmin", "contrasena": CLAVE, "rol": "SUPERADMIN"},
        headers=cabeceras,
    )
    assert adicional.status_code == 400
    with aplicacion.app_context():
        assert db.session.scalar(select(UsuarioPlataformaModelo.id_usuario).where(
            UsuarioPlataformaModelo.login == "otro.superadmin"
        )) is None
        assert db.session.scalar(select(UsuarioPlataformaModelo.estado).where(
            UsuarioPlataformaModelo.id_usuario == admin_id
        )) == "ACTIVO"


@pytest.mark.parametrize("rol_actor", ["OPERADOR", "ADMINISTRADOR"])
def test_solo_superadmin_accede_a_rutas_administrativas(entorno, rol_actor: str) -> None:
    aplicacion, cliente, _, admin_id, operador_id = entorno
    rutas_get = ["/api/v1/iam/roles", "/api/v1/iam/usuarios", f"/api/v1/iam/usuarios/{admin_id}"]
    assert all(cliente.get(ruta).status_code == 401 for ruta in rutas_get)
    otro = aplicacion.test_client()
    if rol_actor == "ADMINISTRADOR":
        with aplicacion.app_context():
            CambiarRolUsuario(
                RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)
            ).ejecutar(actor_id=admin_id, usuario_id=operador_id, rol_nombre=rol_actor)
    estado, csrf = _login(otro, "operador.ficticio")
    assert estado == 200 and csrf is not None
    assert all(otro.get(ruta).status_code == 403 for ruta in rutas_get)
    assert otro.post(
        "/api/v1/iam/usuarios",
        json={"login": "indebida.cuenta", "contrasena": CLAVE, "rol": "OPERADOR"},
        headers={"X-CSRF-Token": csrf},
    ).status_code == 403
    assert otro.patch(
        f"/api/v1/iam/usuarios/{operador_id}/rol",
        json={"rol": "OPERADOR"}, headers={"X-CSRF-Token": csrf},
    ).status_code == 403
    assert otro.patch(
        f"/api/v1/iam/usuarios/{operador_id}/estado",
        json={"estado": "INACTIVO"}, headers={"X-CSRF-Token": csrf},
    ).status_code == 403


def test_admin_exige_csrf_y_rechaza_cuerpos_incompletos_o_adicionales(entorno) -> None:
    aplicacion, cliente, _, _, operador_id = entorno
    _, csrf = _login(cliente, "admin.ficticio")
    ruta = "/api/v1/iam/usuarios"
    cuerpo = {"login": "cuenta.valida", "contrasena": CLAVE, "rol": "OPERADOR"}
    assert cliente.post(ruta, json=cuerpo).status_code == 403
    assert cliente.post(ruta, json=cuerpo, headers={"X-CSRF-Token": "0" * 64}).status_code == 403
    cabeceras = {"X-CSRF-Token": csrf}
    for invalido in ({"login": "falta.clave", "rol": "OPERADOR"},
                     {**cuerpo, "id_usuario": 999}, {**cuerpo, "rol": ["OPERADOR"]},
                     {**cuerpo, "contrasena": "corta"}):
        assert cliente.post(ruta, json=invalido, headers=cabeceras).status_code == 400
    assert cliente.patch(
        f"{ruta}/{operador_id}/rol", json={"rol": ["ADMINISTRADOR"]},
        headers=cabeceras,
    ).status_code == 400
    assert cliente.patch(
        f"{ruta}/{operador_id}/estado", json={"estado": ["INACTIVO"]},
        headers=cabeceras,
    ).status_code == 400
    with aplicacion.app_context():
        assert db.session.scalar(select(UsuarioPlataformaModelo.id_usuario).where(
            UsuarioPlataformaModelo.login == "cuenta.valida"
        )) is None


def test_admin_paginacion_detalle_y_cuenta_inicial_protegida(entorno) -> None:
    _, cliente, _, admin_id, operador_id = entorno
    _, csrf = _login(cliente, "admin.ficticio")
    for consulta in ("limite=0", "limite=101", "desplazamiento=-1", "limite=1&limite=2", "otro=1"):
        assert cliente.get(f"/api/v1/iam/usuarios?{consulta}").status_code == 400
    assert cliente.get("/api/v1/iam/usuarios/99999").status_code == 404
    cabeceras = {"X-CSRF-Token": csrf}
    for sufijo, cuerpo in (("rol", {"rol": "OPERADOR"}),
                           ("estado", {"estado": "INACTIVO"})):
        assert cliente.patch(
            f"/api/v1/iam/usuarios/{admin_id}/{sufijo}", json=cuerpo,
            headers=cabeceras,
        ).status_code == 403
        assert cliente.patch(
            f"/api/v1/iam/usuarios/99999/{sufijo}", json=cuerpo,
            headers=cabeceras,
        ).status_code == 404
    assert cliente.get(f"/api/v1/iam/usuarios/{operador_id}").status_code == 200
    assert cliente.get("/api/v1/auth/me").status_code == 200


def test_admin_falla_cerrado_ante_error_de_persistencia(entorno, monkeypatch) -> None:
    _, cliente, _, _, _ = entorno
    _, csrf = _login(cliente, "admin.ficticio")

    def fallar(*_args, **_kwargs):
        raise RuntimeError("detalle-privado-de-persistencia")

    monkeypatch.setattr(RepositorioIAMSQLAlchemy, "listar_usuarios", fallar)
    respuesta = cliente.get("/api/v1/iam/usuarios")
    assert respuesta.status_code == 503
    assert "detalle-privado-de-persistencia" not in respuesta.get_data(as_text=True)
    def fallar_valor(*_args, **_kwargs):
        raise ValueError("detalle-privado-de-ORM")

    monkeypatch.setattr(RepositorioIAMSQLAlchemy, "listar_usuarios", fallar_valor)
    assert cliente.get("/api/v1/iam/usuarios").status_code == 503
    monkeypatch.setattr(RepositorioIAMSQLAlchemy, "agregar", fallar)
    respuesta = cliente.post(
        "/api/v1/iam/usuarios",
        json={"login": "cuenta.error", "contrasena": CLAVE, "rol": "OPERADOR"},
        headers={"X-CSRF-Token": csrf},
    )
    assert respuesta.status_code == 503
    assert "detalle-privado-de-persistencia" not in respuesta.get_data(as_text=True)
    assert CLAVE not in respuesta.get_data(as_text=True)


def test_admin_fallo_de_auditoria_revierte_creacion_http(entorno, monkeypatch) -> None:
    aplicacion, cliente, _, _, _ = entorno
    _, csrf = _login(cliente, "admin.ficticio")

    def fallar(*_args, **_kwargs):
        raise RuntimeError("detalle-privado-de-auditoria")

    monkeypatch.setattr(RepositorioIAMSQLAlchemy, "auditar", fallar)
    respuesta = cliente.post(
        "/api/v1/iam/usuarios",
        json={"login": "cuenta.sin.auditoria", "contrasena": CLAVE, "rol": "OPERADOR"},
        headers={"X-CSRF-Token": csrf},
    )
    assert respuesta.status_code == 503
    assert "detalle-privado-de-auditoria" not in respuesta.get_data(as_text=True)
    with aplicacion.app_context():
        assert db.session.scalar(select(UsuarioPlataformaModelo.id_usuario).where(
            UsuarioPlataformaModelo.login == "cuenta.sin.auditoria"
        )) is None


def test_admin_respeta_configuracion_https_y_host_local(entorno) -> None:
    aplicacion, cliente, _, _, _ = entorno
    assert cliente.get(
        "/api/v1/iam/roles", environ_overrides={"REMOTE_ADDR": "192.0.2.9"}
    ).status_code == 403
    aplicacion.config["RECON_COOKIE_SECURE"] = True
    assert cliente.get("/api/v1/iam/roles").status_code == 403
