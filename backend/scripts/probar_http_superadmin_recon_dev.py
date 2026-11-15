"""Prueba HTTP local y controlada del SUPERADMIN con Flask test_client()."""

import getpass
import hashlib
import os
import secrets
import sys
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime

from flask.testing import FlaskClient
from sqlalchemy import text

from recon_platform import create_app
from recon_platform.extensions import db
from recon_platform.identidad.infraestructura.modelos import SesionUsuarioModelo
from recon_platform.identidad.infraestructura.repositorios_sesiones import RepositorioSesionesSQLAlchemy
from verificar_recon_dev_0002 import DESTINO, TABLAS, VARIABLES, VerificacionFallida
from verificar_recon_dev_0003 import (
    verificar_datos_previos, verificar_esquema, verificar_sesion_nueva,
)

RUTA = "/api/v1/auth"
BASE_LOCAL = "http://localhost"
ORIGEN_LOCAL = {"REMOTE_ADDR": "127.0.0.1"}


@dataclass(frozen=True, repr=False)
class EstadoInicial:
    id_usuario: int
    login: str
    id_auditoria: int
    total_personas: int
    digests: frozenset[str]
    activos: frozenset[str]


def exigir(condicion: bool, mensaje: str) -> None:
    if not condicion:
        raise VerificacionFallida(mensaje)


def verificar_estado() -> EstadoInicial:
    """Consulta la misma conexión configurada en la app, sin escribir."""
    ausentes = [nombre for nombre in VARIABLES if not os.getenv(nombre)]
    exigir(not ausentes, "Faltan variables de conexión: " + ", ".join(ausentes) + ".")
    url = db.engine.url
    exigir(url.drivername == "mysql+pymysql"
           and (url.host, url.port, url.database, url.username) == DESTINO,
           "La aplicación no apunta a recon_dev con recon_dev_app.")
    with db.engine.connect() as conexion:
        base, cuenta, usuario, puerto = conexion.execute(text(
            "SELECT DATABASE(), CURRENT_USER(), USER(), @@port"
        )).one()
        exigir(base == "recon_dev" and isinstance(cuenta, str)
               and cuenta.partition("@")[0] == "recon_dev_app"
               and isinstance(usuario, str)
               and usuario.partition("@")[0] == "recon_dev_app"
               and puerto == 3306,
               "La identidad real de la conexión MySQL no corresponde a recon_dev.")
        revision = conexion.execute(text(
            "SELECT version_num FROM alembic_version"
        )).scalars().all()
        exigir(revision == ["0003_sesiones_iam"], "Se requiere exactamente 0003_sesiones_iam.")
        tablas: dict[str, str] = {}
        for fila in conexion.execute(text(
            "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE()"
        )).mappings():
            nombre, motor = fila["TABLE_NAME"], fila["ENGINE"]
            if isinstance(nombre, str) and isinstance(motor, str):
                tablas[nombre] = motor
        esperadas = TABLAS | {"sesion_usuario"}
        exigir(esperadas <= tablas.keys()
               and all(tablas[tabla] == "InnoDB" for tabla in esperadas),
               "Faltan tablas InnoDB requeridas para la prueba HTTP.")
        verificar_esquema(conexion)
        verificar_datos_previos(conexion)
        verificar_sesion_nueva(conexion, exigir_vacia=False)
        id_usuario, login = conexion.execute(text(
            "SELECT id_usuario, login FROM usuario_plataforma"
        )).one()
        id_auditoria = conexion.scalar(text("SELECT id_auditoria FROM auditoria_iam"))
        total_personas = conexion.scalar(text("SELECT COUNT(*) FROM persona"))
        digests = frozenset(conexion.execute(text(
            "SELECT digest FROM sesion_usuario"
        )).scalars())
        activos = frozenset(conexion.execute(text(
            "SELECT digest FROM sesion_usuario WHERE fecha_revocacion IS NULL "
            "AND fecha_expiracion > UTC_TIMESTAMP() "
            "AND fecha_actividad > UTC_TIMESTAMP() - INTERVAL 30 MINUTE"
        )).scalars())
        if not (isinstance(id_usuario, int) and isinstance(login, str)
                and isinstance(id_auditoria, int) and isinstance(total_personas, int)):
            raise VerificacionFallida(
                "No se pudo validar la identidad histórica de desarrollo."
            )
        return EstadoInicial(
            id_usuario, login, id_auditoria, total_personas, digests, activos
        )


