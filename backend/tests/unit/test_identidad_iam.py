"""Reglas IAM con dobles en memoria; no accede a MySQL."""

from copy import deepcopy

import pytest

from recon_platform.identidad.aplicacion.casos_de_uso import (
    AutenticarUsuarioPlataforma,
    BootstrapSuperadmin,
    CambiarEstadoUsuario,
    CambiarLoginUsuario,
    CambiarRolUsuario,
    CrearUsuarioPlataforma,
    ConflictoIntegridadIAM,
    PermisoDenegado,
    RestablecerContrasenaUsuario,
    RolNoExiste,
    UsuarioDuplicado,
)
from recon_platform.identidad.dominio.credenciales import (
    generar_hash_contrasena,
    verificar_contrasena,
)
from recon_platform.identidad.dominio.rol import Rol
from recon_platform.identidad.dominio.usuario_plataforma import (
    UsuarioPlataforma,
    normalizar_login,
)
from recon_platform.identidad.infraestructura.modelos import (
    AuditoriaIAMModelo,
    RolModelo,
    UsuarioPlataformaModelo,
)
from recon_platform import create_app

CLAVE_FICTICIA = "Solo-Prueba-Ficticia-2026!"
OTRA_CLAVE_FICTICIA = "Otra-Prueba-Ficticia-2026!"


class RepositorioMemoria:
    def __init__(self) -> None:
        self.roles = {
            nombre: Rol(nombre=nombre, id_rol=indice)
            for indice, nombre in enumerate(
                ("SUPERADMIN", "ADMINISTRADOR", "OPERADOR"), start=1
            )
        }
        self.usuarios: dict[int, UsuarioPlataforma] = {}
        self.eventos: list[dict[str, object]] = []
        self.siguiente_id = 1
        self.bloqueos = 0
        self.fallar_auditoria = False

    def obtener_rol(self, nombre: str, *, bloquear: bool = False) -> Rol | None:
        if bloquear:
            self.bloqueos += 1
        return self.roles.get(nombre)

    def obtener_superadmin(self) -> UsuarioPlataforma | None:
        cuentas = [
            u for u in self.usuarios.values() if u.rol.nombre == "SUPERADMIN"
        ]
        if len(cuentas) > 1:
            raise ConflictoIntegridadIAM("Existe más de una cuenta SUPERADMIN.")
        return cuentas[0] if cuentas else None

    def hay_usuarios(self) -> bool:
        return bool(self.usuarios)

    def obtener_por_id(self, id_usuario: int) -> UsuarioPlataforma | None:
        return self.usuarios.get(id_usuario)

    def obtener_por_login(self, login: str) -> UsuarioPlataforma | None:
        return next((u for u in self.usuarios.values() if u.login == login), None)

    def agregar(self, usuario: UsuarioPlataforma) -> UsuarioPlataforma:
        usuario.id_usuario = self.siguiente_id
        self.usuarios[self.siguiente_id] = usuario
        self.siguiente_id += 1
        return usuario

    def actualizar(self, usuario: UsuarioPlataforma) -> UsuarioPlataforma:
        self.usuarios[usuario.id_usuario] = usuario
        return usuario

    def auditar(
        self, *, accion: str, actor_id: int | None, usuario_id: int,
        anterior: str | None = None, nuevo: str | None = None,
    ) -> None:
        if self.fallar_auditoria:
            raise RuntimeError("Fallo ficticio de auditoría")
        self.eventos.append({
            "accion": accion, "actor_id": actor_id, "usuario_id": usuario_id,
            "anterior": anterior, "nuevo": nuevo,
        })


class UnidadMemoria:
    def __init__(self, repositorio: RepositorioMemoria) -> None:
        self.repositorio = repositorio
        self.confirmaciones = 0
        self.reversiones = 0
        self._guardar_estado()

    def _guardar_estado(self) -> None:
        self.estado = deepcopy((
            self.repositorio.usuarios, self.repositorio.eventos,
            self.repositorio.siguiente_id,
        ))

    def confirmar(self) -> None:
        self.confirmaciones += 1
        self._guardar_estado()

    def revertir(self) -> None:
        self.reversiones += 1
        usuarios, eventos, siguiente_id = deepcopy(self.estado)
        self.repositorio.usuarios = usuarios
        self.repositorio.eventos = eventos
        self.repositorio.siguiente_id = siguiente_id


