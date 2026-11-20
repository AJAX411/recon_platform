"""Entrada administrativa exacta y salida de cuentas sin credenciales."""

from recon_platform.identidad.usuario_plataforma import UsuarioPlataforma


def representar_usuario(usuario: UsuarioPlataforma) -> dict[str, int | str | None]:
    return {
        "id_usuario": usuario.id_usuario,
        "login": usuario.login,
        "rol": usuario.rol.nombre,
        "estado": usuario.estado,
    }


def validar_cuerpo_exacto(datos: object, *campos: str) -> dict | None:
    if not isinstance(datos, dict) or set(datos) != set(campos):
        return None
    return datos