def capturar_cookie(
    cliente: FlaskClient, creadas: dict[str, int | None],
    anteriores: frozenset[str], id_usuario: int | None,
) -> str | None:
    cookie = cliente.get_cookie("recon_session", path="/api/v1")
    if cookie is None:
        return None
    token = cookie.value
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    exigir(digest not in anteriores, "La prueba reutilizaría una sesión preexistente.")
    creadas.setdefault(digest, id_usuario)
    return token


def flujo_http(cliente: FlaskClient, estado: EstadoInicial, login: str,
               contrasena: str, creadas: dict[str, int | None]) -> None:
    def get(ruta: str):
        return cliente.get(ruta, base_url=BASE_LOCAL, environ_overrides=ORIGEN_LOCAL)

    def post(ruta: str, **opciones):
        return cliente.post(ruta, base_url=BASE_LOCAL,
                            environ_overrides=ORIGEN_LOCAL, **opciones)

    exigir(get(f"{RUTA}/me").status_code == 401,
           "La consulta sin autenticación no devolvió 401.")

    respuesta_csrf = get(f"{RUTA}/csrf")
    token_anonimo = capturar_cookie(cliente, creadas, estado.digests, None)
    if respuesta_csrf.status_code != 200 or token_anonimo is None:
        raise VerificacionFallida("No se pudo obtener una sesión anónima y CSRF.")
    cookie_anonima = cliente.get_cookie("recon_session", path="/api/v1")
    exigir(cookie_anonima is not None and bool(cookie_anonima.http_only)
           and cookie_anonima.same_site == "Lax" and not cookie_anonima.secure,
           "Los atributos de la cookie local no coinciden con la configuración aprobada.")
    datos_csrf = respuesta_csrf.get_json(silent=True)
    csrf = datos_csrf.get("csrf_token") if isinstance(datos_csrf, dict) else None
    if not isinstance(csrf, str) or len(csrf) != 64:
        raise VerificacionFallida("La respuesta CSRF es inesperada.")

    respuesta_login = post(
        f"{RUTA}/login", json={"login": login, "contrasena": contrasena},
        headers={"X-CSRF-Token": csrf},
    )
    token_autenticado = capturar_cookie(
        cliente, creadas, estado.digests, estado.id_usuario
    )
    if (respuesta_login.status_code != 200 or token_autenticado is None
            or token_autenticado == token_anonimo):
        raise VerificacionFallida(
            "El inicio de sesión no devolvió la sesión autenticada esperada."
        )
    identidad = respuesta_login.get_json(silent=True)
    esperada = {"id_usuario": estado.id_usuario, "login": estado.login,
                "rol": "SUPERADMIN"}
    exigir(identidad == esperada, "La identidad devuelta por login es inesperada.")
    csrf_autenticado = respuesta_login.headers.get("X-CSRF-Token")
    if (not isinstance(csrf_autenticado, str) or len(csrf_autenticado) != 64
            or csrf_autenticado == csrf):
        raise VerificacionFallida("No se rotó el CSRF tras el login.")

    respuesta_me = get(f"{RUTA}/me")
    exigir(respuesta_me.status_code == 200
           and respuesta_me.get_json(silent=True) == esperada,
           "La consulta de sesión activa no coincide con el SUPERADMIN.")

    respuesta_logout = post(f"{RUTA}/logout",
                            headers={"X-CSRF-Token": csrf_autenticado})
    capturar_cookie(cliente, creadas, estado.digests, estado.id_usuario)
    exigir(respuesta_logout.status_code == 200
           and respuesta_logout.get_json(silent=True) == {"estado": "cerrada"},
           "El cierre de sesión no devolvió el resultado esperado.")
    exigir(cliente.get_cookie("recon_session", path="/api/v1") is None,
           "El cierre de sesión no retiró la cookie del cliente.")
    exigir(get(f"{RUTA}/me").status_code == 401,
           "La sesión cerrada todavía autoriza el acceso.")
    with db.engine.connect() as conexion:
        for token in (token_anonimo, token_autenticado):
            digest = hashlib.sha256(token.encode("ascii")).hexdigest()
            revocacion = conexion.scalar(text(
                "SELECT fecha_revocacion FROM sesion_usuario WHERE digest = :digest"
            ), {"digest": digest})
            exigir(revocacion is not None,
                   "El flujo HTTP no persistió la revocación de una sesión.")