@pytest.fixture
def iam() -> tuple[RepositorioMemoria, UnidadMemoria, UsuarioPlataforma]:
    repositorio = RepositorioMemoria()
    unidad = UnidadMemoria(repositorio)
    creado = BootstrapSuperadmin(repositorio, unidad).ejecutar(
        login="admin.inicial", contrasena=CLAVE_FICTICIA
    )
    assert creado.creado
    return repositorio, unidad, creado.usuario


def test_hash_protege_credencial_y_verifica_sin_biometria() -> None:
    hash_guardado = generar_hash_contrasena(CLAVE_FICTICIA)
    assert hash_guardado.startswith("scrypt:")
    assert CLAVE_FICTICIA not in hash_guardado
    assert verificar_contrasena(hash_guardado, CLAVE_FICTICIA)
    assert not verificar_contrasena(hash_guardado, OTRA_CLAVE_FICTICIA)
    assert not verificar_contrasena("hash-invalido", CLAVE_FICTICIA)


@pytest.mark.parametrize("clave", ["", "corta", "x" * 1025, "abc\x00def123456"])
def test_contrasena_invalida_se_rechaza(clave: str) -> None:
    with pytest.raises(ValueError, match="límites técnicos"):
        generar_hash_contrasena(clave)


def test_login_normalizado_y_roles_controlados() -> None:
    assert normalizar_login("  Admin.Inicial  ") == "admin.inicial"
    with pytest.raises(ValueError, match="login"):
        normalizar_login("inválido@correo")
    with pytest.raises(ValueError, match="rol"):
        Rol(nombre="INVITADO")
    with pytest.raises(ValueError, match="Rol válido"):
        UsuarioPlataforma(
            login="sin.rol", hash_contrasena=generar_hash_contrasena(CLAVE_FICTICIA),
            rol=None,
        )
    with pytest.raises(ValueError, match="hash"):
        UsuarioPlataforma(
            login="sin.hash", hash_contrasena="texto-plano", rol=Rol(nombre="OPERADOR")
        )


def test_modelo_iam_tiene_fk_solo_a_rol_y_login_unico() -> None:
    columnas = UsuarioPlataformaModelo.__table__.columns
    assert "id_persona" not in columnas
    assert "id_rol" in columnas
    assert {fk.target_fullname for fk in UsuarioPlataformaModelo.__table__.foreign_keys} == {
        "rol.id_rol"
    }
    assert any(
        c.name == "uq_usuario_plataforma_login"
        for c in UsuarioPlataformaModelo.__table__.constraints
    )
    assert RolModelo.__tablename__ == "rol"
    assert AuditoriaIAMModelo.__table__.columns["actor_id"].nullable
    assert not UsuarioPlataformaModelo.__table__.columns["id_rol"].nullable
    assert "contrasena" not in AuditoriaIAMModelo.__table__.columns


def test_comando_bootstrap_no_abre_mysql_sin_configuracion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for nombre in ("DB_NAME", "DB_USER", "DB_PASSWORD"):
        monkeypatch.delenv(nombre, raising=False)
    aplicacion = create_app()
    resultado = aplicacion.test_cli_runner().invoke(args=["bootstrap-superadmin"])
    assert resultado.exit_code != 0
    assert "Falta configuración de persistencia" in resultado.output


def test_bootstrap_explicito_es_idempotente_y_auditado(
    iam: tuple[RepositorioMemoria, UnidadMemoria, UsuarioPlataforma],
) -> None:
    repositorio, unidad, inicial = iam
    segundo = BootstrapSuperadmin(repositorio, unidad).ejecutar(
        login="otro.superadmin", contrasena=""
    )
    assert not segundo.creado
    assert segundo.usuario.id_usuario == inicial.id_usuario
    assert len(repositorio.usuarios) == 1
    assert repositorio.bloqueos == 2
    assert repositorio.eventos == [{
        "accion": "BOOTSTRAP_SUPERADMIN", "actor_id": None,
        "usuario_id": inicial.id_usuario, "anterior": None, "nuevo": None,
    }]
    assert CLAVE_FICTICIA not in repr(repositorio.eventos)


