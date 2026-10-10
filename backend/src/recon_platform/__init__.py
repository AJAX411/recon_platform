"""Aplicación principal del backend del Proyecto Recon Facial."""

from flask import Flask

from recon_platform.config import Configuracion


def create_app() -> Flask:
    """Construye y configura una instancia de la aplicación Flask."""

    app = Flask(__name__)
    app.config.from_object(Configuracion)

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
