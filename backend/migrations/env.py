"""Entorno Alembic usado por Flask-Migrate; no ejecuta cambios al importarse."""

from alembic import context
from flask import current_app

from recon_platform.identidad.infraestructura import modelos as modelos_iam  # noqa: F401
from recon_platform.personas.infraestructura import modelos  # noqa: F401
from recon_platform.accesos.infraestructura import modelos_puntos  # noqa: F401
from recon_platform.accesos.infraestructura import modelos_eventos  # noqa: F401
from recon_platform.integracion_edge.infraestructura import modelos as modelos_dispositivos  # noqa: F401
from recon_platform.auditoria.infraestructura import modelos as modelos_auditoria  # noqa: F401

config = context.config
db = current_app.extensions["migrate"].db
target_metadata = db.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=db.engine.url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with db.engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
