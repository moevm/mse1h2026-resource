from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.auth import CurrentUser
from app.models.mapper.edge_preset import (
    EdgePreset,
    EdgePresetCreate,
    EdgePresetUpdate,
    EdgePresetListResponse,
)
from app.repositories.edge_preset_repo import edge_preset_repo

router = APIRouter()


@router.get(
    "",
    response_model=EdgePresetListResponse,
    summary="List all edge presets",
)
def list_presets(user: CurrentUser):
    presets = edge_preset_repo.list_all()
    return EdgePresetListResponse(
        presets=presets,
        total=len(presets),
    )


@router.get(
    "/{preset_id}",
    response_model=EdgePreset,
    summary="Get an edge preset by ID",
)
def get_preset(user: CurrentUser, preset_id: str):
    preset = edge_preset_repo.get(preset_id)
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge preset '{preset_id}' not found",
        )
    return preset


@router.post(
    "",
    response_model=EdgePreset,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new edge preset",
)
def create_preset(user: CurrentUser, data: EdgePresetCreate):
    try:
        return edge_preset_repo.create(data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create preset: {str(e)}",
        )


@router.put(
    "/{preset_id}",
    response_model=EdgePreset,
    summary="Update an edge preset",
)
def update_preset(user: CurrentUser, preset_id: str, data: EdgePresetUpdate):
    try:
        preset = edge_preset_repo.update(preset_id, data)
        if not preset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Edge preset '{preset_id}' not found",
            )
        return preset
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{preset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an edge preset",
)
def delete_preset(user: CurrentUser, preset_id: str):
    try:
        if not edge_preset_repo.delete(preset_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Edge preset '{preset_id}' not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
