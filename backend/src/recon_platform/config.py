"""Configuración inicial del backend del Proyecto Recon Facial."""

import os


class Configuracion:
    """Contiene los valores básicos de configuración de Flask."""

    TESTING = False

    # La clave debe provenir del entorno, nunca estar escrita en el código.
    # Será necesaria cuando implementemos las sesiones de autenticación.
    SECRET_KEY: str | None = os.getenv("SECRET_KEY") or None
