from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.workforce_activity_service import WorkforceActivityService
from app.ai.workforce_activity_schemas import WorkforceAnalysisResultDTO
from app.database.session import get_db

router = APIRouter(prefix="/workforce", tags=["workforce"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/analysis", response_model=WorkforceAnalysisResultDTO)
def get_workforce_analysis(db: DbSession) -> WorkforceAnalysisResultDTO:
    service = WorkforceActivityService(db)
    return service.analyze()
