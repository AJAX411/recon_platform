"""Contratos explícitos de autenticación humana."""

from recon_platform.identidad.servicios.cuentas import IdentidadAutenticada


def representar_identidad(identidad: IdentidadAutenticada) -> dict[str, int | str]:
    return {
        "id_usuario": identidad.id_usuario,
        "login": identidad.login,
        "rol": identidad.rol_nombre,
    }


def validar_login(datos: object) -> tuple[str, str] | None:
    if not isinstance(datos, dict):
        return None
    usuario, contrasena = datos.get("login"), datos.get("contrasena")
    if not isinstance(usuario, str) or not isinstance(contrasena, str):
        return None
    return usuario, contrasena
