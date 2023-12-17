from typing import List

from bson import json_util, ObjectId
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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
    Votes: int
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


@app.get("/projects/{projectId}", response_model=ProjectBase)
async def get_project(projectId: str):
    # Retrieve the project from the MongoDB collection
    project = await db.projects.find_one({"projectId": projectId})

    if project:
        # Convert BSON document to JSON and then to a ProjectBase object
        return ProjectBase(**json_util.loads(json_util.dumps(project)))
    else:
        raise HTTPException(status_code=404, detail=f"Project with projectId {projectId} not found")


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
    print("acas")
    # Retrieve all events from the MongoDB collection "events"
    events = await db["events"].find({}).to_list(None)
    print("qweew")
    # Convert BSON documents to JSON and then to a list of Event objects
    event_objects = [Event(**json_util.loads(json_util.dumps(event))) for event in events]
    print("acatrrts")
    return event_objects


@app.get("/events/{eventId}", response_model=Event)
async def get_event(eventId: str):
    # Retrieve the specific event from the MongoDB collection
    event = await db["events"].find_one({"eventId": eventId})

    if event:
        # Convert BSON document to JSON and then to an Event object
        return Event(**json_util.loads(json_util.dumps(event)))
    else:
        raise HTTPException(status_code=404, detail=f"Event with eventId {eventId} not found")


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


class EventCreate(BaseModel):
    eventName: str
    eventDescription: str
    img: str
    startDate: str  # You might want to use datetime or a proper format
    endDate: str  # You might want to use datetime or a proper format
    location: str
    mainSpeaker: str
    rules: str
    neededVotes: int  # or str, depending on your data type


class Event(EventCreate):
    eventId: str
    votes: int = 0


@app.post("/addEvents/", response_model=str)
async def create_event(event_data: EventCreate):
    event = event_data.dict()
    event['eventId'] = str(ObjectId())  # Generate unique eventId
    event['votes'] = 0  # Initialize votes to 0

    # Insert the event into the MongoDB collection
    await db["events"].insert_one(event)
    return event['eventId']


class EventAssociationRequest(BaseModel):
    ethereumAddress: str
    eventId: str

@app.post("/associateEvent")
async def associate_event(request: EventAssociationRequest):
    # Extract data from the request
    ethereum_address = request.ethereumAddress
    event_id = request.eventId

    # Find the user and update their events list
    update_result = await db["users"].update_one(
        {"ethereumAddress": ethereum_address},
        {"$push": {"events": event_id}}
    )

    if update_result.modified_count == 0:
        # If no user was updated, raise an exception
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Event associated successfully"}


class ProjectCreate(BaseModel):
    Industry: str
    ImageUrl: str  # URL or path to the image
    DaysLeft: int  # Consider using datetime
    ProjectName: str    # Consider using datetime
    ProjectDescription: str
    Raised: float  # Assuming this is the project lead/manager
    Investors: str
    MinInvestment: str
    Slogan: str
    Slogan2: str
    ReasonsToInvest: str


class Project(ProjectCreate):
    projectId: str
    Votes: int = 0


@app.post("/addProjects/", response_model=str)
async def create_project(project_data: ProjectCreate):
    print(4545)
    project = project_data.dict()
    project['projectId'] = str(ObjectId())  # Generate unique projectId
    project['Votes'] = 0

    # Insert the project into the MongoDB collection
    try:
        await db["projects"].insert_one(project)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return project['projectId']


class ProjectAssociationRequest(BaseModel):
    ethereumAddress: str
    projectId: str


@app.post("/associateProject")
async def associate_project(request: ProjectAssociationRequest):
    # Extract data from the request
    ethereum_address = request.ethereumAddress
    project_id = request.projectId

    # Find the user and update their events list
    update_result = await db["users"].update_one(
        {"ethereumAddress": ethereum_address},
        {"$push": {"projects": project_id}}
    )

    if update_result.modified_count == 0:
        # If no user was updated, raise an exception
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Event associated successfully"}
