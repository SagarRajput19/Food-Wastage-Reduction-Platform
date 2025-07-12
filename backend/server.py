from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import hashlib
import os
import jwt
from pymongo import MongoClient
import json

# Initialize FastAPI app
app = FastAPI(title="Food Wastage Reduction Platform")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
SECRET_KEY = "food-wastage-secret-key-2025"

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = MongoClient(MONGO_URL)
db = client.food_wastage_db

# Collections
users_collection = db.users
listings_collection = db.food_listings
requests_collection = db.requests

# Pydantic models
class UserRegistration(BaseModel):
    name: str
    email: str
    password: str
    role: str  # "donor" or "ngo"
    phone: Optional[str] = None
    address: Optional[str] = None
    organization: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class FoodListing(BaseModel):
    title: str
    description: str
    quantity: str
    food_type: str  # "veg", "non-veg", "both"
    pickup_address: str
    expiry_hours: int  # How many hours until food expires
    image_url: Optional[str] = None

class PickupRequest(BaseModel):
    listing_id: str
    message: Optional[str] = None

class RequestAction(BaseModel):
    request_id: str
    action: str  # "accept" or "reject"

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# API Routes

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "food-wastage-platform"}

@app.post("/api/auth/register")
async def register(user_data: UserRegistration):
    # Check if user already exists
    existing_user = users_collection.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = hash_password(user_data.password)
    
    user_doc = {
        "user_id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "password": hashed_password,
        "role": user_data.role,
        "phone": user_data.phone,
        "address": user_data.address,
        "organization": user_data.organization,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True
    }
    
    users_collection.insert_one(user_doc)
    token = create_token(user_id, user_data.email, user_data.role)
    
    return {
        "message": "User registered successfully",
        "token": token,
        "user": {
            "user_id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "role": user_data.role
        }
    }

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    # Find user
    user = users_collection.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    hashed_password = hash_password(credentials.password)
    if user["password"] != hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["user_id"], user["email"], user["role"])
    
    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }

