"""Bootstrap, autenticación y administración exclusiva de SUPERADMIN."""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from recon_platform.identidad.aplicacion.puertos import RepositorioIAM, UnidadTrabajoIAM
from recon_platform.identidad.dominio.credenciales import (
    generar_hash_contrasena,
    verificar_contrasena,
)
from recon_platform.identidad.dominio.usuario_plataforma import (
    UsuarioPlataforma,
    normalizar_login,
)


class PermisoDenegado(ValueError):
    """El actor no puede administrar cuentas de plataforma."""


class UsuarioDuplicado(ValueError):
    """El identificador de login ya está ocupado."""


class UsuarioNoExiste(ValueError):
    """La cuenta solicitada no existe."""


class RolNoExiste(ValueError):
    """El catálogo no contiene el rol solicitado."""


class ConflictoIntegridadIAM(ValueError):
    """La base de datos rechazó la operación IAM."""


@dataclass(frozen=True, slots=True)
class ResultadoBootstrap:
    usuario: UsuarioPlataforma
    creado: bool


@dataclass(frozen=True, slots=True)
class IdentidadAutenticada:
    id_usuario: int
    login: str
    rol_nombre: str


@contextmanager
def _transaccion(unidad: UnidadTrabajoIAM) -> Iterator[None]:
    try:
        yield
        unidad.confirmar()
    except Exception:
        unidad.revertir()
        raise


def _exigir_superadmin(repositorio: RepositorioIAM, actor_id: int) -> UsuarioPlataforma:
    if type(actor_id) is not int or actor_id <= 0:
        raise PermisoDenegado("La operación requiere un SUPERADMIN activo.")
    actor = repositorio.obtener_por_id(actor_id)
    if actor is None or actor.estado != "ACTIVO" or actor.rol.nombre != "SUPERADMIN":
        raise PermisoDenegado("La operación requiere un SUPERADMIN activo.")
    return actor


def _objetivo_administrable(
    repositorio: RepositorioIAM, usuario_id: int
) -> UsuarioPlataforma:
    if type(usuario_id) is not int or usuario_id <= 0:
        raise UsuarioNoExiste("La cuenta no existe.")
    usuario = repositorio.obtener_por_id(usuario_id)
    if usuario is None:
        raise UsuarioNoExiste("La cuenta no existe.")
    if usuario.rol.nombre == "SUPERADMIN":
        raise PermisoDenegado("La cuenta SUPERADMIN inicial está protegida.")
    return usuario


class BootstrapSuperadmin:
    """Crea a lo sumo la cuenta inicial; bloquea el Rol para serializar intentos."""

    def __init__(self, repositorio: RepositorioIAM, unidad: UnidadTrabajoIAM) -> None:
        self.repositorio = repositorio
        self.unidad = unidad

    def ejecutar(self, *, login: str, contrasena: str) -> ResultadoBootstrap:
        with _transaccion(self.unidad):
            rol = self.repositorio.obtener_rol("SUPERADMIN", bloquear=True)
            if rol is None:
                raise RolNoExiste("Primero debe aplicarse la migración del catálogo IAM.")
            existente = self.repositorio.obtener_superadmin()
            if existente is not None:
                if existente.estado != "ACTIVO":
                    raise ConflictoIntegridadIAM(
                        "La cuenta SUPERADMIN existente no está activa."
                    )
                return ResultadoBootstrap(usuario=existente, creado=False)
            if self.repositorio.hay_usuarios():
                raise ConflictoIntegridadIAM(
                    "Hay cuentas existentes sin una cuenta SUPERADMIN."
                )
            usuario = UsuarioPlataforma(
                login=login,
                hash_contrasena=generar_hash_contrasena(contrasena),
                rol=rol,
            )
            usuario = self.repositorio.agregar(usuario)
            self.repositorio.auditar(
                accion="BOOTSTRAP_SUPERADMIN", actor_id=None,
                usuario_id=usuario.id_usuario,
            )
            return ResultadoBootstrap(usuario=usuario, creado=True)


class CrearUsuarioPlataforma:
    """SUPERADMIN crea cuentas ADMINISTRADOR u OPERADOR."""

    def __init__(self, repositorio: RepositorioIAM, unidad: UnidadTrabajoIAM) -> None:
        self.repositorio = repositorio
        self.unidad = unidad

    def ejecutar(
        self, *, actor_id: int, login: str, contrasena: str, rol_nombre: str
    ) -> UsuarioPlataforma:
        with _transaccion(self.unidad):
            actor = _exigir_superadmin(self.repositorio, actor_id)
            if rol_nombre not in {"ADMINISTRADOR", "OPERADOR"}:
                raise PermisoDenegado("No se permite asignar ese rol.")
            rol = self.repositorio.obtener_rol(rol_nombre)
            if rol is None:
                raise RolNoExiste("El rol no existe en el catálogo.")
            login_normalizado = normalizar_login(login)
            if self.repositorio.obtener_por_login(login_normalizado) is not None:
                raise UsuarioDuplicado("El identificador de login ya existe.")
            usuario = self.repositorio.agregar(UsuarioPlataforma(
                login=login_normalizado,
                hash_contrasena=generar_hash_contrasena(contrasena),
                rol=rol,
            ))
            self.repositorio.auditar(
                accion="CREAR_CUENTA", actor_id=actor.id_usuario,
                usuario_id=usuario.id_usuario, nuevo=rol.nombre,
            )
            return usuario


