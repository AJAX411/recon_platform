"""API Personas con SQLite efímero y sesiones IAM reales; no abre MySQL."""

import pytest
from sqlalchemy import select

from recon_platform.extensions import db
from recon_platform.identidad.aplicacion.casos_de_uso import CrearUsuarioPlataforma
from recon_platform.identidad.infraestructura.repositorios import RepositorioIAMSQLAlchemy
from recon_platform.identidad.infraestructura.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy
from recon_platform.personas.aplicacion.casos_de_uso import ActorPersonas, AdministrarPersonas, PermisoPersonasDenegado
from recon_platform.personas.dominio.persona import Persona
from recon_platform.personas.dominio.tipo_persona import TipoPersona
from recon_platform.personas.infraestructura.modelos import AuditoriaPersonasModelo, PersonaModelo, TipoPersonaModelo
from recon_platform.personas.infraestructura.repositorios import RepositorioPersonasSQLAlchemy, RepositorioTiposPersonaSQLAlchemy
from recon_platform.personas.infraestructura.unidad_trabajo import UnidadTrabajoSQLAlchemy

from test_autenticacion_http import CLAVE, _login, entorno  # noqa: F401

BASE = "/api/v1/personas"


@pytest.fixture
def personas_entorno(entorno):
    app, cliente, _, superadmin_id, operador_id = entorno
    with app.app_context():
        TipoPersonaModelo.__table__.create(db.engine)
        PersonaModelo.__table__.create(db.engine)
        AuditoriaPersonasModelo.__table__.create(db.engine)
        db.session.add_all(TipoPersonaModelo(nombre=nombre) for nombre in (
            "ESTUDIANTE", "DOCENTE", "ADMINISTRATIVO", "SERVICIOS_GENERALES",
            "VISITANTE", "PERSONAL_SEGURIDAD"))
        db.session.commit()
        admin = CrearUsuarioPlataforma(
            RepositorioIAMSQLAlchemy(db.session), UnidadTrabajoIAMSQLAlchemy(db.session)
        ).ejecutar(actor_id=superadmin_id, login="admin.personas.ficticio",
                  contrasena=CLAVE, rol_nombre="ADMINISTRADOR")
        admin_id = admin.id_usuario
    return app, cliente, superadmin_id, admin_id, operador_id


def _datos(**cambios):
    return {"primer_nombre": "Persona", "primer_apellido": "Ficticia",
            "tipo_documento": "PRUEBA", "numero_documento": "0001",
            "tipo_persona": "VISITANTE", **cambios}


def _crear(cliente, csrf, **cambios):
    return cliente.post(BASE, json=_datos(**cambios), headers={"X-CSRF-Token": csrf})


def test_registro_consulta_listado_filtros_y_catalogo(personas_entorno):
    app, cliente, actor_id, _, _ = personas_entorno
    assert _login(cliente, "admin.ficticio")[0] == 200
    csrf = cliente.get("/api/v1/auth/csrf").json["csrf_token"]
    creada = _crear(cliente, csrf)
    assert creada.status_code == 201
    persona_id = creada.json["id_persona"]
    assert creada.headers["Location"] == f"{BASE}/{persona_id}"
    assert cliente.get(f"{BASE}/{persona_id}").json == creada.json
    assert cliente.get(f"{BASE}/{persona_id + 99}").status_code == 404
    assert cliente.get(f"{BASE}?limite=1&tipo_persona=VISITANTE&estado=ACTIVO").json["personas"] == [creada.json]
    assert cliente.get(f"{BASE}?numero_documento=desconocido").json["personas"] == []
    assert cliente.get(f"{BASE}?limite=1&desplazamiento=1").json["personas"] == []
    assert len(cliente.get(f"{BASE}/tipos").json["tipos"]) == 6
    with app.app_context():
        eventos = db.session.scalars(select(AuditoriaPersonasModelo)).all()
        assert [(e.actor_id, e.accion, e.id_persona) for e in eventos] == [
            (actor_id, "REGISTRAR_PERSONA", persona_id)]
        assert eventos[0].fecha is not None


def test_actualizacion_estado_y_auditoria(personas_entorno):
    app, cliente, _, _, _ = personas_entorno
    _, csrf = _login(cliente, "admin.ficticio")
    persona_id = _crear(cliente, csrf).json["id_persona"]
    cabeceras = {"X-CSRF-Token": csrf}
    actualizada = cliente.patch(f"{BASE}/{persona_id}", json={
        "tipo_persona": "ESTUDIANTE", "identificador_institucional": "TEST-1",
        "tipo_documento": "OTRO", "numero_documento": "0002"}, headers=cabeceras)
    assert actualizada.status_code == 200
    assert actualizada.json["id_persona"] == persona_id
    assert actualizada.json["tipo_persona"] == "ESTUDIANTE"
    assert cliente.patch(f"{BASE}/{persona_id}", json={"tipo_persona": "VISITANTE",
        "identificador_institucional": None}, headers=cabeceras).status_code == 200
    assert cliente.patch(f"{BASE}/{persona_id}/estado", json={"estado": "INACTIVO"},
                        headers=cabeceras).json["estado"] == "INACTIVO"
    assert cliente.patch(f"{BASE}/{persona_id}/estado", json={"estado": "ACTIVO"},
                        headers=cabeceras).json["estado"] == "ACTIVO"
    with app.app_context():
        assert [e.accion for e in db.session.scalars(select(AuditoriaPersonasModelo).order_by(
            AuditoriaPersonasModelo.id_auditoria)).all()] == [
                "REGISTRAR_PERSONA", "ACTUALIZAR_PERSONA", "ACTUALIZAR_PERSONA",
                "DESACTIVAR_PERSONA", "ACTIVAR_PERSONA"]


