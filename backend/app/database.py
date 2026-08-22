import motor.motor_asyncio
from app.config import settings

client: motor.motor_asyncio.AsyncIOMotorClient = None
db = None

async def connect_db():
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.evaluations.create_index("teacher_id")
    print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")

async def disconnect_db():
    global client
    if client:
        client.close()
        print("🔌 Disconnected from MongoDB")

def get_db():
    return db
