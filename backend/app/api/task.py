import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(tags=["tasks"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task_data: TaskCreate, db: DbSession) -> TaskResponse:
    try:
        return TaskService(db).create_task(task_data)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/tasks", response_model=list[TaskResponse])
def get_tasks(db: DbSession) -> list[TaskResponse]:
    return TaskService(db).get_tasks()


@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: uuid.UUID, db: DbSession) -> TaskResponse:
    task = TaskService(db).get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("/projects/{project_id}/tasks", response_model=list[TaskResponse])
def get_project_tasks(project_id: uuid.UUID, db: DbSession) -> list[TaskResponse]:
    try:
        return TaskService(db).get_tasks_by_project(project_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/employees/{employee_id}/tasks", response_model=list[TaskResponse])
def get_employee_tasks(employee_id: uuid.UUID, db: DbSession) -> list[TaskResponse]:
    try:
        return TaskService(db).get_tasks_by_employee(employee_id)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: uuid.UUID, task_data: TaskUpdate, db: DbSession) -> TaskResponse:
    try:
        task = TaskService(db).update_task(task_id, task_data)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: uuid.UUID, db: DbSession) -> None:
    if not TaskService(db).delete_task(task_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
