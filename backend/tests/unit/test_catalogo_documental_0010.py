"""Catálogo, legado y contrato con dobles y SQLite en memoria; sin MySQL."""

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import re

import pytest
from sqlalchemy import func, select

from recon_platform.extensions import db
from recon_platform.personas import tipos_documento as catalogo
from recon_platform.personas.modelos import AuditoriaPersonasModelo, PersonaModelo, TipoPersonaModelo
from recon_platform.personas.servicio import ActorPersonas, AdministrarPersonas, DatosInvalidosPersona, PermisoPersonasDenegado, RegistrarPersona
from test_autenticacion_http import _login, entorno  # noqa: F401
from test_casos_personas import (
    RepositorioFalso, TiposFalsos, UnidadTrabajoFalsa, nueva_persona,
)
from test_personas_http import BASE, _crear, _datos, personas_entorno  # noqa: F401


ESPERADOS = [
    ("CC", "Cédula de ciudadanía"), ("TI", "Tarjeta de identidad"),
    ("CE", "Cédula de extranjería"), ("PA", "Pasaporte"),
    ("PPT", "Permiso por Protección Temporal"), ("RC", "Registro civil de nacimiento"),
]
CLAVES_PERSONA = {
    "id_persona", "primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido",
    "tipo_documento", "numero_documento", "identificador_institucional", "tipo_persona",
    "estado", "fecha_creacion", "fecha_actualizacion",
}


def test_catalogo_exacto_inmutable_y_autorizacion_de_aplicacion():
    tipos = catalogo.catalogo_tipos_documento()
    assert isinstance(tipos, tuple)
    assert [(t.codigo, t.nombre) for t in tipos] == ESPERADOS
    assert all(t.habilitado_para_altas is True for t in tipos)
    with pytest.raises(FrozenInstanceError):
        setattr(tipos[0], "nombre", "No debe mutar")
    caso = AdministrarPersonas(RepositorioFalso(), TiposFalsos("ESTUDIANTE"),
                              UnidadTrabajoFalsa(RepositorioFalso()))
    assert caso.listar_tipos_documento(actor=ActorPersonas(1, "ADMINISTRADOR")) == tipos
    with pytest.raises(PermisoPersonasDenegado):
        caso.listar_tipos_documento(actor=ActorPersonas(2, "OPERADOR"))


@pytest.mark.parametrize("codigo", [c for c, _ in ESPERADOS])
@pytest.mark.parametrize("administrativo", [False, True])
def test_ambos_casos_de_alta_aceptan_seis_tipos_sin_correo(codigo, administrativo):
    repo = RepositorioFalso()
    unidad = UnidadTrabajoFalsa(repo)
    persona = nueva_persona()
    persona.tipo_documento = codigo
    if administrativo:
        guardada = AdministrarPersonas(repo, TiposFalsos("ESTUDIANTE"), unidad).registrar(
            actor=ActorPersonas(1, "SUPERADMIN"), persona=persona)
    else:
        guardada = RegistrarPersona(repo, TiposFalsos("ESTUDIANTE"), unidad).ejecutar(persona)
    assert guardada.tipo_documento == codigo
    assert unidad.confirmaciones == 1


@pytest.mark.parametrize("administrativo", [False, True])
@pytest.mark.parametrize("codigo", ["LEGADO-X", "cc", "PAS"])
def test_alta_desconocida_no_confirma_ni_audita(codigo, administrativo):
    repo = RepositorioFalso()
    unidad = UnidadTrabajoFalsa(repo)
    persona = nueva_persona()
    persona.tipo_documento = codigo
    with pytest.raises(DatosInvalidosPersona):
        if administrativo:
            AdministrarPersonas(repo, TiposFalsos("ESTUDIANTE"), unidad).registrar(
                actor=ActorPersonas(1, "SUPERADMIN"), persona=persona)
        else:
            RegistrarPersona(repo, TiposFalsos("ESTUDIANTE"), unidad).ejecutar(persona)
    assert not repo.existentes and not repo.eventos and unidad.confirmaciones == 0
    assert unidad.reversiones == 1


