"""Extensiones compartidas de la aplicación Flask."""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


# Se crean sin vincularlas todavía a una aplicación concreta.
# La conexión a MySQL se configurará en una etapa posterior.
db = SQLAlchemy()
migrate = Migrate()
