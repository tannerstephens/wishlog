"""Adds desire column to item

Revision ID: dc260f21196f
Revises: 1b6043dfe203
Create Date: 2024-11-25 23:48:44.908945

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dc260f21196f"
down_revision: Union[str, None] = "1b6043dfe203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("items", sa.Column("desire", sa.Integer(), nullable=False, server_default="50"))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("items", "desire")
    # ### end Alembic commands ###
