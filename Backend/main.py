from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os 
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
#     expose_headers=["*"],
# )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


MONGODB_URL = os.getenv("MONGODB_URI")

mongodb_client = AsyncIOMotorClient(MONGODB_URL)

database = mongodb_client.AuraAI

# Import and setup auth routes after database is initialized
from auth.auth_routes import router as auth_router, set_database as set_auth_database
from meetings_routes import router as meetings_router, set_database as set_meetings_database
from settings_routes import router as settings_router, set_database as set_settings_database
from trans2action.routes import router as trans2actions_router, set_database as set_trans2actions_database
from userload.routes import router as userload_router, set_database as set_userload_database
from admin.routes import router as admin_router, set_database as set_admin_database
from composio_routes import router as composio_router, set_database as set_composio_database

# Set database for all routes
set_auth_database(database)
set_meetings_database(database)
set_settings_database(database)
set_trans2actions_database(database)
set_userload_database(database)
set_admin_database(database)
set_composio_database(database)

app.include_router(auth_router)
app.include_router(meetings_router)
app.include_router(settings_router)
app.include_router(trans2actions_router)
app.include_router(userload_router)
app.include_router(admin_router)
app.include_router(composio_router)

@app.get("/")
async def root():
    return {"message": "Welcome to AuraAI Backend"}

@app.get("/health")
async def health_check():

    await mongodb_client.admin.command('ping')
    
    return {
        "status": "healthy",
        "api": "running",
        "mongodb": "connected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app , port=8000)