def test_validaciones_duplicados_y_rollback(personas_entorno, monkeypatch):
    app, cliente, _, _, _ = personas_entorno
    _, csrf = _login(cliente, "admin.ficticio")
    cabeceras = {"X-CSRF-Token": csrf}
    primera = _crear(cliente, csrf, tipo_persona="ESTUDIANTE", identificador_institucional="TEST-1")
    assert primera.status_code == 201
    segunda = _crear(cliente, csrf, numero_documento="0002", identificador_institucional="TEST-2")
    assert segunda.status_code == 201
    for cambios in ({"numero_documento": "0001"}, {"identificador_institucional": "TEST-1"}):
        assert cliente.patch(f"{BASE}/{segunda.json['id_persona']}", json=cambios,
                            headers=cabeceras).status_code == 409
    assert cliente.patch(f"{BASE}/{segunda.json['id_persona']}",
        json={"tipo_persona": "ESTUDIANTE"}, headers=cabeceras).status_code == 200
    assert cliente.patch(f"{BASE}/{segunda.json['id_persona']}",
        json={"identificador_institucional": None}, headers=cabeceras).status_code == 400
    assert _crear(cliente, csrf, numero_documento="0003", tipo_persona="ESTUDIANTE").status_code == 400
    assert _crear(cliente, csrf, numero_documento="0001", identificador_institucional="TEST-3").status_code == 409
    for cuerpo in ({"primer_nombre": "X"}, {**_datos(numero_documento="0004"), "extra": 1},
                   {**_datos(numero_documento="0004"), "estado": "INACTIVO"}):
        assert cliente.post(BASE, json=cuerpo, headers=cabeceras).status_code == 400
    def fallar(*_args, **_kwargs):
        raise RuntimeError("detalle-personal-secreto")
    monkeypatch.setattr(RepositorioPersonasSQLAlchemy, "auditar", fallar)
    respuesta = _crear(cliente, csrf, numero_documento="fallo")
    assert respuesta.status_code == 503
    assert "detalle-personal-secreto" not in respuesta.get_data(as_text=True)
    with app.app_context():
        assert db.session.scalar(select(PersonaModelo.id_persona).where(
            PersonaModelo.numero_documento == "fallo")) is None


def test_permisos_sesion_csrf_y_filtros_rechazados(personas_entorno):
    app, cliente, superadmin_id, admin_id, _ = personas_entorno
    assert cliente.get(BASE).status_code == 401
    assert cliente.get(f"{BASE}/tipos").status_code == 401
    assert cliente.post(BASE, json=_datos()).status_code == 403
    operador = app.test_client()
    _, csrf_operador = _login(operador, "operador.ficticio")
    for ruta in (BASE, f"{BASE}/tipos", f"{BASE}/1"):
        assert operador.get(ruta).status_code == 403
    assert _crear(operador, csrf_operador).status_code == 403
    assert operador.patch(f"{BASE}/1", json={"primer_nombre": "Sin permiso"},
                          headers={"X-CSRF-Token": csrf_operador}).status_code == 403
    assert _login(cliente, "admin.personas.ficticio")[0] == 200
    csrf = cliente.get("/api/v1/auth/csrf").json["csrf_token"]
    assert _crear(cliente, csrf).status_code == 201
    assert _crear(cliente, "0" * 64, numero_documento="0002").status_code == 403
    assert cliente.patch(f"{BASE}/1", json={"primer_nombre": "Cambio"}).status_code == 403
    for consulta in ("limite=0", "limite=101", "otro=1", "estado=OTRO",
                     "tipo_persona=OTRO", "limite=1&limite=2"):
        assert cliente.get(f"{BASE}?{consulta}").status_code == 400
    assert cliente.get(f"{BASE}/tipos?otro=1").status_code == 400
    assert cliente.get(f"{BASE}/0").status_code == 400
    assert cliente.get(BASE).status_code == 200
    with app.app_context():
        caso = AdministrarPersonas(RepositorioPersonasSQLAlchemy(db.session),
                                  RepositorioTiposPersonaSQLAlchemy(db.session),
                                  UnidadTrabajoSQLAlchemy(db.session))
        with pytest.raises(PermisoPersonasDenegado):
            caso.listar(actor=ActorPersonas(999, "OPERADOR"))


def test_caso_administrativo_rollback_de_actualizacion_y_autorizacion(personas_entorno, monkeypatch):
    app, _, superadmin_id, _, _ = personas_entorno
    with app.app_context():
        repo = RepositorioPersonasSQLAlchemy(db.session)
        caso = AdministrarPersonas(repo, RepositorioTiposPersonaSQLAlchemy(db.session),
                                  UnidadTrabajoSQLAlchemy(db.session))
        actor = ActorPersonas(superadmin_id, "SUPERADMIN")
        registrada = caso.registrar(actor=actor, persona=Persona(
            primer_nombre="Inicial", primer_apellido="Ficticia",
            tipo_documento="PRUEBA", numero_documento="CASO-1",
            tipo_persona=TipoPersona(nombre="VISITANTE")))
        with pytest.raises(PermisoPersonasDenegado):
            caso.actualizar(actor=ActorPersonas(superadmin_id, "OPERADOR"),
                            id_persona=registrada.id_persona,
                            datos={"primer_nombre": "No autorizado"})
        def fallar(*_args, **_kwargs):
            raise RuntimeError("fallo ficticio")
        monkeypatch.setattr(repo, "auditar", fallar)
        with pytest.raises(RuntimeError):
            caso.actualizar(actor=actor, id_persona=registrada.id_persona,
                            datos={"primer_nombre": "No persistir"})
        db.session.expire_all()
        assert caso.consultar(actor=actor, id_persona=registrada.id_persona).primer_nombre == "Inicial"