def test_tipo_deshabilitado_no_es_nueva_asignacion_pero_se_conserva(monkeypatch):
    repo = RepositorioFalso()
    unidad = UnidadTrabajoFalsa(repo)
    caso = AdministrarPersonas(repo, TiposFalsos("ESTUDIANTE"), unidad)
    actor = ActorPersonas(1, "SUPERADMIN")
    caso.registrar(actor=actor, persona=nueva_persona())
    monkeypatch.setattr(catalogo, "TIPOS_DOCUMENTO", tuple(
        replace(t, habilitado_para_altas=False) if t.codigo == "CC" else t
        for t in catalogo.TIPOS_DOCUMENTO))
    assert caso.actualizar(actor=actor, id_persona=1, datos={"primer_nombre": "Conservado"}).tipo_documento == "CC"
    with pytest.raises(DatosInvalidosPersona):
        caso.actualizar(actor=actor, id_persona=1, datos={"numero_documento": "NUEVO"})
    with pytest.raises(DatosInvalidosPersona):
        caso.registrar(actor=actor, persona=nueva_persona(documento="OTRO", identificador="F-2"))
    assert len(repo.existentes) == 1


@pytest.mark.parametrize("login", ["admin.ficticio", "admin.personas.ficticio"])
def test_http_catalogo_seis_tipos_roles_y_parametros(personas_entorno, login):  # noqa: F811
    _, cliente, *_ = personas_entorno
    assert _login(cliente, login)[0] == 200
    respuesta = cliente.get(f"{BASE}/tipos-documento")
    assert respuesta.status_code == 200
    assert respuesta.headers["Cache-Control"] == "no-store"
    assert respuesta.json == {"tipos_documento": [
        {"codigo": c, "nombre": n, "habilitado_para_altas": True} for c, n in ESPERADOS]}
    assert cliente.get(f"{BASE}/tipos-documento?limite=1").status_code == 400
    assert len(cliente.get(f"{BASE}/tipos").json["tipos"]) == 6


def test_http_catalogo_anonimo_operador_y_fallo(personas_entorno, monkeypatch):  # noqa: F811
    _, cliente, *_ = personas_entorno
    assert cliente.get(f"{BASE}/tipos-documento").status_code == 401
    assert _login(cliente, "operador.ficticio")[0] == 200
    assert cliente.get(f"{BASE}/tipos-documento").status_code == 403
    assert _login(cliente, "admin.ficticio")[0] == 200

    def fallar(*args, **kwargs):
        raise RuntimeError("Fallo ficticio de consulta")

    monkeypatch.setattr(AdministrarPersonas, "listar_tipos_documento", fallar)
    fallo = cliente.get(f"{BASE}/tipos-documento")
    assert fallo.status_code == 503 and fallo.json == {"error": "La administración de Personas no está disponible."}
    assert fallo.headers["Cache-Control"] == "no-store"


