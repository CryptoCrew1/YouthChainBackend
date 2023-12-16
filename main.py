from typing import List

from bson import json_util
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient


app = FastAPI()

# MongoDB Configuration
MONGODB_URL = "mongodb://localhost:27017"
DB_NAME = "youthchain"

# MongoDB connection
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DB_NAME]

# Define Pydantic models for request and response data
class UserCreate(BaseModel):
    ethereumAddress: str
    projects: list[str] = []
    events: list[str] = []
    watchlist: list[str] = []


class User(BaseModel):
    ethereumAddress: str
    projects: list[str]
    events: list[str]
    watchlist: list[str]


# Routes
@app.post("/user/", response_model=User)
async def create_or_get_user(user_data: UserCreate):
    # Check if the user exists in the database
    existing_user = await db.users.find_one({"ethereumAddress": user_data.ethereumAddress})

    if existing_user:
        # If the user exists, return the existing user
        return existing_user

    # If the user does not exist, create a new one
    new_user = user_data.dict()
    result = await db.users.insert_one(new_user)
    new_user["_id"] = str(result.inserted_id)

    return new_user


class ProjectBase(BaseModel):
    projectId: str
    Industry: str
    ImageUrl: str
    DaysLeft: int
    ProjectName: str
    ProjectDescription: str
    Raised: int
    Investors: str
    Votes: str
    MinInvestment: str
    Slogan: str
    Slogan2: str
    ReasonsToInvest: str


# Route to get all projects
@app.get("/projects/", response_model=List[ProjectBase])
async def get_all_projects():
    # Retrieve all projects from the MongoDB collection
    projects = await db.projects.find({}).to_list(None)

    # Convert BSON documents to JSON and then to a list of ProjectBase objects
    project_objects = [ProjectBase(**json_util.loads(json_util.dumps(project))) for project in projects]

    return project_objects


@app.get("/user/projects/{ethereum_address}/", response_model=List[ProjectBase])
async def get_user_projects(ethereum_address: str):
    # Check if the user exists in the database
    existing_user = await db.users.find_one({"ethereumAddress": ethereum_address})

    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    user_projects = existing_user.get("projects", [])

    # Retrieve projects with project IDs in the user's project list
    projects = await db.projects.find({"projectId": {"$in": user_projects}}).to_list(None)

    # Convert BSON documents to JSON and then to a list of ProjectBase objects
    project_objects = [ProjectBase(**json_util.loads(json_util.dumps(project))) for project in projects]

    return project_objects


class Event(BaseModel):
    eventId: str
    eventName: str
    eventDescription: str
    startDate: str
    endDate: str
    location: str
    img: str
    mainSpeaker: str
    rules: str
    votes: int
    neededVotes: int


@app.get("/events/", response_model=List[Event])
async def get_all_events():
    # Retrieve all events from the MongoDB collection "events"
    events = await db["events"].find({}).to_list(None)

    # Convert BSON documents to JSON and then to a list of Event objects
    event_objects = [Event(**json_util.loads(json_util.dumps(event))) for event in events]

    return event_objects


@app.get("/user/events/{ethereum_address}/", response_model=List[Event])
async def get_user_events(ethereum_address: str):
    # Check if the user exists in the database
    existing_user = await db.users.find_one({"ethereumAddress": ethereum_address})

    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    user_events = existing_user.get("events", [])

    # Retrieve events with event IDs in the user's events list
    events = await db.events.find({"eventId": {"$in": user_events}}).to_list(None)

    # Convert BSON documents to JSON and then to a list of Event objects
    event_objects = [Event(**json_util.loads(json_util.dumps(event))) for event in events]

    return event_objects


class WatchlistRequest(BaseModel):
    ethereum_address: str
    project_id: str


@app.post("/user/add-to-watchlist/")
async def add_project_to_watchlist(watch_data: WatchlistRequest):
    # Check if the user exists in the database
    existing_user = await db.users.find_one({"ethereumAddress": watch_data.ethereum_address})

    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the project ID exists in the "projects" collection
    project = await db.projects.find_one({"projectId": watch_data.project_id})



    # Check if the project ID is already in the user's watchlist
    if watch_data.project_id in existing_user.get("watchlist", []):
        raise HTTPException(status_code=400, detail="Project already in watchlist")

    # Add the project ID to the user's watchlist
    existing_user.setdefault("watchlist", []).append(watch_data.project_id)

    # Update the user in the database
    await db.users.update_one({"ethereumAddress": watch_data.ethereum_address}, {"$set": existing_user})

    return {"message": f"Project ID {watch_data.project_id} added to the watchlist"}


@app.post("/user/remove-from-watchlist/")
async def remove_project_from_watchlist(request: WatchlistRequest):
    # Check if the user exists in the database
    existing_user = await db.users.find_one({"ethereumAddress": request.ethereum_address})

    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if the project ID exists in the user's watchlist
    if request.project_id not in existing_user.get("watchlist", []):
        raise HTTPException(status_code=404, detail="Project not found in watchlist")

    # Remove the project ID from the user's watchlist
    existing_user['watchlist'].remove(request.project_id)

    # Update the user in the database
    await db.users.update_one({"ethereumAddress": request.ethereum_address}, {"$set": existing_user})

    return {"message": f"Project ID {request.project_id} removed from the watchlist"}