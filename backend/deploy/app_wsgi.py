"""Adaptador contenedor: secretos montados y proxy HTTPS acotado; sin SQL al importar."""

import os
from pathlib import Path
import socket

from werkzeug.middleware.proxy_fix import ProxyFix


def read_secret(path: str, *, root: Path = Path("/run/secrets")) -> str:
    """Leer solo un secreto montado, sin imprimir o escribir su contenido."""
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_relative_to(root.resolve(strict=True)) or not resolved.is_file():
        raise ValueError("Se requiere un archivo de secreto montado.")
    if resolved.stat().st_size > 4096:
        raise ValueError("Secreto fuera del tamaño admitido.")
    value = resolved.read_text(encoding="utf-8").rstrip("\r\n")
    if not value or "\n" in value or "\r" in value:
        raise ValueError("Formato de secreto no admitido.")
    return value


def validate_public_settings(settings) -> None:
    """Este stack nuevo no puede apuntar a MySQL Windows ni usar HTTP inseguro."""
    if (settings.get("DB_HOST"), settings.get("DB_PORT"), settings.get("DB_NAME"),
            settings.get("DB_USER")) != ("db", "3306", "recon_container_0010", "recon_container_app"):
        raise ValueError("Destino de contenedor fuera del contrato aislado.")
    if settings.get("RECON_SESSION_COOKIE_SECURE", "1") != "1" or settings.get("RECON_LOCAL_HTTP") == "1":
        raise ValueError("El contenedor exige HTTPS y cookie Secure.")


class TrustedFrontendProxy:
    """Solo Nginx del servicio frontend puede declarar el esquema HTTPS."""

    def __init__(self, app, *, resolver=socket.gethostbyname):
        self.app = app
        self.proxied = ProxyFix(app, x_for=0, x_proto=1, x_host=0, x_port=0, x_prefix=0)
        self.resolver = resolver

    def __call__(self, environ, start_response):
        proto = environ.get("HTTP_X_FORWARDED_PROTO")
        for key in list(environ):
            if key == "HTTP_FORWARDED" or key.startswith("HTTP_X_FORWARDED_") and key != "HTTP_X_FORWARDED_PROTO":
                environ.pop(key, None)
        if proto:
            try:
                trusted = environ.get("REMOTE_ADDR") == self.resolver("frontend")
            except OSError:
                trusted = False
            if not trusted or proto != "https":
                start_response("403 Forbidden", [("Content-Type", "application/json"), ("Cache-Control", "no-store")])
                return [b'{"error":"Proxy o transporte no autorizado."}']
            return self.proxied(environ, start_response)
        return self.app(environ, start_response)


def create_cli_app():
    """Factory Flask explícita para CLI del contenedor; carga *_FILE y nunca migra."""
    validate_public_settings(os.environ)
    password = read_secret(os.environ["DB_PASSWORD_FILE"])
    key = read_secret(os.environ["SECRET_KEY_FILE"])
    if len(key.encode("utf-8")) < 32:
        raise ValueError("La clave de sesión requiere al menos 32 bytes.")
    os.environ["DB_PASSWORD"] = password
    os.environ["SECRET_KEY"] = key
    from recon_platform import create_app

    app = create_app(pruebas=False)
    app.config["DEBUG"] = False
    password = key = None
    return app


def create_wsgi_app():
    """Factory invocada por Gunicorn con el mismo destino y secretos acotados."""
    return TrustedFrontendProxy(create_cli_app())
