from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

MONGO_URL = settings.MONGO_URL

mongo_client = AsyncIOMotorClient(MONGO_URL)

db = mongo_client[settings.DB_NAME]

async def get_db():
    yield db

