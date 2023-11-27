"""Create Item table

Revision ID: 8951ad679911
Revises: 9a8034043d03
Create Date: 2023-11-26 23:39:11.642997

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8951ad679911"
down_revision: Union[str, None] = "9a8034043d03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "items",
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("cost", sa.String(), nullable=True),
        sa.Column("link", sa.String(), nullable=True),
        sa.Column("image_file_path", sa.String(), nullable=True),
        sa.Column("claimed", sa.Boolean(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("items")
    # ### end Alembic commands ###
