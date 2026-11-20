"""Bootstrap manual; jamás se ejecuta al importar o arrancar Flask."""

import click
from flask import Flask
from flask.cli import with_appcontext

from recon_platform.extensions import db
from recon_platform.identidad.servicio_cuentas import BootstrapSuperadmin
from recon_platform.identidad.repositorio_cuentas import RepositorioIAMSQLAlchemy
from recon_platform.identidad.unidad_trabajo import UnidadTrabajoIAMSQLAlchemy


def registrar_comandos(app: Flask) -> None:
    @app.cli.command("bootstrap-superadmin")
    @with_appcontext
    def bootstrap_superadmin() -> None:
        """Provisiona una sola cuenta inicial mediante prompts protegidos."""
        if "SQLALCHEMY_DATABASE_URI" not in app.config:
            raise click.ClickException("Falta configuración de persistencia.")
        repositorio = RepositorioIAMSQLAlchemy(db.session)
        try:
            existente = repositorio.obtener_superadmin()
            hay_usuarios = repositorio.hay_usuarios() if existente is None else False
            db.session.rollback()
        except Exception:
            db.session.rollback()
            raise click.ClickException(
                "No se pudo comprobar el estado del bootstrap."
            ) from None
        if existente is not None:
            if existente.estado != "ACTIVO":
                raise click.ClickException(
                    "La cuenta SUPERADMIN existente no está activa; requiere revisión."
                )
            click.echo("La cuenta SUPERADMIN inicial ya existe; no se creó otra.")
            return
        if hay_usuarios:
            raise click.ClickException(
                "Hay cuentas existentes sin SUPERADMIN; requiere revisión."
            )

        if not click.confirm(
            "¿Confirmas que la conexión configurada apunta a la base prevista?",
            default=False,
        ):
            click.echo("Bootstrap cancelado.")
            return
        login = click.prompt(
            "Identificador de login", hide_input=True, confirmation_prompt=True
        )
        contrasena = click.prompt(
            "Contraseña inicial", hide_input=True, confirmation_prompt=True
        )
        try:
            resultado = BootstrapSuperadmin(
                repositorio, UnidadTrabajoIAMSQLAlchemy(db.session)
            ).ejecutar(login=login, contrasena=contrasena)
        except ValueError:
            raise click.ClickException("Datos de bootstrap o catálogo IAM inválidos.") from None
        except Exception:
            raise click.ClickException("No se pudo completar el bootstrap.") from None
        if resultado.creado:
            click.echo("Cuenta SUPERADMIN inicial creada.")
        else:
            click.echo("La cuenta SUPERADMIN inicial ya existe; no se creó otra.")
