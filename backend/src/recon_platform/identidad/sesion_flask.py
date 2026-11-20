"""Impide crear por accidente la sesión firmada del lado del cliente de Flask."""

from flask import Flask, Request, Response
from flask.sessions import SessionInterface, SessionMixin


class SinSesionCliente(SessionInterface):
    def open_session(self, app: Flask, request: Request) -> None:
        return None  # Flask entrega NullSession; escribir en ella falla cerrado.

    def save_session(self, app: Flask, session: SessionMixin, response: Response) -> None:
        return None
