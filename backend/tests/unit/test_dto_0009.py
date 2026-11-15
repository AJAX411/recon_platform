"""Regresiones de las fronteras extraídas: forma, etapa y minimización."""

from datetime import UTC, datetime
from dataclasses import dataclass, replace

import pytest

from recon_platform.accesos.dto.eventos import representar_evento_manual, validar_cuerpo_manual
from recon_platform.accesos.dto.puntos import representar_punto
from recon_platform.accesos.dominio.evento_acceso import EventoAcceso
from recon_platform.accesos.dominio.punto_acceso import PuntoAcceso
from recon_platform.auditoria.dto.eventos import representar_auditoria
from recon_platform.auditoria.dominio.evento_auditoria import EventoAuditoria
from recon_platform.identidad.dto.autenticacion import representar_identidad, validar_login
from recon_platform.identidad.dto.usuarios import representar_usuario, validar_cuerpo_exacto
from recon_platform.identidad.dominio.credenciales import generar_hash_contrasena
from recon_platform.identidad.dominio.rol import Rol
from recon_platform.identidad.dominio.usuario_plataforma import UsuarioPlataforma
from recon_platform.identidad.servicios.cuentas import IdentidadAutenticada
from recon_platform.integracion_edge.dto.dispositivos import representar_dispositivo
from recon_platform.integracion_edge.dominio.dispositivo_edge import DispositivoEdge
from recon_platform.personas.dto.personas import representar_persona, validar_cuerpo_persona
from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TipoPersona


@dataclass(frozen=True, slots=True)
class IdentidadConCamposAdicionales(IdentidadAutenticada):
    hash_contrasena: str = "marcador-ficticio"
    digest: str = "marcador-ficticio"
    campo_privado: str = "marcador-ficticio"


@dataclass(kw_only=True, slots=True)
class CuentaConCamposAdicionales(UsuarioPlataforma):
    digest: str = "marcador-ficticio"
    campo_privado: str = "marcador-ficticio"


@dataclass(kw_only=True, slots=True)
class PersonaConCamposAdicionales(Persona):
    campo_privado: str = "marcador-ficticio"


@dataclass(kw_only=True, slots=True)
class PuntoConCamposAdicionales(PuntoAcceso):
    campo_privado: str = "marcador-ficticio"


@dataclass(kw_only=True, slots=True)
class DispositivoConCamposAdicionales(DispositivoEdge):
    credencial: str = "marcador-ficticio"


@pytest.mark.parametrize("datos", [None, [], "texto", {}, {"login": "ficticio"},
    {"login": 1, "contrasena": "ficticia"}, {"login": "ficticio", "contrasena": None}])
def test_login_rechaza_formas_invalidas(datos):
    assert validar_login(datos) is None


def test_login_conserva_claves_adicionales_espacios_y_vacios_para_el_servicio():
    assert validar_login({"login": " ficticio ", "contrasena": " ficticia ", "extra": 1}) == (
        " ficticio ", " ficticia ")
    assert validar_login({"login": "", "contrasena": ""}) == ("", "")


@pytest.mark.parametrize("datos", [None, [], {}, {"rol": "OPERADOR", "extra": True}])
def test_iam_exige_las_claves_exactas(datos):
    assert validar_cuerpo_exacto(datos, "rol") is None


def test_iam_no_adelanta_la_validacion_del_tipo_del_campo():
    datos = {"rol": None}
    assert validar_cuerpo_exacto(datos, "rol") is datos


@pytest.mark.parametrize("datos,nuevo", [
    (None, True), ([], False), ({}, True), ({}, False),
    ({"primer_nombre": None}, False), ({"tipo_persona": "DESCONOCIDO"}, False),
    ({"campo_desconocido": "ficticio"}, False),
])
def test_persona_conserva_el_rechazo_de_forma_y_catalogo(datos, nuevo):
    assert validar_cuerpo_persona(datos, nuevo=nuevo) is None


def test_persona_no_confunde_forma_http_con_reglas_de_dominio():
    datos = {"primer_nombre": "", "primer_apellido": "Ficticio", "tipo_documento": "CC",
             "numero_documento": "FICTICIO", "tipo_persona": "ESTUDIANTE",
             "segundo_nombre": None, "segundo_apellido": None,
             "identificador_institucional": None}
    # Vacíos y obligatoriedad condicional se siguen resolviendo en dominio/aplicación.
    assert validar_cuerpo_persona(datos, nuevo=True) is datos
    assert validar_cuerpo_persona({"segundo_nombre": None}, nuevo=False) == {"segundo_nombre": None}
    assert validar_cuerpo_persona({"primer_nombre": "Ficticio"}, nuevo=True) is None


@pytest.mark.parametrize("datos", [None, [], {}, {"id_persona": 1},
    {"id_persona": 1, "id_punto_acceso": 1, "tipo_movimiento": "ENTRADA", "actor": 2}])
def test_manual_conserva_value_error_para_formas_invalidas(datos):
    with pytest.raises(ValueError, match=r"^Cuerpo inválido\.$"):
        validar_cuerpo_manual(datos)


def test_manual_conserva_la_validacion_de_ids_y_movimiento_en_aplicacion():
    datos = {"id_persona": True, "id_punto_acceso": None, "tipo_movimiento": "INVALIDO"}
    assert validar_cuerpo_manual(datos) is datos


