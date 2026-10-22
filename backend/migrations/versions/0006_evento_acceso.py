"""EventoAcceso manual, incidencias, idempotencia y origen futuro opcional.

Revision ID: 0006_evento_acceso
Revises: 0005_puntos_edge_auditoria
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0006_evento_acceso"
down_revision = "0005_puntos_edge_auditoria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    identificador = sa.Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
    fecha = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")
    movimiento = sa.String(10).with_variant(mysql.VARCHAR(10, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
    resultado = sa.String(10).with_variant(mysql.VARCHAR(10, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
    metodo = sa.String(10).with_variant(mysql.VARCHAR(10, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
    incidencia = sa.String(40).with_variant(mysql.VARCHAR(40, charset="utf8mb4", collation="utf8mb4_bin"), "mysql")
    clave = sa.CHAR(36).with_variant(mysql.CHAR(36, charset="ascii", collation="ascii_bin"), "mysql")
    op.create_table(
        "evento_acceso",
        sa.Column("id_evento_acceso", identificador, primary_key=True, autoincrement=True),
        sa.Column("id_persona", identificador, nullable=True),
        sa.Column("id_punto_acceso", identificador, nullable=False),
        sa.Column("tipo_movimiento", movimiento, nullable=False),
        sa.Column("resultado", resultado, nullable=False),
        sa.Column("metodo_registro", metodo, nullable=False),
        sa.Column("id_usuario_registrador", identificador, nullable=True),
        sa.Column("fecha_hora_ocurrencia", fecha, nullable=False),
        sa.Column("tipo_incidencia_secuencia", incidencia, nullable=True),
        sa.Column("id_dispositivo", identificador, nullable=True),
        sa.Column("clave_idempotencia", clave, nullable=True),
        sa.ForeignKeyConstraint(["id_persona"], ["persona.id_persona"],
                                name="fk_evento_acceso_persona", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["id_punto_acceso"], ["punto_acceso.id_punto_acceso"],
                                name="fk_evento_acceso_punto", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["id_usuario_registrador"], ["usuario_plataforma.id_usuario"],
                                name="fk_evento_acceso_registrador", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["id_dispositivo"], ["dispositivo_edge.id_dispositivo"],
                                name="fk_evento_acceso_dispositivo", ondelete="RESTRICT"),
        sa.UniqueConstraint("clave_idempotencia", name="uq_evento_acceso_clave_idempotencia"),
        sa.CheckConstraint("tipo_movimiento IN ('ENTRADA', 'SALIDA')",
                           name="ck_evento_acceso_movimiento"),
        sa.CheckConstraint("resultado IN ('AUTORIZADO', 'RECHAZADO')",
                           name="ck_evento_acceso_resultado"),
        sa.CheckConstraint("metodo_registro IN ('MANUAL', 'FACIAL')",
                           name="ck_evento_acceso_metodo"),
        sa.CheckConstraint("tipo_incidencia_secuencia IS NULL OR tipo_incidencia_secuencia IN "
                           "('ENTRADA_REPETIDA', 'SALIDA_REPETIDA', 'SALIDA_SIN_ENTRADA_DEL_DIA')",
                           name="ck_evento_acceso_incidencia"),
        sa.CheckConstraint("tipo_incidencia_secuencia IS NULL OR resultado = 'AUTORIZADO'",
                           name="ck_evento_acceso_incidencia_autorizada"),
        sa.CheckConstraint("metodo_registro <> 'MANUAL' OR (id_persona IS NOT NULL AND "
                           "id_usuario_registrador IS NOT NULL AND id_dispositivo IS NULL AND "
                           "clave_idempotencia IS NOT NULL)", name="ck_evento_acceso_manual"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_evento_acceso_registrador", "evento_acceso", ["id_usuario_registrador"])
    op.create_index("ix_evento_acceso_dispositivo", "evento_acceso", ["id_dispositivo"])
    op.create_index("ix_evento_acceso_secuencia", "evento_acceso",
                    ["id_persona", "resultado", "fecha_hora_ocurrencia", "id_evento_acceso"])
    op.create_index("ix_evento_acceso_fecha", "evento_acceso",
                    ["fecha_hora_ocurrencia", "id_evento_acceso"])
    op.create_index("ix_evento_acceso_alertas", "evento_acceso",
                    ["tipo_incidencia_secuencia", "fecha_hora_ocurrencia", "id_evento_acceso"])
    op.create_index("ix_evento_acceso_punto_fecha", "evento_acceso",
                    ["id_punto_acceso", "fecha_hora_ocurrencia"])


def downgrade() -> None:
    # La eliminación de eventos requiere autorización, preflight y respaldo fuera de Alembic.
    op.drop_index("ix_evento_acceso_punto_fecha", table_name="evento_acceso")
    op.drop_index("ix_evento_acceso_alertas", table_name="evento_acceso")
    op.drop_index("ix_evento_acceso_fecha", table_name="evento_acceso")
    op.drop_index("ix_evento_acceso_secuencia", table_name="evento_acceso")
    op.drop_index("ix_evento_acceso_dispositivo", table_name="evento_acceso")
    op.drop_index("ix_evento_acceso_registrador", table_name="evento_acceso")
    op.drop_table("evento_acceso")