def test_bootstrap_sin_rol_migrado_revierte() -> None:
    repositorio = RepositorioMemoria()
    repositorio.roles.pop("SUPERADMIN")
    unidad = UnidadMemoria(repositorio)
    with pytest.raises(RolNoExiste):
        BootstrapSuperadmin(repositorio, unidad).ejecutar(
            login="admin.inicial", contrasena=CLAVE_FICTICIA
        )
    assert repositorio.usuarios == {}
    assert unidad.reversiones == 1


def test_bootstrap_rechaza_cuentas_previas_sin_superadmin() -> None:
    repositorio = RepositorioMemoria()
    repositorio.agregar(UsuarioPlataforma(
        login="operador.previo",
        hash_contrasena=generar_hash_contrasena(CLAVE_FICTICIA),
        rol=repositorio.roles["OPERADOR"],
    ))
    unidad = UnidadMemoria(repositorio)
    with pytest.raises(ConflictoIntegridadIAM, match="cuentas existentes"):
        BootstrapSuperadmin(repositorio, unidad).ejecutar(
            login="admin.inicial", contrasena=CLAVE_FICTICIA
        )
    assert len(repositorio.usuarios) == 1
    assert repositorio.eventos == []
    assert unidad.reversiones == 1


def test_bootstrap_rechaza_superadmin_inactivo() -> None:
    repositorio = RepositorioMemoria()
    repositorio.agregar(UsuarioPlataforma(
        login="admin.inactivo",
        hash_contrasena=generar_hash_contrasena(CLAVE_FICTICIA),
        rol=repositorio.roles["SUPERADMIN"],
        estado="INACTIVO",
    ))
    unidad = UnidadMemoria(repositorio)
    with pytest.raises(ConflictoIntegridadIAM, match="no está activa"):
        BootstrapSuperadmin(repositorio, unidad).ejecutar(
            login="admin.nuevo", contrasena=CLAVE_FICTICIA
        )
    assert len(repositorio.usuarios) == 1
    assert repositorio.eventos == []
    assert unidad.reversiones == 1


def test_bootstrap_rechaza_multiples_superadmin() -> None:
    repositorio = RepositorioMemoria()
    for login in ("admin.uno", "admin.dos"):
        repositorio.agregar(UsuarioPlataforma(
            login=login,
            hash_contrasena=generar_hash_contrasena(CLAVE_FICTICIA),
            rol=repositorio.roles["SUPERADMIN"],
        ))
    unidad = UnidadMemoria(repositorio)
    with pytest.raises(ConflictoIntegridadIAM, match="más de una"):
        BootstrapSuperadmin(repositorio, unidad).ejecutar(
            login="admin.tres", contrasena=CLAVE_FICTICIA
        )
    assert len(repositorio.usuarios) == 2
    assert repositorio.eventos == []
    assert unidad.reversiones == 1


def test_superadmin_crea_cuenta_sin_persona_y_autentica(
    iam: tuple[RepositorioMemoria, UnidadMemoria, UsuarioPlataforma],
) -> None:
    repositorio, unidad, inicial = iam
    cuenta = CrearUsuarioPlataforma(repositorio, unidad).ejecutar(
        actor_id=inicial.id_usuario, login=" Operador.Prueba ",
        contrasena=CLAVE_FICTICIA, rol_nombre="OPERADOR",
    )
    assert cuenta.login == "operador.prueba"
    assert not hasattr(cuenta, "id_persona")
    assert cuenta.rol.nombre == "OPERADOR"
    assert cuenta.hash_contrasena != CLAVE_FICTICIA
    autenticada = AutenticarUsuarioPlataforma(repositorio, unidad).ejecutar(
        login="OPERADOR.PRUEBA", contrasena=CLAVE_FICTICIA
    )
    assert autenticada.id_usuario == cuenta.id_usuario
    assert autenticada.rol_nombre == "OPERADOR"
    assert not hasattr(autenticada, "hash_contrasena")
    assert AutenticarUsuarioPlataforma(repositorio, unidad).ejecutar(
        login="OPERADOR.PRUEBA", contrasena=OTRA_CLAVE_FICTICIA
    ) is None
    assert repositorio.eventos[-1]["accion"] == "CREAR_CUENTA"


