"""seed categorias poi: informacion turistica, ermitas y marinas

Revision ID: 2cb0f4ad4086
Revises: 2afd742cbc8a
Create Date: 2026-08-04 17:19:25.247591

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cb0f4ad4086'
down_revision: Union[str, Sequence[str], None] = '2afd742cbc8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    dim_poi_category = sa.table(
        "dim_poi_category",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
    )
    op.bulk_insert(
        dim_poi_category,
        [
            {"code": "informacion_turistica", "name": "Oficinas de información turística"},
            {"code": "ermitas_cruces", "name": "Ermitas y cruces de camino"},
            {"code": "marinas_resorts", "name": "Marinas, resorts y parques acuáticos"},
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    dim_poi_category = sa.table("dim_poi_category", sa.column("code", sa.String))
    op.execute(
        dim_poi_category.delete().where(
            dim_poi_category.c.code.in_(
                ["informacion_turistica", "ermitas_cruces", "marinas_resorts"]
            )
        )
    )
