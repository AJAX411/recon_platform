"""PuntoAcceso, DispositivoEdge y EventoAuditoria general mínima.

Revision ID: 0005_puntos_edge_auditoria
Revises: 0004_auditoria_personas
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0005_puntos_edge_auditoria"
down_revision = "0004_auditoria_personas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    entero_id = sa.Integer().with_variant(mysql.INTEGER(unsigned=True), "mysql")
    op.create_table(
        "punto_acceso",
        sa.Column("id_punto_acceso", entero_id, primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("descripcion", sa.String(150), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("codigo", name="uq_punto_acceso_codigo"),
        sa.CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')", name="ck_punto_acceso_estado"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_punto_acceso_estado", "punto_acceso", ["estado"])
    op.create_table(
        "dispositivo_edge",
        sa.Column("id_dispositivo", entero_id, primary_key=True, autoincrement=True),
        sa.Column("id_punto_acceso", entero_id, nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("modo_operacion", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("ultima_comunicacion", sa.DateTime(), nullable=True),
        sa.Column("fecha_creacion", sa.DateTime(), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["id_punto_acceso"], ["punto_acceso.id_punto_acceso"],
                                name="fk_dispositivo_edge_punto", ondelete="RESTRICT"),
        sa.UniqueConstraint("codigo", name="uq_dispositivo_edge_codigo"),
        sa.CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')", name="ck_dispositivo_edge_estado"),
        sa.CheckConstraint("modo_operacion IN ('ENTRADA', 'SALIDA', 'AUTOMATICO')", name="ck_dispositivo_edge_modo"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_dispositivo_edge_id_punto_acceso", "dispositivo_edge", ["id_punto_acceso"])
    op.create_index("ix_dispositivo_edge_estado", "dispositivo_edge", ["estado"])
    op.create_table(
        "evento_auditoria",
        sa.Column("id_auditoria", entero_id, primary_key=True, autoincrement=True),
        sa.Column("id_usuario_actor", entero_id, nullable=True),
        sa.Column("tipo_actor", sa.String(20), nullable=False),
        sa.Column("accion", sa.String(50), nullable=False),
        sa.Column("recurso_tipo", sa.String(50), nullable=True),
        sa.Column("id_recurso_afectado", sa.String(100), nullable=True),
        sa.Column("resultado", sa.String(20), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("fecha_hora", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["id_usuario_actor"], ["usuario_plataforma.id_usuario"],
                                name="fk_evento_auditoria_actor", ondelete="RESTRICT"),
        sa.CheckConstraint("tipo_actor IN ('USUARIO', 'SISTEMA')", name="ck_evento_auditoria_tipo_actor"),
        sa.CheckConstraint("resultado IN ('EXITOSO', 'FALLIDO')", name="ck_evento_auditoria_resultado"),
        sa.CheckConstraint("(tipo_actor = 'USUARIO' AND id_usuario_actor IS NOT NULL) OR (tipo_actor = 'SISTEMA' AND id_usuario_actor IS NULL)", name="ck_evento_auditoria_actor"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_evento_auditoria_id_usuario_actor", "evento_auditoria", ["id_usuario_actor"])
    op.create_index("ix_evento_auditoria_accion", "evento_auditoria", ["accion"])
    op.create_index("ix_evento_auditoria_fecha_hora", "evento_auditoria", ["fecha_hora"])
    op.create_index("ix_evento_auditoria_recurso", "evento_auditoria", ["recurso_tipo", "id_recurso_afectado"])


def downgrade() -> None:
    op.drop_index("ix_evento_auditoria_recurso", table_name="evento_auditoria")
    op.drop_index("ix_evento_auditoria_fecha_hora", table_name="evento_auditoria")
    op.drop_index("ix_evento_auditoria_accion", table_name="evento_auditoria")
    op.drop_index("ix_evento_auditoria_id_usuario_actor", table_name="evento_auditoria")
    op.drop_table("evento_auditoria")
    op.drop_index("ix_dispositivo_edge_estado", table_name="dispositivo_edge")
    op.drop_index("ix_dispositivo_edge_id_punto_acceso", table_name="dispositivo_edge")
    op.drop_table("dispositivo_edge")
    op.drop_index("ix_punto_acceso_estado", table_name="punto_acceso")
    op.drop_table("punto_acceso")
