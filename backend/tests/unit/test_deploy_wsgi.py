"""Adaptador de contenedor: pruebas nuevas sin SQL, secretos reales o sockets."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location(
    "container_wsgi", Path(__file__).resolve().parents[2] / "deploy/app_wsgi.py")
wsgi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wsgi)


def public_settings():
    return {"DB_HOST": "db", "DB_PORT": "3306", "DB_NAME": "recon_container_0010",
            "DB_USER": "recon_container_app", "RECON_SESSION_COOKIE_SECURE": "1"}


def invoke(headers, resolver=lambda _: "172.20.0.3"):
    seen = {}

    def app(env, start):
        seen.update(env)
        start("200 OK", [])
        return [b"fixture"]

    middleware = wsgi.TrustedFrontendProxy(app, resolver=resolver)
    statuses = []
    env = {"wsgi.url_scheme": "http", "REMOTE_ADDR": "172.20.0.3", **headers}
    body = middleware(env, lambda status, _: statuses.append(status))
    return seen, statuses[0], body


def test_proxy_https_verificado_solo_confia_en_esquema():
    seen, status, _ = invoke({"HTTP_X_FORWARDED_PROTO": "https",
                             "HTTP_X_FORWARDED_FOR": "1.2.3.4", "HTTP_X_FORWARDED_HOST": "ajeno",
                             "HTTP_HOST": "localhost", "HTTP_FORWARDED": "host=ajeno"})
    assert status == "200 OK" and seen["wsgi.url_scheme"] == "https"
    assert seen["REMOTE_ADDR"] == "172.20.0.3" and seen["HTTP_HOST"] == "localhost"
    assert "HTTP_X_FORWARDED_FOR" not in seen and "HTTP_FORWARDED" not in seen


@pytest.mark.parametrize("headers", [
    {"HTTP_X_FORWARDED_PROTO": "https", "REMOTE_ADDR": "172.21.0.5"},
    {"HTTP_X_FORWARDED_PROTO": "http"},
    {"HTTP_X_FORWARDED_PROTO": "https,http"},
])
def test_proxy_rechaza_origen_o_proto_no_autorizados(headers):
    seen, status, _ = invoke(headers)
    assert status == "403 Forbidden" and not seen


def test_proxy_dns_no_disponible_falla_cerrado():
    def missing(_):
        raise OSError("fixture")

    assert invoke({"HTTP_X_FORWARDED_PROTO": "https"}, missing)[1] == "403 Forbidden"


def test_liveness_sin_forwarded_no_resuelve_dns():
    def forbidden(_):
        raise AssertionError("DNS no necesario")

    seen, status, _ = invoke({}, forbidden)
    assert status == "200 OK" and seen["wsgi.url_scheme"] == "http"


@pytest.mark.parametrize("key,value", [
    ("DB_HOST", "127.0.0.1"), ("DB_NAME", "recon_dev"), ("DB_NAME", "recon_tests"),
    ("DB_USER", "root"), ("RECON_SESSION_COOKIE_SECURE", "0"), ("RECON_LOCAL_HTTP", "1"),
])
def test_contenedor_rechaza_destinos_locales_e_inseguridad(key, value):
    settings = public_settings()
    settings[key] = value
    with pytest.raises(ValueError):
        wsgi.validate_public_settings(settings)


def test_configuracion_publica_nueva_aceptada():
    wsgi.validate_public_settings(public_settings())


def test_secreto_ficticio_solo_bajo_raiz_montada(tmp_path):
    root = tmp_path / "mount"
    root.mkdir()
    item = root / "fixture"
    item.write_text("DATO-FICTICIO-NO-SECRETO\n", encoding="utf-8")
    assert wsgi.read_secret(str(item), root=root) == "DATO-FICTICIO-NO-SECRETO"
    outside = tmp_path / "outside"
    outside.write_text("fixture", encoding="utf-8")
    with pytest.raises(ValueError):
        wsgi.read_secret(str(outside), root=root)


@pytest.mark.parametrize("text", ["", "dos\nlineas", "x" * 4097])
def test_secreto_formato_invalido_sin_exponer_valor(tmp_path, text):
    item = tmp_path / "fixture"
    item.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        wsgi.read_secret(str(item), root=tmp_path)


def test_factory_cli_carga_file_antes_de_crear_app_sin_migrar(monkeypatch):
    import recon_platform

    for key, value in public_settings().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("DB_PASSWORD_FILE", "/run/secrets/db_app_password")
    monkeypatch.setenv("SECRET_KEY_FILE", "/run/secrets/session_key")
    monkeypatch.delenv("RECON_LOCAL_HTTP", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setattr(wsgi, "read_secret", lambda path: (
        "DATO-FICTICIO-NO-SECRETO" if path.endswith("db_app_password") else "fixture" * 8))
    app = SimpleNamespace(config={})

    def factory(*, pruebas):
        assert pruebas is False
        assert wsgi.os.environ["DB_PASSWORD"] == "DATO-FICTICIO-NO-SECRETO"
        assert wsgi.os.environ["SECRET_KEY"] == "fixture" * 8
        return app

    monkeypatch.setattr(recon_platform, "create_app", factory)
    assert wsgi.create_cli_app() is app
    assert app.config["DEBUG"] is False


def test_factory_cli_rechaza_destino_antes_de_leer_archivos(monkeypatch):
    monkeypatch.setenv("DB_HOST", "127.0.0.1")

    def forbidden(_):
        raise AssertionError("No debe leer secretos para un destino no autorizado.")

    monkeypatch.setattr(wsgi, "read_secret", forbidden)
    with pytest.raises(ValueError, match="Destino"):
        wsgi.create_cli_app()


def test_wsgi_conserva_proxy_sobre_factory_cli(monkeypatch):
    app = SimpleNamespace()
    monkeypatch.setattr(wsgi, "create_cli_app", lambda: app)
    assert wsgi.create_wsgi_app().app is app