@app.get("/api/auth/me")
async def get_current_user(current_user: dict = Depends(verify_token)):
    user = users_collection.find_one({"user_id": current_user["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "phone": user.get("phone"),
        "address": user.get("address"),
        "organization": user.get("organization")
    }

@app.post("/api/listings")
async def create_food_listing(listing_data: FoodListing, current_user: dict = Depends(verify_token)):
    if current_user["role"] != "donor":
        raise HTTPException(status_code=403, detail="Only donors can create listings")
    
    listing_id = str(uuid.uuid4())
    expiry_time = datetime.utcnow() + timedelta(hours=listing_data.expiry_hours)
    
    listing_doc = {
        "listing_id": listing_id,
        "title": listing_data.title,
        "description": listing_data.description,
        "quantity": listing_data.quantity,
        "food_type": listing_data.food_type,
        "pickup_address": listing_data.pickup_address,
        "expiry_time": expiry_time.isoformat(),
        "image_url": listing_data.image_url,
        "posted_by": current_user["user_id"],
        "posted_by_name": current_user.get("name", ""),
        "status": "available",  # available, requested, picked_up, expired
        "created_at": datetime.utcnow().isoformat()
    }
    
    listings_collection.insert_one(listing_doc)
    
    return {
        "message": "Food listing created successfully",
        "listing_id": listing_id
    }

@app.get("/api/listings")
async def get_food_listings(current_user: dict = Depends(verify_token)):
    # Get all available listings for NGOs, or own listings for donors
    if current_user["role"] == "ngo":
        # NGOs see all available listings
        listings = list(listings_collection.find({
            "status": "available",
            "expiry_time": {"$gt": datetime.utcnow().isoformat()}
        }))
    else:
        # Donors see their own listings
        listings = list(listings_collection.find({
            "posted_by": current_user["user_id"]
        }))
    
    # Remove MongoDB _id and add additional info
    for listing in listings:
        listing.pop("_id", None)
        # Add time remaining
        expiry_time = datetime.fromisoformat(listing["expiry_time"])
        time_remaining = expiry_time - datetime.utcnow()
        listing["hours_remaining"] = max(0, int(time_remaining.total_seconds() / 3600))
    
    return {"listings": listings}

@app.get("/api/listings/{listing_id}")
async def get_listing_details(listing_id: str, current_user: dict = Depends(verify_token)):
    listing = listings_collection.find_one({"listing_id": listing_id})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    listing.pop("_id", None)
    
    # Add time remaining
    expiry_time = datetime.fromisoformat(listing["expiry_time"])
    time_remaining = expiry_time - datetime.utcnow()
    listing["hours_remaining"] = max(0, int(time_remaining.total_seconds() / 3600))
    
    # Get requests for this listing if user is the donor
    if current_user["user_id"] == listing["posted_by"]:
        requests = list(requests_collection.find({"listing_id": listing_id}))
        for req in requests:
            req.pop("_id", None)
            # Add requester info
            requester = users_collection.find_one({"user_id": req["requested_by"]})
            if requester:
                req["requester_name"] = requester["name"]
                req["requester_organization"] = requester.get("organization", "")
        listing["requests"] = requests
    
    return listing

@app.post("/api/listings/{listing_id}/request")
async def request_pickup(listing_id: str, request_data: PickupRequest, current_user: dict = Depends(verify_token)):
    if current_user["role"] != "ngo":
        raise HTTPException(status_code=403, detail="Only NGOs can request pickups")
    
    # Check if listing exists and is available
    listing = listings_collection.find_one({
        "listing_id": listing_id,
        "status": "available"
    })
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or not available")
    
    # Check if user already requested this listing
    existing_request = requests_collection.find_one({
        "listing_id": listing_id,
        "requested_by": current_user["user_id"]
    })
    if existing_request:
        raise HTTPException(status_code=400, detail="You have already requested this listing")
    
    request_id = str(uuid.uuid4())
    request_doc = {
        "request_id": request_id,
        "listing_id": listing_id,
        "requested_by": current_user["user_id"],
        "requested_by_name": current_user.get("name", ""),
        "message": request_data.message,
        "status": "pending",  # pending, accepted, rejected
        "requested_at": datetime.utcnow().isoformat()
    }
    
    requests_collection.insert_one(request_doc)
    
    return {
        "message": "Pickup request sent successfully",
        "request_id": request_id
    }

@app.post("/api/requests/{request_id}/action")
async def handle_request_action(request_id: str, action_data: RequestAction, current_user: dict = Depends(verify_token)):
    if current_user["role"] != "donor":
        raise HTTPException(status_code=403, detail="Only donors can accept/reject requests")
    
    # Find the request
    request_doc = requests_collection.find_one({"request_id": request_id})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check if the current user owns the listing
    listing = listings_collection.find_one({
        "listing_id": request_doc["listing_id"],
        "posted_by": current_user["user_id"]
    })
    if not listing:
        raise HTTPException(status_code=403, detail="You can only manage requests for your own listings")
    
    # Update request status
    requests_collection.update_one(
        {"request_id": request_id},
        {"$set": {
            "status": action_data.action + "ed",  # "accepted" or "rejected"
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
    
    # If accepted, update listing status and reject other requests
    if action_data.action == "accept":
        # Update listing status
        listings_collection.update_one(
            {"listing_id": request_doc["listing_id"]},
            {"$set": {"status": "requested"}}
        )
        
        # Reject all other pending requests for this listing
        requests_collection.update_many(
            {
                "listing_id": request_doc["listing_id"],
                "request_id": {"$ne": request_id},
                "status": "pending"
            },
            {"$set": {"status": "rejected"}}
        )
    
    return {"message": f"Request {action_data.action}ed successfully"}

@app.post("/api/listings/{listing_id}/complete")
async def mark_pickup_complete(listing_id: str, current_user: dict = Depends(verify_token)):
    if current_user["role"] != "donor":
        raise HTTPException(status_code=403, detail="Only donors can mark pickups as complete")
    
    # Check if listing belongs to current user
    listing = listings_collection.find_one({
        "listing_id": listing_id,
        "posted_by": current_user["user_id"]
    })
    if not listing:
        raise HTTPException(status_code=403, detail="You can only manage your own listings")
    
    # Update listing status
    listings_collection.update_one(
        {"listing_id": listing_id},
        {"$set": {
            "status": "picked_up",
            "completed_at": datetime.utcnow().isoformat()
        }}
    )
    
    return {"message": "Pickup marked as complete"}

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(verify_token)):
    if current_user["role"] == "donor":
        # Donor stats
        total_listings = listings_collection.count_documents({"posted_by": current_user["user_id"]})
        active_listings = listings_collection.count_documents({
            "posted_by": current_user["user_id"],
            "status": {"$in": ["available", "requested"]}
        })
        completed_pickups = listings_collection.count_documents({
            "posted_by": current_user["user_id"],
            "status": "picked_up"
        })
        
        return {
            "role": "donor",
            "total_listings": total_listings,
            "active_listings": active_listings,
            "completed_pickups": completed_pickups
        }
    else:
        # NGO stats
        total_requests = requests_collection.count_documents({"requested_by": current_user["user_id"]})
        accepted_requests = requests_collection.count_documents({
            "requested_by": current_user["user_id"],
            "status": "accepted"
        })
        completed_pickups = requests_collection.count_documents({
            "requested_by": current_user["user_id"],
            "status": "accepted"
        })
        
        return {
            "role": "ngo",
            "total_requests": total_requests,
            "accepted_requests": accepted_requests,
            "completed_pickups": completed_pickups
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)