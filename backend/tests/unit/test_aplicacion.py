"""Pruebas iniciales de la aplicación Flask."""

from flask import Flask

from recon_platform import create_app


def test_crear_aplicacion() -> None:
    """Comprueba que la fábrica construye una aplicación Flask."""
    aplicacion = create_app()

    assert isinstance(aplicacion, Flask)


def test_ruta_diagnostico() -> None:
    """Comprueba la respuesta de la ruta temporal de diagnóstico."""
    aplicacion = create_app()
    cliente = aplicacion.test_client()

    respuesta = cliente.get("/_diagnostico")

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "servicio": "recon_platform",
        "estado": "inicializado",
    }