class CambiarRolUsuario:
    def __init__(self, repositorio: RepositorioIAM, unidad: UnidadTrabajoIAM) -> None:
        self.repositorio = repositorio
        self.unidad = unidad

    def ejecutar(
        self, *, actor_id: int, usuario_id: int, rol_nombre: str
    ) -> UsuarioPlataforma:
        with _transaccion(self.unidad):
            actor = _exigir_superadmin(self.repositorio, actor_id)
            objetivo = _objetivo_administrable(self.repositorio, usuario_id)
            if rol_nombre not in {"ADMINISTRADOR", "OPERADOR"}:
                raise PermisoDenegado("No se permite asignar ese rol.")
            rol = self.repositorio.obtener_rol(rol_nombre)
            if rol is None:
                raise RolNoExiste("El rol no existe en el catálogo.")
            if objetivo.rol.nombre == rol.nombre:
                return objetivo
            anterior = objetivo.rol.nombre
            objetivo.rol = rol
            actualizado = self.repositorio.actualizar(objetivo)
            self.repositorio.auditar(
                accion="CAMBIAR_ROL", actor_id=actor.id_usuario,
                usuario_id=objetivo.id_usuario, anterior=anterior, nuevo=rol.nombre,
            )
            return actualizado


class CambiarEstadoUsuario:
    def __init__(self, repositorio: RepositorioIAM, unidad: UnidadTrabajoIAM) -> None:
        self.repositorio = repositorio
        self.unidad = unidad

    def ejecutar(
        self, *, actor_id: int, usuario_id: int, estado: str
    ) -> UsuarioPlataforma:
        with _transaccion(self.unidad):
            actor = _exigir_superadmin(self.repositorio, actor_id)
            objetivo = _objetivo_administrable(self.repositorio, usuario_id)
            if estado not in {"ACTIVO", "INACTIVO"}:
                raise ValueError("El estado de cuenta no es válido.")
            if objetivo.estado == estado:
                return objetivo
            anterior = objetivo.estado
            objetivo.estado = estado
            actualizado = self.repositorio.actualizar(objetivo)
            self.repositorio.auditar(
                accion="CAMBIAR_ESTADO", actor_id=actor.id_usuario,
                usuario_id=objetivo.id_usuario, anterior=anterior, nuevo=estado,
            )
            return actualizado


class CambiarLoginUsuario:
    def __init__(self, repositorio: RepositorioIAM, unidad: UnidadTrabajoIAM) -> None:
        self.repositorio = repositorio
        self.unidad = unidad

    def ejecutar(
        self, *, actor_id: int, usuario_id: int, login: str
    ) -> UsuarioPlataforma:
        with _transaccion(self.unidad):
            actor = _exigir_superadmin(self.repositorio, actor_id)
            objetivo = _objetivo_administrable(self.repositorio, usuario_id)
            nuevo = normalizar_login(login)
            if objetivo.login == nuevo:
                return objetivo
            if self.repositorio.obtener_por_login(nuevo) is not None:
                raise UsuarioDuplicado("El identificador de login ya existe.")
            anterior = objetivo.login
            objetivo.login = nuevo
            actualizado = self.repositorio.actualizar(objetivo)
            self.repositorio.auditar(
                accion="CAMBIAR_LOGIN", actor_id=actor.id_usuario,
                usuario_id=objetivo.id_usuario, anterior=anterior, nuevo=nuevo,
            )
            return actualizado


class RestablecerContrasenaUsuario:
    def __init__(self, repositorio: RepositorioIAM, unidad: UnidadTrabajoIAM) -> None:
        self.repositorio = repositorio
        self.unidad = unidad

    def ejecutar(
        self, *, actor_id: int, usuario_id: int, nueva_contrasena: str
    ) -> UsuarioPlataforma:
        with _transaccion(self.unidad):
            actor = _exigir_superadmin(self.repositorio, actor_id)
            objetivo = _objetivo_administrable(self.repositorio, usuario_id)
            objetivo.hash_contrasena = generar_hash_contrasena(nueva_contrasena)
            actualizado = self.repositorio.actualizar(objetivo)
            self.repositorio.auditar(
                accion="RESTABLECER_CONTRASENA", actor_id=actor.id_usuario,
                usuario_id=objetivo.id_usuario,
            )
            return actualizado


class AutenticarUsuarioPlataforma:
    """Verifica credenciales sin sesión HTTP ni dependencia biométrica."""

    def __init__(self, repositorio: RepositorioIAM, unidad: UnidadTrabajoIAM) -> None:
        self.repositorio = repositorio
        self.unidad = unidad

    def ejecutar(self, *, login: str, contrasena: str) -> IdentidadAutenticada | None:
        with _transaccion(self.unidad):
            try:
                normalizado = normalizar_login(login)
            except ValueError:
                return None
            usuario = self.repositorio.obtener_por_login(normalizado)
            if (
                usuario is None or usuario.estado != "ACTIVO"
                or not verificar_contrasena(usuario.hash_contrasena, contrasena)
            ):
                return None
            return IdentidadAutenticada(
                id_usuario=usuario.id_usuario,
                login=usuario.login,
                rol_nombre=usuario.rol.nombre,
            )
