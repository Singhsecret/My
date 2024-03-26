from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
from pymongo import MongoClient

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['notes_app']
users_collection = db['users']
notes_collection = db['notes']

# FastAPI app
app = FastAPI()

# Models
class Note(BaseModel):
    title: str
    content: str
    owner_id: str

class User(BaseModel):
    username: str
    password: str

class UserInDB(User):
    id: str

# Authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Functions to simulate user and note operations
def get_user(username: str):
    return users_collection.find_one({"username": username})

def create_user(user: User):
    user_id = users_collection.insert_one(user.dict()).inserted_id
    return str(user_id)

def get_notes(owner_id: str):
    return list(notes_collection.find({"owner_id": owner_id}))

def create_note(note: Note):
    note_id = notes_collection.insert_one(note.dict()).inserted_id
    return str(note_id)

def get_note_by_id(note_id: str, owner_id: str):
    return notes_collection.find_one({"_id": ObjectId(note_id), "owner_id": owner_id})

def update_note(note_id: str, note: Note, owner_id: str):
    updated_note = notes_collection.update_one({"_id": ObjectId(note_id), "owner_id": owner_id}, {"$set": note.dict()})
    if updated_note.modified_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Note updated successfully"}

def delete_note(note_id: str, owner_id: str):
    result = notes_collection.delete_one({"_id": ObjectId(note_id), "owner_id": owner_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"message": "Note deleted successfully"}

# Routes
@app.post("/api/auth/signup")
def signup(user: User):
    existing_user = get_user(user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    user_id = create_user(user)
    return {"user_id": user_id}

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user(form_data.username)
    if not user or user.password != form_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": user["username"]}  # For simplicity, using username as access token

@app.get("/api/notes")
def get_user_notes(token: str = Depends(oauth2_scheme)):
    user = get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    notes = get_notes(user['_id'])
    return notes

@app.get("/api/notes/{note_id}")
def get_single_note(note_id: str, token: str = Depends(oauth2_scheme)):
    user = get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    note = get_note_by_id(note_id, user['_id'])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.post("/api/notes")
def create_single_note(note: Note, token: str = Depends(oauth2_scheme)):
    user = get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    note.owner_id = user['_id']
    note_id = create_note(note)
    return {"note_id": note_id}

@app.put("/api/notes/{note_id}")
def update_single_note(note_id: str, note: Note, token: str = Depends(oauth2_scheme)):
    user = get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    update_note(note_id, note, user['_id'])
    return {"message": "Note updated successfully"}

@app.delete("/api/notes/{note_id}")
def delete_single_note(note_id: str, token: str = Depends(oauth2_scheme)):
    user = get_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    delete_note(note_id, user['_id'])
    return {"message": "Note deleted successfully"}
