"""create employees table

Revision ID: 05f8c7d4e1a2
Revises: 7ac644ab63ee
Create Date: 2026-08-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "05f8c7d4e1a2"
down_revision: Union[str, Sequence[str], None] = "7ac644ab63ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("employee_code", sa.String(length=20), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("designation", sa.String(length=100), nullable=False),
        sa.Column("department_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_employees_employee_code", "employees", ["employee_code"], unique=True
    )
    op.create_index("ix_employees_email", "employees", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_employees_email", table_name="employees")
    op.drop_index("ix_employees_employee_code", table_name="employees")
    op.drop_table("employees")