def test_http_altas_legacy_patch_filtro_obs_y_estado(personas_entorno):  # noqa: F811
    app, cliente, *_ = personas_entorno
    _, csrf = _login(cliente, "admin.personas.ficticio")
    headers = {"X-CSRF-Token": csrf}
    persona_id = 0
    for codigo, _ in ESPERADOS:
        creada = _crear(cliente, csrf, tipo_documento=codigo, numero_documento=f"F-{codigo}")
        assert creada.status_code == 201 and set(creada.json) == CLAVES_PERSONA
        persona_id = creada.json["id_persona"]
    assert persona_id > 0
    with app.app_context():
        modelo = db.session.get(PersonaModelo, persona_id)
        assert modelo is not None
        modelo.tipo_documento = "LEGADO-X"  # Solo fixture SQLite, nunca MySQL.
        db.session.commit()
        antes = db.session.scalar(select(func.count()).select_from(AuditoriaPersonasModelo))
        assert isinstance(antes, int)
    assert cliente.get(f"{BASE}/{persona_id}").json["tipo_documento"] == "LEGADO-X"
    assert len(cliente.get(f"{BASE}?tipo_documento=LEGADO-X").json["personas"]) == 1
    for datos in [{"primer_nombre": "Conservado"},
                  {"tipo_documento": " LEGADO-X ", "numero_documento": " F-RC "}]:
        respuesta = cliente.patch(f"{BASE}/{persona_id}", json=datos, headers=headers)
        assert respuesta.status_code == 200 and respuesta.json["tipo_documento"] == "LEGADO-X"
        assert set(respuesta.json) == CLAVES_PERSONA
    for datos in [{"numero_documento": "NUEVO"}, {"tipo_documento": "DESCONOCIDO"}]:
        assert cliente.patch(f"{BASE}/{persona_id}", json=datos, headers=headers).status_code == 400
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(AuditoriaPersonasModelo)) == antes + 2
    assert cliente.patch(f"{BASE}/{persona_id}", json={"tipo_documento": "CC"}, headers=headers).status_code == 200
    assert cliente.patch(f"{BASE}/{persona_id}/estado", json={"estado": "INACTIVO"}, headers=headers).status_code == 200
    with app.app_context():
        tipo = db.session.scalar(select(TipoPersonaModelo).where(TipoPersonaModelo.nombre == "VISITANTE"))
        assert tipo is not None
        tipo.estado = "INACTIVO"
        db.session.commit()
    rechazo = cliente.patch(f"{BASE}/{persona_id}", json={"primer_nombre": "No aplicar"}, headers=headers)
    assert rechazo.status_code == 400 and rechazo.json["error"] == "El TipoPersona no está disponible."
    assert cliente.patch(f"{BASE}/{persona_id}/estado", json={"estado": "ACTIVO"}, headers=headers).status_code == 200


def test_http_allowlist_y_rechazo_documental_sin_filas_parciales(personas_entorno):  # noqa: F811
    app, cliente, *_ = personas_entorno
    _, csrf = _login(cliente, "admin.ficticio")
    for cambios in [{"tipo_documento": "LEGADO-X"}, {"correo_electronico": "ficticio@example.test"}]:
        respuesta = cliente.post(BASE, json=_datos(**cambios), headers={"X-CSRF-Token": csrf})
        assert respuesta.status_code == 400
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(PersonaModelo)) == 0
        assert db.session.scalar(select(func.count()).select_from(AuditoriaPersonasModelo)) == 0


def test_alta_conserva_trim_exterior_del_codigo(personas_entorno):  # noqa: F811
    _, cliente, *_ = personas_entorno
    _, csrf = _login(cliente, "admin.ficticio")
    respuesta = _crear(cliente, csrf, tipo_documento=" RC ")
    assert respuesta.status_code == 201 and respuesta.json["tipo_documento"] == "RC"


def test_openapi_cierra_solo_altas_y_no_respuestas_patch_o_filtros():
    api = json.loads((Path(__file__).resolve().parents[2] / "openapi.json").read_text(encoding="utf-8"))
    schemas = api["components"]["schemas"]
    patron = schemas["PersonaEntrada"]["properties"]["tipo_documento"]["pattern"]
    assert all(re.fullmatch(patron, c) and re.fullmatch(patron, f" {c} ") for c, _ in ESPERADOS)
    assert not re.fullmatch(patron, "LEGADO-X") and not re.fullmatch(patron, "cc")
    assert "enum" not in schemas["PersonaCambio"]["properties"]["tipo_documento"]
    assert "enum" not in schemas["Persona"]["properties"]["tipo_documento"]
    assert set(schemas["Persona"]["properties"]) == CLAVES_PERSONA
    filtro = next(p for p in api["paths"]["/personas"]["get"]["parameters"] if p["name"] == "tipo_documento")
    assert "enum" not in filtro["schema"]
    assert "/personas/tipos-documento" in api["paths"]
    assert sum(m in {"get", "post", "patch", "put", "delete"} for p in api["paths"].values() for m in p) == 36
    login = api["paths"]["/iam/usuarios/{usuario_id}/login"]["patch"]
    cuerpo = login["requestBody"]["content"]["application/json"]["schema"]
    assert cuerpo["required"] == ["login"] and cuerpo["additionalProperties"] is False
    assert set(cuerpo["properties"]) == {"login"}
    assert {"200", "400", "401", "403", "404", "409", "503"} <= set(login["responses"])
