"""Riesgos del traslado: primer registro, contratos, composición y relojes."""

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from datetime import timedelta

from recon_platform import composicion
from recon_platform.accesos.controladores import eventos
from recon_platform.extensions import db
from recon_platform.identidad.controladores import seguridad

# Fixture HTTP existente: datos ficticios y SQLite exclusivamente en memoria.
from test_autenticacion_http import _login, entorno  # noqa: F401


def test_primer_registro_aislado_conserva_modelos_metadata_y_mapa_http():
    codigo = textwrap.dedent('''
        import hashlib, importlib, json
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        from sqlalchemy.dialects import mysql
        from sqlalchemy.schema import CreateTable, CreateIndex

        @event.listens_for(Engine, "do_connect")
        def prohibir_conexion(*args, **kwargs):
            raise AssertionError("El primer registro no debe abrir conexiones.")

        import recon_platform
        from recon_platform.extensions import db
        assert not db.metadata.tables
        recon_platform.obtener_uri_mysql = lambda **_: "sqlite+pysqlite:///:memory:"
        app = recon_platform.create_app(pruebas=True)
        dialect = mysql.dialect()
        esquema = {n: {"ddl": str(CreateTable(t).compile(dialect=dialect)),
            "indexes": sorted(str(CreateIndex(i).compile(dialect=dialect)) for i in t.indexes)}
            for n,t in db.metadata.tables.items()}
        def firma(value):
            return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        reglas = {"rules": sorted([{"rule": str(r), "endpoint": r.endpoint,
            "view": app.view_functions[r.endpoint].__name__, "methods": sorted(r.methods),
            "arguments": sorted(r.arguments),
            "converters": {k: type(v).__name__ for k,v in r._converters.items()},
            "defaults": r.defaults, "strict_slashes": r.strict_slashes,
            "subdomain": r.subdomain, "redirect_to": r.redirect_to,
            "automatic_options": r.provide_automatic_options,
        } for r in app.url_map.iter_rules()], key=lambda r: (r["rule"], r["endpoint"])),
            "blueprints": list(app.blueprints),
            "before": {str(k): [f.__name__ for f in fs] for k,fs in app.before_request_funcs.items()},
            "after": {str(k): [f.__name__ for f in fs] for k,fs in app.after_request_funcs.items()},
            "resources": {k: {"static_folder": b.static_folder, "template_folder": b.template_folder}
                for k,b in app.blueprints.items()},
        }
        mappers = list(db.Model.registry.mappers)
        assert len(mappers) == 11 and len(db.metadata.tables) == 11
        assert "alembic_version" not in db.metadata.tables
        for mapper in mappers:
            clase = mapper.class_
            canonica = getattr(importlib.import_module(clase.__module__), clase.__name__)
            assert canonica is clase
            assert clase.metadata is db.metadata
            assert mapper.local_table is db.metadata.tables[mapper.local_table.name]
        # Otra app importa las mismas clases; no registra un segundo conjunto.
        recon_platform.create_app(pruebas=True)
        assert set(db.Model.registry.mappers) == set(mappers)
        assert not any(n.startswith("alembic.") and n.endswith(".env") for n in __import__("sys").modules)
        print(json.dumps({"schema": firma(esquema), "routes": firma(reglas)}))
    ''')
    entorno_proceso = {k: v for k, v in os.environ.items()
                       if not k.startswith(("DB_", "RECON_")) and k != "SECRET_KEY"}
    resultado = subprocess.run([sys.executable, "-B", "-c", codigo],
        cwd=Path(__file__).resolve().parents[2], env=entorno_proceso,
        capture_output=True, text=True, timeout=30, check=True)
    # Firmas de U0, obtenidas antes del refactor; no describen una base MySQL viva.
    assert json.loads(resultado.stdout) == {
        "schema": "c429d9b17d888f46f8c6ad03ed72b346b83a61402ea9f0dbd42cf7b5b5e9d934",
        "routes": "3cd6637c064f3e1c0d92dfb67e9aa39e4c9b2e1d64ab616ec468199653d5d409",
    }