@pytest.mark.parametrize("rol_actor", ["ADMINISTRADOR", "OPERADOR"])
def test_otros_roles_no_administran_cuentas(
    iam: tuple[RepositorioMemoria, UnidadMemoria, UsuarioPlataforma], rol_actor: str
) -> None:
    repositorio, unidad, inicial = iam
    actor = CrearUsuarioPlataforma(repositorio, unidad).ejecutar(
        actor_id=inicial.id_usuario, login=f"actor.{rol_actor.lower()}",
        contrasena=CLAVE_FICTICIA, rol_nombre=rol_actor,
    )
    with pytest.raises(PermisoDenegado):
        CrearUsuarioPlataforma(repositorio, unidad).ejecutar(
            actor_id=actor.id_usuario, login="nuevo.usuario",
            contrasena=CLAVE_FICTICIA, rol_nombre="OPERADOR",
        )
    with pytest.raises(PermisoDenegado):
        CambiarRolUsuario(repositorio, unidad).ejecutar(
            actor_id=actor.id_usuario, usuario_id=actor.id_usuario,
            rol_nombre="ADMINISTRADOR",
        )
    with pytest.raises(PermisoDenegado):
        CambiarEstadoUsuario(repositorio, unidad).ejecutar(
            actor_id=actor.id_usuario, usuario_id=actor.id_usuario,
            estado="INACTIVO",
        )
    with pytest.raises(PermisoDenegado):
        CambiarLoginUsuario(repositorio, unidad).ejecutar(
            actor_id=actor.id_usuario, usuario_id=actor.id_usuario,
            login="login.indebido",
        )
    with pytest.raises(PermisoDenegado):
        RestablecerContrasenaUsuario(repositorio, unidad).ejecutar(
            actor_id=actor.id_usuario, usuario_id=actor.id_usuario,
            nueva_contrasena=OTRA_CLAVE_FICTICIA,
        )
    assert repositorio.obtener_por_login("nuevo.usuario") is None


def test_login_duplicado_y_superadmin_adicional_rechazados(
    iam: tuple[RepositorioMemoria, UnidadMemoria, UsuarioPlataforma],
) -> None:
    repositorio, unidad, inicial = iam
    crear = CrearUsuarioPlataforma(repositorio, unidad)
    crear.ejecutar(
        actor_id=inicial.id_usuario, login="cuenta.unica",
        contrasena=CLAVE_FICTICIA, rol_nombre="OPERADOR",
    )
    with pytest.raises(UsuarioDuplicado):
        crear.ejecutar(
            actor_id=inicial.id_usuario, login=" CUENTA.UNICA ",
            contrasena=CLAVE_FICTICIA, rol_nombre="ADMINISTRADOR",
        )
    with pytest.raises(PermisoDenegado):
        crear.ejecutar(
            actor_id=inicial.id_usuario, login="otro.admin",
            contrasena=CLAVE_FICTICIA, rol_nombre="SUPERADMIN",
        )
    assert len(repositorio.usuarios) == 2


