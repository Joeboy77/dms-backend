from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.database import get_db

router = APIRouter(tags=["Database"])


@router.get("/database/collections")
async def list_collections(db: AsyncIOMotorDatabase = Depends(get_db)):
    """
    List all collections in the database.
    """
    collections = await db.list_collection_names()
    return {"collections": collections}


def convert_objectid_to_str(obj):
    """Convert ObjectId to string recursively in dictionaries and lists"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectid_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    return obj


@router.get("/database/collections/{collection_name}")
async def collection_info(
    collection_name: str, db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get information about a specific collection including document count and sample documents.
    """
    collection = db[collection_name]

    # Get collection stats
    count = await collection.count_documents({})

    # Get a few sample documents (limit to 5)
    sample_docs = await collection.find({}).limit(5).to_list(length=5)

    # Convert ObjectIds to strings for JSON serialization
    sample_docs = convert_objectid_to_str(sample_docs)

    return {
        "collection_name": collection_name,
        "document_count": count,
        "sample_documents": sample_docs,
    }
