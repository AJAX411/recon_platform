"""Extensiones compartidas de la aplicación Flask."""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


# Se vinculan en la fábrica solo si existe configuración completa.
db = SQLAlchemy()
migrate = Migrate()