def test_cambio_de_rol_conserva_id_y_audita(
    iam: tuple[RepositorioMemoria, UnidadMemoria, UsuarioPlataforma],
) -> None:
    repositorio, unidad, inicial = iam
    cuenta = CrearUsuarioPlataforma(repositorio, unidad).ejecutar(
        actor_id=inicial.id_usuario, login="cuenta.rol",
        contrasena=CLAVE_FICTICIA, rol_nombre="OPERADOR",
    )
    actualizado = CambiarRolUsuario(repositorio, unidad).ejecutar(
        actor_id=inicial.id_usuario, usuario_id=cuenta.id_usuario,
        rol_nombre="ADMINISTRADOR",
    )
    assert actualizado.id_usuario == cuenta.id_usuario
    assert actualizado.rol.nombre == "ADMINISTRADOR"
    assert repositorio.eventos[-1]["anterior"] == "OPERADOR"
    assert repositorio.eventos[-1]["nuevo"] == "ADMINISTRADOR"
    with pytest.raises(PermisoDenegado):
        CambiarRolUsuario(repositorio, unidad).ejecutar(
            actor_id=inicial.id_usuario, usuario_id=cuenta.id_usuario,
            rol_nombre="SUPERADMIN",
        )


def test_estado_login_y_clave_cambian_solo_por_superadmin(
    iam: tuple[RepositorioMemoria, UnidadMemoria, UsuarioPlataforma],
) -> None:
    repositorio, unidad, inicial = iam
    cuenta = CrearUsuarioPlataforma(repositorio, unidad).ejecutar(
        actor_id=inicial.id_usuario, login="cuenta.cambio",
        contrasena=CLAVE_FICTICIA, rol_nombre="OPERADOR",
    )
    CambiarLoginUsuario(repositorio, unidad).ejecutar(
        actor_id=inicial.id_usuario, usuario_id=cuenta.id_usuario,
        login="cuenta.nueva",
    )
    RestablecerContrasenaUsuario(repositorio, unidad).ejecutar(
        actor_id=inicial.id_usuario, usuario_id=cuenta.id_usuario,
        nueva_contrasena=OTRA_CLAVE_FICTICIA,
    )
    CambiarEstadoUsuario(repositorio, unidad).ejecutar(
        actor_id=inicial.id_usuario, usuario_id=cuenta.id_usuario,
        estado="INACTIVO",
    )
    assert cuenta.id_usuario == repositorio.obtener_por_login("cuenta.nueva").id_usuario
    assert not AutenticarUsuarioPlataforma(repositorio, unidad).ejecutar(
        login="cuenta.nueva", contrasena=OTRA_CLAVE_FICTICIA
    )
    assert OTRA_CLAVE_FICTICIA not in repr(repositorio.eventos)
    assert [e["accion"] for e in repositorio.eventos][-3:] == [
        "CAMBIAR_LOGIN", "RESTABLECER_CONTRASENA", "CAMBIAR_ESTADO"
    ]


def test_superadmin_inicial_no_puede_desactivarse_ni_cambiar_rol(
    iam: tuple[RepositorioMemoria, UnidadMemoria, UsuarioPlataforma],
) -> None:
    repositorio, unidad, inicial = iam
    with pytest.raises(PermisoDenegado):
        CambiarEstadoUsuario(repositorio, unidad).ejecutar(
            actor_id=inicial.id_usuario, usuario_id=inicial.id_usuario,
            estado="INACTIVO",
        )
    with pytest.raises(PermisoDenegado):
        CambiarRolUsuario(repositorio, unidad).ejecutar(
            actor_id=inicial.id_usuario, usuario_id=inicial.id_usuario,
            rol_nombre="OPERADOR",
        )
    assert repositorio.obtener_superadmin().estado == "ACTIVO"


def test_fallo_de_auditoria_revierte_creacion_y_no_deja_cuenta(
    iam: tuple[RepositorioMemoria, UnidadMemoria, UsuarioPlataforma],
) -> None:
    repositorio, unidad, inicial = iam
    repositorio.fallar_auditoria = True
    with pytest.raises(RuntimeError, match="auditoría"):
        CrearUsuarioPlataforma(repositorio, unidad).ejecutar(
            actor_id=inicial.id_usuario, login="cuenta.revertida",
            contrasena=CLAVE_FICTICIA, rol_nombre="OPERADOR",
        )
    assert repositorio.obtener_por_login("cuenta.revertida") is None
    assert len(repositorio.eventos) == 1
    assert unidad.reversiones == 1
