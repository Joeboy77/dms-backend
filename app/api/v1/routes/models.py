from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, responses
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.authentication.auth_middleware import get_current_token
from app.core.database import get_db
from app.schemas.models import ModelCreate, ModelPublic, ModelUpdate, Page
from app.schemas.token import TokenData

router = APIRouter(tags=["Models"])


@router.get("/models", response_model=Page)
async def get_all_model_details(
    limit: int = Query(10, alias="limit", ge=1, le=100),
    cursor: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    return await db["models"].find_all(
        limit=limit,
        cursor=cursor,
    )


@router.get("/models/{id}", response_model=ModelPublic)
async def get_model_details(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    model_details = await db["models"].find_one({"_id": ObjectId(id)})
    if model_details is None:
        raise HTTPException(status_code=404, detail="model not found")
    return model_details


@router.post("/models", response_model=ModelPublic)
async def save_model_details(
    model_details: ModelCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    try:
        model_details = model_details.model_dump()
        model_details["created_at"] = datetime.now()
        model_details["updated_at"] = None
        new_model_details = await db["models"].insert_one(model_details)
        created_model_details = await db["models"].find_one(
            {"_id": new_model_details.inserted_id}
        )
        return created_model_details

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/models/{id}", response_model=ModelPublic)
async def update_model_details(
    id: str,
    model_details: ModelUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    try:
        model_details = model_details.model_dump()
        model_details["updated_at"] = datetime.now()
        await db["models"].update_one(
            {"_id": ObjectId(id)},
            {"$set": model_details},
        )
        updated_model_details = await db["models"].find_one({"_id": ObjectId(id)})

        return updated_model_details

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/models/{id}", status_code=204)
async def delete_model_details(
    id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(get_current_token),
):
    try:
        deleted_model_details = await db["models"].delete_one({"_id": ObjectId(id)})

        if deleted_model_details.acknowledged:
            return responses.Response(status_code=204)

        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
