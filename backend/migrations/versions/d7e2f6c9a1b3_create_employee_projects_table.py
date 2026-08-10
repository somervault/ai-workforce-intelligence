"""create employee projects table

Revision ID: d7e2f6c9a1b3
Revises: c5e1d4a8b0f2
Create Date: 2026-08-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e2f6c9a1b3"
down_revision: Union[str, Sequence[str], None] = "c5e1d4a8b0f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_projects",
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("employee_id", "project_id"),
    )


def downgrade() -> None:
    op.drop_table("employee_projects")