def revocar_propias(creadas: dict[str, int | None], anteriores: frozenset[str]) -> None:
    """Recuperación acotada para errores intermedios; nunca toca sesiones previas."""
    if not creadas:
        return
    db.session.remove()
    repositorio = RepositorioSesionesSQLAlchemy(db.session)
    cambios = False
    try:
        for digest in creadas:
            exigir(digest not in anteriores, "Una sesión de la prueba coincide con una previa.")
            modelo = db.session.get(SesionUsuarioModelo, digest)
            if modelo is None:
                continue
            if modelo.fecha_revocacion is None:
                repositorio.revocar(digest, datetime.now(UTC).replace(tzinfo=None))
                cambios = True
        if cambios:
            db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    finally:
        db.session.remove()


def verificar_cierre(inicial: EstadoInicial,
                     creadas: dict[str, int | None]) -> None:
    final = verificar_estado()
    exigir((final.id_usuario, final.login, final.id_auditoria, final.total_personas)
           == (inicial.id_usuario, inicial.login, inicial.id_auditoria,
               inicial.total_personas),
           "La cuenta, auditoría o cantidad de Personas cambió durante la prueba.")
    exigir(not (final.activos - inicial.activos),
           "Quedaron sesiones activas nuevas; revisar manualmente antes de continuar.")
    with db.engine.connect() as conexion:
        for digest, cuenta_esperada in creadas.items():
            fila = conexion.execute(text(
                "SELECT id_usuario, fecha_revocacion FROM sesion_usuario "
                "WHERE digest = :digest"
            ), {"digest": digest}).one_or_none()
            exigir(fila is not None and fila[0] == cuenta_esperada
                   and fila[1] is not None,
                   "Una sesión creada no quedó revocada.")


def main() -> int:
    if len(sys.argv) != 1:
        print("NO APTO: este script no acepta argumentos.", file=sys.stderr)
        return 1
    if os.getenv("RECON_LOCAL_HTTP") != "1" \
            or os.getenv("RECON_SESSION_COOKIE_SECURE") != "0":
        print("NO APTO: se requiere la excepción HTTP local explícita.", file=sys.stderr)
        return 1
    os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
    warnings.simplefilter("error", getpass.GetPassWarning)
    try:
        app = create_app(pruebas=False)
        app.logger.disabled = True
        with app.app_context():
            inicial = verificar_estado()
            print("APTO: destino real, revisión 0003 e integridad previa verificados.")
            login = getpass.getpass("Login del SUPERADMIN (oculto): ")
            exigir(login.strip().lower() == inicial.login,
                   "El login introducido no corresponde al SUPERADMIN verificado.")
            contrasena = getpass.getpass("Contraseña del SUPERADMIN (oculta): ")
            exigir(bool(contrasena), "La contraseña no puede estar vacía.")
            creadas: dict[str, int | None] = {}
            fallo: str | None = None
            try:
                flujo_http(app.test_client(), inicial, login, contrasena, creadas)
            except VerificacionFallida as error:
                fallo = str(error)
            except Exception:
                fallo = "El flujo HTTP produjo un resultado inesperado."
            finally:
                contrasena = ""
                try:
                    revocar_propias(creadas, inicial.digests)
                except Exception:
                    fallo = "No se pudo asegurar la revocación de las sesiones de la prueba."
                try:
                    verificar_cierre(inicial, creadas)
                except Exception:
                    fallo = "No se pudo confirmar la preservación de datos y el cierre de sesiones."
            if fallo is not None:
                raise VerificacionFallida(fallo)
    except VerificacionFallida as error:
        print(f"NO APTO: {error}", file=sys.stderr)
        return 1
    except Exception:
        print("NO APTO: no se pudo completar la prueba HTTP de forma segura.",
              file=sys.stderr)
        return 1
    finally:
        os.environ.pop("SECRET_KEY", None)
    print("APTO: login, sesión activa, logout y rechazo posterior comprobados.")
    print("APTO: Persona, SUPERADMIN y auditoría conservados; sin sesiones nuevas activas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
