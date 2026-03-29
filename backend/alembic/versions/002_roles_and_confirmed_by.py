"""roles operator_record/operator_verify + confirmed_by_user_id

Revision ID: 002
Revises: 001
Create Date: 2026-03-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL: новые значения enum нельзя использовать в той же транзакции, что и ADD VALUE.
    # autocommit_block коммитит ALTER TYPE до UPDATE и остальных шагов.
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'operator_record'"))
        op.execute(sa.text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'operator_verify'"))
    op.execute(
        sa.text(
            "UPDATE users SET role = 'operator_record'::userrole "
            "WHERE role::text = 'operator'"
        )
    )
    op.add_column(
        "voice_commands",
        sa.Column("confirmed_by_user_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_voice_commands_confirmed_by_user_id"),
        "voice_commands",
        ["confirmed_by_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_voice_commands_confirmed_by_user_id_users"),
        "voice_commands",
        "users",
        ["confirmed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_voice_commands_confirmed_by_user_id_users"),
        "voice_commands",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_voice_commands_confirmed_by_user_id"), table_name="voice_commands")
    op.drop_column("voice_commands", "confirmed_by_user_id")
    # Значения enum в PostgreSQL не удаляем; старые строки с operator_record останутся
