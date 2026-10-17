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
from recon_platform.identidad import api
from recon_platform.identidad.aplicacion.casos_de_uso import (
    BootstrapSuperadmin,
    CambiarEstadoUsuario,
    CambiarRolUsuario,
    CrearUsuarioPlataforma,
    RestablecerContrasenaUsuario,
)
from recon_platform.identidad.infraestructura.modelos import (
    AuditoriaIAMModelo,
    RolModelo,
    SesionUsuarioModelo,
    UsuarioPlataformaModelo,
)
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.sesiones import RepositorioSesionesSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy

CLAVE = "Clave-Ficticia-Prueba-2026!"
INICIO = datetime(2026, 10, 16, 10, 0)


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Flask, FlaskClient, list[datetime], int, int]]:
    monkeypatch.setattr("recon_platform.obtener_uri_mysql", lambda **_: "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "clave-ficticia-unitaria-de-32-caracteres-o-mas")
    monkeypatch.setenv("RECON_LOCAL_HTTP", "1")
    monkeypatch.setenv("RECON_SESSION_COOKIE_SECURE", "0")
    reloj = [INICIO]
    monkeypatch.setattr(api, "_ahora", lambda: reloj[0])
    aplicacion = create_app(pruebas=True)

    @aplicacion.get("/api/v1/prueba-admin")
    @api.requerir_roles("SUPERADMIN")
    def solo_superadmin():
        return jsonify({"estado": "permitido"})

    @aplicacion.post("/api/v1/prueba-admin")
    @api.requerir_roles("SUPERADMIN")
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
    return respuesta.json["csrf_token"]


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
