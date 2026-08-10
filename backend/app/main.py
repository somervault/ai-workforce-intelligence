from fastapi import FastAPI

from app.api.employee import router as employee_router
from app.api.employee_project import router as employee_project_router
from app.api.project import router as project_router
from app.config.settings import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(employee_router)
app.include_router(employee_project_router)
app.include_router(project_router)


@app.get("/")
def root():
    return {
        "message": f"{settings.app_name} API is running 🚀"
    }
