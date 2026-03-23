from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status

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
def list_presets():
    """List all available edge presets (built-in + custom)."""
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
def get_preset(preset_id: str):
    """Get a specific edge preset by its ID."""
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
def create_preset(data: EdgePresetCreate):
    """Create a new custom edge preset.

    Built-in presets cannot be modified. Custom presets are stored in Neo4j.
    """
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
def update_preset(preset_id: str, data: EdgePresetUpdate):
    """Update an existing custom edge preset.

    Built-in presets cannot be modified.
    """
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
def delete_preset(preset_id: str):
    """Delete a custom edge preset.

    Built-in presets cannot be deleted.
    """
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
