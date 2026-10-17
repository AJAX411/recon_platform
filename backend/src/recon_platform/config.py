"""Configuración de la plataforma sin conexiones implícitas a MySQL."""

import os

from sqlalchemy.engine import URL


class Configuracion:
    """Contiene valores básicos de Flask; los secretos provienen del entorno."""

    TESTING = False

    # La clave debe provenir del entorno, nunca estar escrita en el código.
    # El HTTP IAM exige un valor del entorno de al menos 32 bytes UTF-8.
    SECRET_KEY: str | None = os.getenv("SECRET_KEY") or None
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def obtener_uri_mysql(*, pruebas: bool = False) -> str | None:
    """Prepara la URL sin abrir conexión; aísla base y credenciales de pruebas."""
    base_desarrollo = os.getenv("DB_NAME", "").strip()
    if pruebas:
        nombre = os.getenv("DB_TEST_NAME", "").strip()
        usuario = os.getenv("DB_TEST_USER", "").strip()
        clave = os.getenv("DB_TEST_PASSWORD", "")
        if not all((base_desarrollo, nombre, usuario, clave)):
            raise ValueError("La configuración MySQL de pruebas está incompleta.")
        if nombre.casefold() == base_desarrollo.casefold():
            raise ValueError("DB_TEST_NAME debe ser diferente de DB_NAME.")
    else:
        nombre = base_desarrollo
        usuario = os.getenv("DB_USER", "").strip()
        clave = os.getenv("DB_PASSWORD", "")
        if not any((nombre, usuario, clave)):
            return None
        if not all((nombre, usuario, clave)):
            raise ValueError("La configuración MySQL está incompleta.")

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
