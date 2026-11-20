"""Aplicación principal del backend del Proyecto Recon Facial."""

import os

from flask import Flask

from recon_platform.config import Configuracion, obtener_uri_mysql
from recon_platform.extensions import db, migrate


def create_app(*, pruebas: bool = False) -> Flask:
    """Construye y configura una instancia de la aplicación Flask."""

    app = Flask(__name__)
    from recon_platform.identidad.sesion_flask import SinSesionCliente

    app.session_interface = SinSesionCliente()
    app.config.from_object(Configuracion)
    app.config["TESTING"] = pruebas
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or None
    cookie_segura = os.getenv("RECON_SESSION_COOKIE_SECURE", "1")
    if cookie_segura not in {"0", "1"}:
        raise ValueError("RECON_SESSION_COOKIE_SECURE debe ser 0 o 1.")
    if cookie_segura == "0" and (
        os.getenv("RECON_LOCAL_HTTP") != "1"
        or os.getenv("DB_HOST", "127.0.0.1") != "127.0.0.1"
    ):
        raise ValueError("La cookie HTTP sin Secure solo se admite en desarrollo local.")
    app.config["RECON_COOKIE_SECURE"] = cookie_segura == "1"

    uri = obtener_uri_mysql(pruebas=pruebas)
    if uri is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = uri
        db.init_app(app)
        # Registrar metadatos antes de asociar Flask-Migrate.
        from recon_platform.identidad import modelos as modelos_iam  # noqa: F401
        from recon_platform.personas import modelos  # noqa: F401
        from recon_platform.accesos import modelos_puntos  # noqa: F401
        from recon_platform.integracion_edge import modelos as modelos_dispositivos  # noqa: F401
        from recon_platform.auditoria import modelos as modelos_auditoria  # noqa: F401
        from recon_platform.accesos import modelos_eventos  # noqa: F401

        migrate.init_app(app, db)

    from recon_platform.identidad.controlador_auth import bp as bp_autenticacion
    from recon_platform.identidad.limitador import LimitadorIntentos

    app.extensions["recon_limitador_login"] = LimitadorIntentos()
    app.register_blueprint(bp_autenticacion)

    from recon_platform.identidad.controlador_usuarios import bp as bp_administracion_iam

    app.register_blueprint(bp_administracion_iam)

    from recon_platform.personas.controlador import bp as bp_personas

    app.register_blueprint(bp_personas)

    from recon_platform.accesos.controlador_puntos import bp as bp_puntos
    from recon_platform.integracion_edge.controlador import bp as bp_dispositivos
    from recon_platform.auditoria.controlador import bp as bp_auditoria

    app.register_blueprint(bp_puntos)
    app.register_blueprint(bp_dispositivos)
    app.register_blueprint(bp_auditoria)

    from recon_platform.accesos.controlador_eventos import bp as bp_eventos_acceso

    app.register_blueprint(bp_eventos_acceso)

    from recon_platform.consultas.controlador import bp as bp_consultas

    app.register_blueprint(bp_consultas)

    from recon_platform.identidad.cli import registrar_comandos

    registrar_comandos(app)

    # Ruta temporal de diagnóstico para verificar el arranque.
    # No constituye todavía un endpoint definitivo de la API.
    @app.get("/_diagnostico")
    def obtener_diagnostico() -> dict[str, str]:
        """Confirma que la aplicación Flask responde correctamente."""
        return {
            "servicio": "recon_platform",
            "estado": "inicializado",
        }

    return app
