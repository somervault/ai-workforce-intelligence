import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee_external_identity import EmployeeExternalIdentity


class EmployeeExternalIdentityRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, identity: EmployeeExternalIdentity) -> EmployeeExternalIdentity:
        self.db.add(identity)
        self.db.commit()
        self.db.refresh(identity)
        return identity

    def get_by_id(self, mapping_id: uuid.UUID) -> EmployeeExternalIdentity | None:
        return self.db.get(EmployeeExternalIdentity, mapping_id)

    def get_by_employee_id(self, employee_id: uuid.UUID) -> list[EmployeeExternalIdentity]:
        return list(self.db.scalars(select(EmployeeExternalIdentity).where(EmployeeExternalIdentity.employee_id == employee_id).order_by(EmployeeExternalIdentity.created_at)))

    def get_active_by_external_id(self, provider: str, external_id: str) -> EmployeeExternalIdentity | None:
        statement = select(EmployeeExternalIdentity).where(
            EmployeeExternalIdentity.provider == provider,
            EmployeeExternalIdentity.external_id == external_id,
            EmployeeExternalIdentity.status == "active",
        )
        return self.db.scalar(statement)

    def get_active_by_employee_provider(self, employee_id: uuid.UUID, provider: str) -> EmployeeExternalIdentity | None:
        statement = select(EmployeeExternalIdentity).where(
            EmployeeExternalIdentity.employee_id == employee_id,
            EmployeeExternalIdentity.provider == provider,
            EmployeeExternalIdentity.status == "active",
        )
        return self.db.scalar(statement)

    def update(self, identity: EmployeeExternalIdentity, **values: object) -> EmployeeExternalIdentity:
        for field, value in values.items():
            setattr(identity, field, value)
        self.db.commit()
        self.db.refresh(identity)
        return identity
