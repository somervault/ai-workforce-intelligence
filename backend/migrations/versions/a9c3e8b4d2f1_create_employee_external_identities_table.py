"""create employee external identities table

Revision ID: a9c3e8b4d2f1
Revises: f2a8c5d1e4b7
Create Date: 2026-08-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a9c3e8b4d2f1"
down_revision: Union[str, Sequence[str], None] = "f2a8c5d1e4b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_external_identities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("external_login", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.CheckConstraint("provider IN ('jira', 'github')", name="ck_external_identity_provider"),
        sa.CheckConstraint("status IN ('active', 'inactive', 'deleted')", name="ck_external_identity_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_external_identities_employee_id", "employee_external_identities", ["employee_id"])
    op.create_index("uq_active_external_identity", "employee_external_identities", ["provider", "external_id"], unique=True, postgresql_where=sa.text("status = 'active'"))
    op.create_index("uq_active_employee_provider_identity", "employee_external_identities", ["employee_id", "provider"], unique=True, postgresql_where=sa.text("status = 'active'"))


def downgrade() -> None:
    op.drop_index("uq_active_employee_provider_identity", table_name="employee_external_identities")
    op.drop_index("uq_active_external_identity", table_name="employee_external_identities")
    op.drop_index("ix_employee_external_identities_employee_id", table_name="employee_external_identities")
    op.drop_table("employee_external_identities")