def test_composicion_construye_por_peticion_y_comparte_la_sesion(entorno):  # noqa: F811
    app, _, _, _, _ = entorno
    with app.app_context():
        auditoria = composicion.auditoria()
        puntos = composicion.puntos()
        dispositivos = composicion.dispositivos()
        gestor = composicion.crear_gestor_sesiones("clave-ficticia-de-composicion-0009")
        cuenta, unidad_iam = composicion.crear_dependencias_iam()
        personas = composicion.crear_administracion_personas()
        consulta = composicion.crear_consulta_eventos(eventos._reloj)
        registro = composicion.crear_registro_manual(eventos._reloj)
        adaptadores = [auditoria.repositorio, auditoria.unidad,
            puntos.puntos, puntos.auditoria, puntos.unidad,
            dispositivos.dispositivos, dispositivos.puntos, dispositivos.auditoria, dispositivos.unidad,
            gestor.sesiones, gestor.cuentas, gestor.unidad, cuenta, unidad_iam,
            personas.personas, personas.tipos, personas.unidad_trabajo,
            consulta.eventos, registro.eventos, registro.auditoria, registro.unidad]
        assert all(adaptador.sesion is db.session for adaptador in adaptadores)
        assert composicion.puntos() is not puntos
        assert composicion.crear_registro_manual(eventos._reloj) is not registro
        assert consulta.reloj is eventos._reloj and registro.reloj is eventos._reloj


def test_reloj_canonico_expira_endpoint_y_guard_con_un_solo_parche(entorno):  # noqa: F811
    _, cliente, reloj, _, _ = entorno
    assert _login(cliente, "admin.ficticio")[0] == 200
    assert seguridad.ahora_utc() == reloj[0]
    assert cliente.get("/api/v1/auth/me").status_code == 200
    assert cliente.get("/api/v1/iam/roles").status_code == 200
    reloj[0] += timedelta(minutes=30)
    assert cliente.get("/api/v1/auth/me").status_code == 401
    assert cliente.get("/api/v1/iam/roles").status_code == 401


def test_composicion_y_nucleo_no_dependen_de_controladores_o_frameworks():
    raiz = Path(__file__).resolve().parents[2] / "src/recon_platform"
    for archivo in raiz.rglob("*.py"):
        es_nucleo = bool({"servicios", "puertos", "dominio"} & set(archivo.relative_to(raiz).parts))
        if archivo.name != "composicion.py" and not es_nucleo:
            continue
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom):
                modulos = [nodo.module or ""]
            elif isinstance(nodo, ast.Import):
                modulos = [nombre.name for nombre in nodo.names]
            else:
                continue
            assert all(".controladores" not in nombre for nombre in modulos), archivo
            if es_nucleo:
                assert all(nombre.split(".")[0] not in {"flask", "sqlalchemy", "flask_sqlalchemy"}
                           for nombre in modulos), archivo


def test_repositorios_y_composicion_no_confirman_transacciones():
    raiz = Path(__file__).resolve().parents[2] / "src/recon_platform"
    archivos = [raiz / "composicion.py", *raiz.rglob("repositorios*.py")]
    for archivo in archivos:
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute):
                assert nodo.func.attr != "commit", archivo


def test_imports_de_consumidores_resuelven_rutas_canonicas_sin_ejecutar_alembic():
    backend = Path(__file__).resolve().parents[2]
    fuente = backend / "src"
    archivos = [*fuente.rglob("*.py"), *(backend / "tests").rglob("*.py"),
                *(backend / "scripts").glob("*.py"), backend / "migrations/env.py"]
    for archivo in archivos:
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            nombres = ([nodo.module] if isinstance(nodo, ast.ImportFrom) and not nodo.level
                       else [a.name for a in nodo.names] if isinstance(nodo, ast.Import) else [])
            for nombre in nombres:
                if nombre and nombre.startswith("recon_platform"):
                    ruta = fuente / nombre.replace(".", "/")
                    assert ruta.with_suffix(".py").is_file() or (ruta / "__init__.py").is_file(), (
                        archivo, nombre)
