"""Upload processing endpoints."""

from pathlib import Path
from threading import Thread

from fastapi import APIRouter, Depends, Form, Header, Query, Request
from fastapi.responses import FileResponse

from app.api.deps import validate_internal_api_key
from app.schemas.upload import ProcessUploadRequest, ProcessUploadResponse, UploadActor, UploadResponse
from app.services.process_upload_job import ProcessUploadJob
from app.services.upload_management_service import UploadManagementService, upload_processing_state, upload_to_summary
from app.services.upload_processor import UploadProcessor


router = APIRouter()


def current_actor(
    x_user_id: str = Header(...),
    x_user_role: str = Header(...),
    x_company_id: str | None = Header(default=None),
) -> UploadActor:
    return UploadActor(user_id=x_user_id, role=x_user_role, company_id=x_company_id)


def _parse_shared_user_ids(values: list[str] | None) -> list[str]:
    if not values:
        return []

    parsed: list[str] = []
    for value in values:
        parsed.extend(item.strip() for item in value.split(",") if item.strip())
    return parsed


@router.post(
    "/uploads",
    response_model=UploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
async def upload_files(
    request: Request,
    actor: UploadActor = Depends(current_actor),
) -> UploadResponse:
    form = await request.form()
    scope = str(form.get("scope") or "")
    visibility = str(form.get("visibility") or "private")
    company_id = _form_optional_string(form.get("company_id"))
    project_id = _form_optional_string(form.get("project_id"))
    task_id = _form_optional_string(form.get("task_id"))
    access_level = str(form.get("access_level") or "view")
    shared_with_user_ids = form.getlist("shared_with_user_ids") + form.getlist("shared_with_user_ids[]")
    service = UploadManagementService()
    created = []
    reused_count = 0
    upload_files = form.getlist("files") + form.getlist("files[]")

    if not upload_files:
        return UploadResponse(
            success=False,
            message="At least one file is required.",
            data={"uploads": []},
        )

    try:
        for file in upload_files:
            content = await file.read()
            stored = service.create_upload(
                file=file,
                content=content,
                actor=actor,
                scope=scope,
                visibility=visibility,
                company_id=company_id,
                project_id=project_id,
                task_id=task_id,
                shared_with_user_ids=_parse_shared_user_ids(shared_with_user_ids),
                access_level=access_level,
            )
            upload_payload = upload_to_summary(stored.upload).model_dump()
            upload_payload["already_exists"] = not stored.created
            upload_payload["has_ai_analysis"] = stored.upload.processing_status == "processed"
            if not stored.created:
                reused_count += 1
                upload_payload["message"] = (
                    "This file already exists and its AI analysis is ready."
                    if stored.upload.processing_status == "processed"
                    else "This file already exists and AI processing is already in progress."
                )
            created.append(upload_payload)
            if stored.created:
                Thread(target=ProcessUploadJob(stored.upload.id).run, daemon=True).start()
    finally:
        service.session.close()

    return UploadResponse(
        message="Existing processed file returned" if reused_count == len(created) else "Files uploaded successfully",
        data={"uploads": created},
    )


def _form_optional_string(value: object) -> str | None:
    if value is None:
        return None
    clean_value = str(value).strip()
    return clean_value or None


@router.get(
    "/uploads",
    response_model=UploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def list_uploads(
    scope: str | None = None,
    visibility: str | None = None,
    project_id: str | None = None,
    task_id: str | None = None,
    per_page: int = Query(50, ge=1, le=100),
    actor: UploadActor = Depends(current_actor),
) -> UploadResponse:
    service = UploadManagementService()
    try:
        uploads = service.list_uploads(
            actor=actor,
            scope=scope,
            visibility=visibility,
            project_id=project_id,
            task_id=task_id,
            per_page=per_page,
        )
        return UploadResponse(
            message="Uploads retrieved successfully",
            data={"uploads": [upload_to_summary(upload).model_dump() for upload in uploads]},
        )
    finally:
        service.session.close()


@router.get(
    "/uploads/list",
    response_model=UploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def list_uploads_alias(
    scope: str | None = None,
    visibility: str | None = None,
    project_id: str | None = None,
    task_id: str | None = None,
    per_page: int = Query(50, ge=1, le=100),
    actor: UploadActor = Depends(current_actor),
) -> UploadResponse:
    return list_uploads(scope, visibility, project_id, task_id, per_page, actor)


@router.get(
    "/uploads/mine",
    response_model=UploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def list_my_uploads(
    per_page: int = Query(50, ge=1, le=100),
    actor: UploadActor = Depends(current_actor),
) -> UploadResponse:
    service = UploadManagementService()
    try:
        uploads = service.list_uploads(actor=actor, per_page=per_page, mine_only=True)
        return UploadResponse(
            message="Uploads retrieved successfully",
            data={"uploads": [upload_to_summary(upload).model_dump() for upload in uploads]},
        )
    finally:
        service.session.close()


@router.get(
    "/uploads/{project_id}/list",
    response_model=UploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def list_project_uploads(
    project_id: str,
    per_page: int = Query(50, ge=1, le=100),
    actor: UploadActor = Depends(current_actor),
) -> UploadResponse:
    service = UploadManagementService()
    try:
        uploads = service.list_uploads(actor=actor, project_id=project_id, per_page=per_page)
        return UploadResponse(
            message="Project uploads retrieved successfully",
            data={"uploads": [upload_to_summary(upload).model_dump() for upload in uploads]},
        )
    finally:
        service.session.close()


@router.post(
    "/uploads/process",
    response_model=ProcessUploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def process_upload(request: ProcessUploadRequest) -> ProcessUploadResponse:
    return UploadProcessor().process(request)


@router.post("/meetings/upload", dependencies=[Depends(validate_internal_api_key)])
def upload_meeting() -> dict[str, str]:
    return {"status": "deprecated", "replacement": "/api/v1/uploads/process"}


@router.get("/uploads/{upload_id}/status", dependencies=[Depends(validate_internal_api_key)])
def get_upload_status(upload_id: str, actor: UploadActor = Depends(current_actor)) -> dict[str, str | int | None]:
    service = UploadManagementService()
    try:
        upload = service.get_upload(upload_id, actor=actor)
        state = upload_processing_state(upload)
        return {
            "upload_id": upload.id,
            "status": upload.processing_status,
            "stage": state["stage"],
            "progress": state["progress"],
            "message": state["message"],
            "processing_error": upload.processing_error,
        }
    finally:
        service.session.close()


@router.get(
    "/uploads/{upload_id}",
    response_model=UploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def get_upload(upload_id: str, actor: UploadActor = Depends(current_actor)) -> UploadResponse:
    service = UploadManagementService()
    try:
        upload = service.get_upload(upload_id, actor=actor)
        return UploadResponse(
            message="Upload retrieved successfully",
            data={"upload": service.get_detail(upload).model_dump()},
        )
    finally:
        service.session.close()


@router.get("/uploads/{upload_id}/download", dependencies=[Depends(validate_internal_api_key)])
def download_upload(upload_id: str, actor: UploadActor = Depends(current_actor)) -> FileResponse:
    service = UploadManagementService()
    try:
        upload = service.get_upload(upload_id, actor=actor)
        path = Path(upload.file_path)
        return FileResponse(
            path=path,
            media_type=upload.file_type or "application/octet-stream",
            filename=upload.file_name,
        )
    finally:
        service.session.close()


@router.delete(
    "/uploads/{upload_id}",
    response_model=UploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def delete_upload(upload_id: str, actor: UploadActor = Depends(current_actor)) -> UploadResponse:
    service = UploadManagementService()
    try:
        upload = service.soft_delete_upload(upload_id, actor=actor)
        return UploadResponse(
            message="Upload deleted successfully",
            data={"upload": upload_to_summary(upload).model_dump()},
        )
    finally:
        service.session.close()


@router.post(
    "/uploads/{upload_id}/permissions",
    response_model=UploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def add_upload_permission(
    upload_id: str,
    user_id: str = Form(...),
    access_level: str = Form("view"),
    actor: UploadActor = Depends(current_actor),
) -> UploadResponse:
    service = UploadManagementService()
    try:
        permission = service.add_permission(
            upload_id,
            actor=actor,
            user_id=user_id,
            access_level=access_level,
        )
        return UploadResponse(
            message="Upload permission saved successfully",
            data={
                "permission": {
                    "id": permission.id,
                    "upload_id": permission.upload_id,
                    "user_id": permission.user_id,
                    "access_level": permission.access_level,
                },
            },
        )
    finally:
        service.session.close()


@router.delete(
    "/uploads/{upload_id}/permissions/{user_id}",
    response_model=UploadResponse,
    dependencies=[Depends(validate_internal_api_key)],
)
def remove_upload_permission(
    upload_id: str,
    user_id: str,
    actor: UploadActor = Depends(current_actor),
) -> UploadResponse:
    service = UploadManagementService()
    try:
        service.remove_permission(upload_id, actor=actor, user_id=user_id)
        return UploadResponse(
            message="Upload permission deleted successfully",
            data={"upload_id": upload_id, "user_id": user_id},
        )
    finally:
        service.session.close()
