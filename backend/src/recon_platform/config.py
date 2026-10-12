"""Configuración de la plataforma sin conexiones implícitas a MySQL."""

import os

from sqlalchemy.engine import URL


class Configuracion:
    """Contiene valores básicos de Flask; los secretos provienen del entorno."""

    TESTING = False

    # La clave debe provenir del entorno, nunca estar escrita en el código.
    # Será necesaria cuando implementemos las sesiones de autenticación.
    SECRET_KEY: str | None = os.getenv("SECRET_KEY") or None
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def obtener_uri_mysql(*, pruebas: bool = False) -> str | None:
    """Prepara la URL sin abrir conexión; exige una base distinta en pruebas."""
    base_desarrollo = os.getenv("DB_NAME", "").strip()
    base_pruebas = os.getenv("DB_TEST_NAME", "").strip()
    nombre = base_pruebas if pruebas else base_desarrollo
    usuario = os.getenv("DB_USER", "").strip()
    clave = os.getenv("DB_PASSWORD", "")

    if not pruebas and not any((base_desarrollo, usuario, clave)):
        return None
    if pruebas and not any((base_desarrollo, base_pruebas, usuario, clave)):
        return None
    if not nombre or not usuario or not clave:
        raise ValueError("La configuración MySQL está incompleta.")
    if pruebas and (
        not base_desarrollo or base_pruebas.casefold() == base_desarrollo.casefold()
    ):
        raise ValueError("DB_TEST_NAME debe ser diferente de DB_NAME.")

    puerto_texto = os.getenv("DB_PORT", "3306")
    try:
        puerto = int(puerto_texto)
    except ValueError as error:
        raise ValueError("DB_PORT debe ser un entero válido.") from error
    if not 1 <= puerto <= 65535:
        raise ValueError("DB_PORT debe estar entre 1 y 65535.")

    url = URL.create(
        "mysql+pymysql",
        username=usuario,
        password=clave,
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=puerto,
        database=nombre,
        query={"charset": "utf8mb4"},
    )
    return url.render_as_string(hide_password=False)
