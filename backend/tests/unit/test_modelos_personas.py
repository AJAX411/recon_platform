"""Comprueba el esquema declarado sin crear ni conectar bases de datos."""

from sqlalchemy import UniqueConstraint

from recon_platform.personas.modelos import PersonaModelo, TipoPersonaModelo


def test_persona_declara_fk_y_unicidades_independientes() -> None:
    tabla = PersonaModelo.__table__
    assert tabla.c.id_tipo_persona.nullable is False
    assert tabla.c.tipo_documento.nullable is False
    assert tabla.c.numero_documento.nullable is False
    assert tabla.c.identificador_institucional.nullable is True
    assert {
        (fk.parent.name, fk.column.table.name, fk.column.name, fk.ondelete)
        for fk in tabla.foreign_keys
    } == {("id_tipo_persona", "tipo_persona", "id_tipo_persona", "RESTRICT")}
    unicidades = {
        frozenset(columna.name for columna in restriccion.columns)
        for restriccion in tabla.constraints
        if isinstance(restriccion, UniqueConstraint)
    }
    assert unicidades == {
        frozenset({"identificador_institucional"}),
        frozenset({"tipo_documento", "numero_documento"}),
    }
    assert TipoPersonaModelo.__table__.c.nombre.nullable is False