def test_cuentas_e_identidad_no_serializan_credenciales_ni_campos_agregados():
    identidad = IdentidadConCamposAdicionales(id_usuario=7, login="cuenta.ficticia", rol_nombre="OPERADOR")
    cuenta = CuentaConCamposAdicionales(id_usuario=7, login="cuenta.ficticia", rol=Rol(nombre="OPERADOR"),
        estado="ACTIVO", hash_contrasena=generar_hash_contrasena("Clave-Ficticia-DTO-0009!"))
    assert representar_identidad(identidad) == {"id_usuario": 7, "login": "cuenta.ficticia", "rol": "OPERADOR"}
    assert representar_usuario(cuenta) == {"id_usuario": 7, "login": "cuenta.ficticia",
        "rol": "OPERADOR", "estado": "ACTIVO"}


def test_persona_preserva_null_y_formato_de_fechas_sin_agregar_campos():
    fecha = datetime(2026, 11, 14, 14, 0, tzinfo=UTC)
    persona = PersonaConCamposAdicionales(id_persona=1, primer_nombre="Persona", segundo_nombre=None,
        primer_apellido="Ficticia", segundo_apellido=None, tipo_documento="CC",
        numero_documento="FICTICIO-0009", identificador_institucional=None,
        tipo_persona=TipoPersona(nombre="VISITANTE"), estado="ACTIVO",
        fecha_creacion=fecha, fecha_actualizacion=None, campo_privado="marcador-ficticio")
    assert representar_persona(persona) == {
        "id_persona": 1, "primer_nombre": "Persona", "segundo_nombre": None,
        "primer_apellido": "Ficticia", "segundo_apellido": None, "tipo_documento": "CC",
        "numero_documento": "FICTICIO-0009", "identificador_institucional": None,
        "tipo_persona": "VISITANTE", "estado": "ACTIVO",
        "fecha_creacion": "2026-11-14T14:00:00+00:00", "fecha_actualizacion": None,
    }


def test_punto_y_dispositivo_conservan_null_y_no_inventan_actividad_edge():
    punto = PuntoConCamposAdicionales(id_punto_acceso=1, codigo="P-0009", nombre="Punto ficticio",
        descripcion=None, estado="ACTIVO", fecha_creacion=None, fecha_actualizacion=None,
        campo_privado="marcador-ficticio")
    assert representar_punto(punto) == {"id_punto_acceso": 1, "codigo": "P-0009",
        "nombre": "Punto ficticio", "descripcion": None, "estado": "ACTIVO",
        "fecha_creacion": None, "fecha_actualizacion": None}
    dispositivo = DispositivoConCamposAdicionales(id_dispositivo=2, id_punto_acceso=1, codigo="D-0009",
        nombre="Nodo ficticio", modo_operacion="ENTRADA", estado="INACTIVO",
        ultima_comunicacion=None, fecha_creacion=None, fecha_actualizacion=None,
        credencial="marcador-ficticio")
    assert representar_dispositivo(dispositivo) == {"id_dispositivo": 2, "id_punto_acceso": 1,
        "codigo": "D-0009", "nombre": "Nodo ficticio", "modo_operacion": "ENTRADA",
        "estado": "INACTIVO", "ultima_comunicacion": None,
        "fecha_creacion": None, "fecha_actualizacion": None}


def test_respuesta_manual_no_expone_clave_idempotente_y_conserva_fecha_exacta():
    evento = EventoAcceso(id_evento_acceso=3, id_persona=1, id_punto_acceso=2,
        tipo_movimiento="SALIDA", resultado="AUTORIZADO", metodo_registro="MANUAL",
        id_usuario_registrador=7, fecha_hora_ocurrencia=datetime(2026, 11, 14, 14, 0, tzinfo=UTC),
        tipo_incidencia_secuencia="SALIDA_SIN_ENTRADA_DEL_DIA", id_dispositivo=None,
        clave_idempotencia="11111111-1111-4111-8111-111111111111")
    assert representar_evento_manual(evento) == {"id_evento_acceso": 3, "id_persona": 1,
        "id_punto_acceso": 2, "tipo_movimiento": "SALIDA", "resultado": "AUTORIZADO",
        "metodo_registro": "MANUAL", "id_usuario_registrador": 7,
        "fecha_hora_ocurrencia": "2026-11-14T14:00:00+00:00",
        "tipo_incidencia_secuencia": "SALIDA_SIN_ENTRADA_DEL_DIA", "id_dispositivo": None}


def test_auditoria_no_agrega_tolerancia_a_fecha_ausente():
    evento = EventoAuditoria(id_auditoria=1, id_usuario_actor=None, tipo_actor="SISTEMA",
        accion="ACCION_FICTICIA", recurso_tipo=None, id_recurso_afectado=None,
        resultado="EXITOSO", detalle=None, fecha_hora=None)
    with pytest.raises(AttributeError, match=r"^'NoneType' object has no attribute 'isoformat'$"):
        representar_auditoria(evento)
    evento = replace(evento, fecha_hora=datetime(2026, 11, 14, 14, 0, tzinfo=UTC))
    assert representar_auditoria(evento) == {"id_auditoria": 1, "id_usuario_actor": None,
        "tipo_actor": "SISTEMA", "accion": "ACCION_FICTICIA", "recurso_tipo": None,
        "id_recurso_afectado": None, "resultado": "EXITOSO", "detalle": None,
        "fecha_hora": "2026-11-14T14:00:00+00:00"}
