"""Hash y verificación de contraseñas humanas sin persistir texto claro."""

from werkzeug.security import check_password_hash, generate_password_hash


def generar_hash_contrasena(contrasena: str) -> str:
    # Límite técnico inicial; la política funcional definitiva sigue pendiente.
    if (
        not isinstance(contrasena, str)
        or not 12 <= len(contrasena) <= 1024
        or "\x00" in contrasena
    ):
        raise ValueError("La contraseña no cumple los límites técnicos.")
    return generate_password_hash(contrasena, method="scrypt:32768:8:1")


def verificar_contrasena(hash_almacenado: str, contrasena: str) -> bool:
    if not isinstance(contrasena, str) or not isinstance(hash_almacenado, str):
        return False
    try:
        return check_password_hash(hash_almacenado, contrasena)
    except (ValueError, TypeError):
        return False
