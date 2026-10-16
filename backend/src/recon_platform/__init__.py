"""Aplicación principal del backend del Proyecto Recon Facial."""

from flask import Flask

from recon_platform.config import Configuracion, obtener_uri_mysql
from recon_platform.extensions import db, migrate


def create_app(*, pruebas: bool = False) -> Flask:
    """Construye y configura una instancia de la aplicación Flask."""

    app = Flask(__name__)
    app.config.from_object(Configuracion)
    app.config["TESTING"] = pruebas

    uri = obtener_uri_mysql(pruebas=pruebas)
    if uri is not None:
        app.config["SQLALCHEMY_DATABASE_URI"] = uri
        db.init_app(app)
        # Registrar metadatos antes de asociar Flask-Migrate.
        from recon_platform.identidad.infraestructura import modelos as modelos_iam  # noqa: F401
        from recon_platform.personas.infraestructura import modelos  # noqa: F401

        migrate.init_app(app, db)

    from recon_platform.identidad.infraestructura.cli import registrar_comandos

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
