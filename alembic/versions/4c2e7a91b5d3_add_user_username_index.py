"""Add case-insensitive unique index on username

Revision ID: 4c2e7a91b5d3
Revises: dc260f21196f
Create Date: 2026-11-08 16:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c2e7a91b5d3"
down_revision: Union[str, None] = "dc260f21196f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Usernames have always been stored lowercased, so existing rows can't conflict
    op.create_index(
        "user_username_idx", "users", [sa.text("lower(username)")], unique=True
    )


def downgrade() -> None:
    op.drop_index("user_username_idx", table_name="users")
