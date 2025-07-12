from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import hashlib
import os
import jwt
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
import json
import asyncio
from dataclasses import dataclass
import math

# Initialize FastAPI app
app = FastAPI(title="Food Wastage Reduction Platform - Enhanced")

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
notifications_collection = db.notifications

# Create indexes for better performance
try:
    # Text index for search functionality
    listings_collection.create_index([
        ("title", TEXT),
        ("description", TEXT),
        ("pickup_address", TEXT)
    ])
    
    # Compound indexes for better query performance
    listings_collection.create_index([("status", ASCENDING), ("expiry_time", ASCENDING)])
    listings_collection.create_index([("posted_by", ASCENDING), ("created_at", DESCENDING)])
    requests_collection.create_index([("listing_id", ASCENDING), ("status", ASCENDING)])
    notifications_collection.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    
    print("✅ Database indexes created successfully")
except Exception as e:
    print(f"⚠️  Index creation error: {e}")

# WebSocket Connection Manager for real-time notifications
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except:
                # Connection may be closed, remove it
                self.disconnect(user_id)

    async def send_notification(self, user_id: str, notification_type: str, title: str, message: str, data: dict = None):
        # Store notification in database
        notification_doc = {
            "notification_id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "read": False,
            "created_at": datetime.utcnow().isoformat()
        }
        notifications_collection.insert_one(notification_doc)
        
        # Send real-time notification
        await self.send_personal_message({
            "type": "notification",
            "notification": notification_doc
        }, user_id)

manager = ConnectionManager()

# Pydantic models
class UserRegistration(BaseModel):
    name: str
    email: str
    password: str
    role: str  # "donor", "ngo", "admin"
    phone: Optional[str] = None
    address: Optional[str] = None
    organization: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class UserLogin(BaseModel):
    email: str
    password: str

class FoodListing(BaseModel):
    title: str
    description: str
    quantity: str
    food_type: str  # "veg", "non-veg", "both"
    pickup_address: str
    expiry_hours: int
    image_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    category: Optional[str] = "other"  # "prepared_food", "raw_ingredients", "packaged", "other"
    urgency: Optional[str] = "medium"  # "low", "medium", "high"

class PickupRequest(BaseModel):
    listing_id: str
    message: Optional[str] = None

class RequestAction(BaseModel):
    request_id: str
    action: str  # "accept" or "reject"

class SearchFilters(BaseModel):
    food_type: Optional[str] = None
    category: Optional[str] = None
    urgency: Optional[str] = None
    max_distance: Optional[float] = None
    search_query: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class AdminAction(BaseModel):
    action: str  # "approve", "suspend", "delete"
    reason: Optional[str] = None

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

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    if not all([lat1, lon1, lat2, lon2]):
        return float('inf')
    
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat/2) * math.sin(dlat/2) + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2) * math.sin(dlon/2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    
    return distance

def requires_admin(current_user: dict = Depends(verify_token)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# WebSocket endpoint for real-time notifications
@app.websocket("/api/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# API Routes
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "food-wastage-platform-enhanced", "version": "2.0"}

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
        "latitude": user_data.latitude,
        "longitude": user_data.longitude,
        "created_at": datetime.utcnow().isoformat(),
        "is_active": True,
        "is_verified": user_data.role != "ngo",  # NGOs require verification
        "rating": 5.0,
        "total_donations": 0,
        "total_pickups": 0
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
            "role": user_data.role,
            "is_verified": user_doc["is_verified"]
        }
    }

@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    # Find user
    user = users_collection.find_one({"email": credentials.email})
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Invalid credentials or account suspended")
    
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
            "role": user["role"],
            "is_verified": user.get("is_verified", True)
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
        "organization": user.get("organization"),
        "latitude": user.get("latitude"),
        "longitude": user.get("longitude"),
        "is_verified": user.get("is_verified", True),
        "rating": user.get("rating", 5.0),
        "total_donations": user.get("total_donations", 0),
        "total_pickups": user.get("total_pickups", 0)
    }

@app.post("/api/listings")
async def create_food_listing(listing_data: FoodListing, current_user: dict = Depends(verify_token), background_tasks: BackgroundTasks):
    if current_user["role"] not in ["donor", "admin"]:
        raise HTTPException(status_code=403, detail="Only donors can create listings")
    
    listing_id = str(uuid.uuid4())
    expiry_time = datetime.utcnow() + timedelta(hours=listing_data.expiry_hours)
    
    listing_doc = {
        "listing_id": listing_id,
        "title": listing_data.title,
        "description": listing_data.description,
        "quantity": listing_data.quantity,
        "food_type": listing_data.food_type,
        "category": listing_data.category,
        "urgency": listing_data.urgency,
        "pickup_address": listing_data.pickup_address,
        "latitude": listing_data.latitude,
        "longitude": listing_data.longitude,
        "expiry_time": expiry_time.isoformat(),
        "image_url": listing_data.image_url,
        "posted_by": current_user["user_id"],
        "posted_by_name": current_user.get("name", ""),
        "status": "available",
        "created_at": datetime.utcnow().isoformat(),
        "views": 0,
        "requests_count": 0
    }
    
    listings_collection.insert_one(listing_doc)
    
    # Update user donation count
    users_collection.update_one(
        {"user_id": current_user["user_id"]},
        {"$inc": {"total_donations": 1}}
    )
    
    # Send notifications to nearby NGOs (background task)
    background_tasks.add_task(notify_nearby_ngos, listing_doc)
    
    return {
        "message": "Food listing created successfully",
        "listing_id": listing_id
    }

async def notify_nearby_ngos(listing_doc: dict):
    """Notify NGOs within reasonable distance about new food listing"""
    if not listing_doc.get("latitude") or not listing_doc.get("longitude"):
        return
    
    # Find NGOs within 50km radius
    ngos = users_collection.find({
        "role": "ngo",
        "is_active": True,
        "is_verified": True,
        "latitude": {"$exists": True},
        "longitude": {"$exists": True}
    })
    
    for ngo in ngos:
        distance = calculate_distance(
            listing_doc["latitude"], listing_doc["longitude"],
            ngo["latitude"], ngo["longitude"]
        )
        
        if distance <= 50:  # 50km radius
            await manager.send_notification(
                ngo["user_id"],
                "new_listing",
                "New Food Donation Nearby!",
                f"'{listing_doc['title']}' is available {distance:.1f}km away",
                {"listing_id": listing_doc["listing_id"], "distance": distance}
            )

@app.get("/api/listings")
async def get_food_listings(
    current_user: dict = Depends(verify_token),
    filters: SearchFilters = Depends(),
    skip: int = 0,
    limit: int = 20
):
    query = {}
    
    if current_user["role"] == "ngo":
        # NGOs see available listings with filters
        query["status"] = "available"
        query["expiry_time"] = {"$gt": datetime.utcnow().isoformat()}
        
        # Apply filters
        if filters.food_type:
            query["food_type"] = filters.food_type
        if filters.category:
            query["category"] = filters.category
        if filters.urgency:
            query["urgency"] = filters.urgency
        if filters.search_query:
            query["$text"] = {"$search": filters.search_query}
            
    elif current_user["role"] == "donor":
        # Donors see their own listings
        query["posted_by"] = current_user["user_id"]
    elif current_user["role"] == "admin":
        # Admins see all listings
        pass
    
    # Get listings
    cursor = listings_collection.find(query).sort("created_at", DESCENDING).skip(skip).limit(limit)
    listings = list(cursor)
    
    # Calculate distance and add additional info
    for listing in listings:
        listing.pop("_id", None)
        
        # Calculate time remaining
        expiry_time = datetime.fromisoformat(listing["expiry_time"])
        time_remaining = expiry_time - datetime.utcnow()
        listing["hours_remaining"] = max(0, int(time_remaining.total_seconds() / 3600))
        
        # Calculate distance for NGOs
        if (current_user["role"] == "ngo" and 
            filters.latitude and filters.longitude and
            listing.get("latitude") and listing.get("longitude")):
            
            distance = calculate_distance(
                filters.latitude, filters.longitude,
                listing["latitude"], listing["longitude"]
            )
            listing["distance_km"] = round(distance, 1)
        
        # Increment view count for NGOs
        if current_user["role"] == "ngo":
            listings_collection.update_one(
                {"listing_id": listing["listing_id"]},
                {"$inc": {"views": 1}}
            )
    
    # Sort by distance if location provided
    if (current_user["role"] == "ngo" and filters.latitude and filters.longitude):
        listings.sort(key=lambda x: x.get("distance_km", float('inf')))
        
        # Apply distance filter
        if filters.max_distance:
            listings = [l for l in listings if l.get("distance_km", float('inf')) <= filters.max_distance]
    
    return {"listings": listings, "total": len(listings)}

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
    
    # Get requests for this listing if user is the donor or admin
    if current_user["user_id"] == listing["posted_by"] or current_user["role"] == "admin":
        requests = list(requests_collection.find({"listing_id": listing_id}))
        for req in requests:
            req.pop("_id", None)
            # Add requester info
            requester = users_collection.find_one({"user_id": req["requested_by"]})
            if requester:
                req["requester_name"] = requester["name"]
                req["requester_organization"] = requester.get("organization", "")
                req["requester_rating"] = requester.get("rating", 5.0)
        listing["requests"] = requests
    
    return listing

@app.post("/api/listings/{listing_id}/request")
async def request_pickup(
    listing_id: str, 
    request_data: PickupRequest, 
    current_user: dict = Depends(verify_token),
    background_tasks: BackgroundTasks
):
    if current_user["role"] != "ngo":
        raise HTTPException(status_code=403, detail="Only NGOs can request pickups")
    
    if not users_collection.find_one({"user_id": current_user["user_id"], "is_verified": True}):
        raise HTTPException(status_code=403, detail="NGO account needs to be verified")
    
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
        "status": "pending",
        "requested_at": datetime.utcnow().isoformat()
    }
    
    requests_collection.insert_one(request_doc)
    
    # Update listing request count
    listings_collection.update_one(
        {"listing_id": listing_id},
        {"$inc": {"requests_count": 1}}
    )
    
    # Notify the donor about the new request
    background_tasks.add_task(
        manager.send_notification,
        listing["posted_by"],
        "new_request",
        "New Pickup Request!",
        f"'{current_user.get('name', 'An NGO')}' wants to pick up '{listing['title']}'",
        {"listing_id": listing_id, "request_id": request_id}
    )
    
    return {
        "message": "Pickup request sent successfully",
        "request_id": request_id
    }

@app.post("/api/requests/{request_id}/action")
async def handle_request_action(
    request_id: str, 
    action_data: RequestAction, 
    current_user: dict = Depends(verify_token),
    background_tasks: BackgroundTasks
):
    if current_user["role"] not in ["donor", "admin"]:
        raise HTTPException(status_code=403, detail="Only donors can accept/reject requests")
    
    # Find the request
    request_doc = requests_collection.find_one({"request_id": request_id})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Check if the current user owns the listing (or is admin)
    listing = listings_collection.find_one({
        "listing_id": request_doc["listing_id"],
        "posted_by": current_user["user_id"]
    })
    if not listing and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="You can only manage requests for your own listings")
    
    # Update request status
    requests_collection.update_one(
        {"request_id": request_id},
        {"$set": {
            "status": action_data.action + "ed",
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
        
        # Notify the NGO about acceptance
        background_tasks.add_task(
            manager.send_notification,
            request_doc["requested_by"],
            "request_accepted",
            "Pickup Request Accepted! 🎉",
            f"Your request for '{listing['title']}' has been accepted. Please coordinate pickup.",
            {"listing_id": request_doc["listing_id"], "request_id": request_id}
        )
    else:
        # Notify the NGO about rejection
        background_tasks.add_task(
            manager.send_notification,
            request_doc["requested_by"],
            "request_rejected",
            "Pickup Request Declined",
            f"Your request for '{listing['title']}' has been declined.",
            {"listing_id": request_doc["listing_id"], "request_id": request_id}
        )
    
    return {"message": f"Request {action_data.action}ed successfully"}

@app.post("/api/listings/{listing_id}/complete")
async def mark_pickup_complete(
    listing_id: str, 
    current_user: dict = Depends(verify_token),
    background_tasks: BackgroundTasks
):
    if current_user["role"] not in ["donor", "admin"]:
        raise HTTPException(status_code=403, detail="Only donors can mark pickups as complete")
    
    # Check if listing belongs to current user
    listing = listings_collection.find_one({
        "listing_id": listing_id,
        "posted_by": current_user["user_id"]
    })
    if not listing and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="You can only manage your own listings")
    
    # Update listing status
    listings_collection.update_one(
        {"listing_id": listing_id},
        {"$set": {
            "status": "picked_up",
            "completed_at": datetime.utcnow().isoformat()
        }}
    )
    
    # Find the accepted request and update NGO pickup count
    accepted_request = requests_collection.find_one({
        "listing_id": listing_id,
        "status": "accepted"
    })
    
    if accepted_request:
        users_collection.update_one(
            {"user_id": accepted_request["requested_by"]},
            {"$inc": {"total_pickups": 1}}
        )
        
        # Notify the NGO about completion
        background_tasks.add_task(
            manager.send_notification,
            accepted_request["requested_by"],
            "pickup_completed",
            "Pickup Completed! ✅",
            f"Thank you for picking up '{listing['title']}'. Together we're reducing food waste!",
            {"listing_id": listing_id}
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
        total_requests = requests_collection.count_documents({
            "listing_id": {"$in": [doc["listing_id"] for doc in listings_collection.find({"posted_by": current_user["user_id"]}, {"listing_id": 1})]}
        })
        
        return {
            "role": "donor",
            "total_listings": total_listings,
            "active_listings": active_listings,
            "completed_pickups": completed_pickups,
            "total_requests": total_requests,
            "impact_score": completed_pickups * 10  # Simple impact calculation
        }
    elif current_user["role"] == "ngo":
        # NGO stats
        total_requests = requests_collection.count_documents({"requested_by": current_user["user_id"]})
        accepted_requests = requests_collection.count_documents({
            "requested_by": current_user["user_id"],
            "status": "accepted"
        })
        completed_pickups = users_collection.find_one({"user_id": current_user["user_id"]}, {"total_pickups": 1})
        completed_pickups = completed_pickups.get("total_pickups", 0) if completed_pickups else 0
        
        return {
            "role": "ngo",
            "total_requests": total_requests,
            "accepted_requests": accepted_requests,
            "completed_pickups": completed_pickups,
            "success_rate": round((accepted_requests / max(total_requests, 1)) * 100, 1)
        }
    elif current_user["role"] == "admin":
        # Admin stats
        total_users = users_collection.count_documents({})
        total_donors = users_collection.count_documents({"role": "donor"})
        total_ngos = users_collection.count_documents({"role": "ngo"})
        total_listings = listings_collection.count_documents({})
        completed_pickups = listings_collection.count_documents({"status": "picked_up"})
        
        return {
            "role": "admin",
            "total_users": total_users,
            "total_donors": total_donors,
            "total_ngos": total_ngos,
            "total_listings": total_listings,
            "completed_pickups": completed_pickups,
            "platform_impact": completed_pickups * 100  # Estimated meals saved
        }

@app.get("/api/notifications")
async def get_notifications(current_user: dict = Depends(verify_token), limit: int = 50):
    notifications = list(notifications_collection.find(
        {"user_id": current_user["user_id"]},
        {"_id": 0}
    ).sort("created_at", DESCENDING).limit(limit))
    
    return {"notifications": notifications}

@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: dict = Depends(verify_token)):
    notifications_collection.update_one(
        {"notification_id": notification_id, "user_id": current_user["user_id"]},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

# Admin endpoints
@app.get("/api/admin/users")
async def get_all_users(current_user: dict = Depends(requires_admin), skip: int = 0, limit: int = 50):
    users = list(users_collection.find(
        {},
        {"password": 0, "_id": 0}
    ).sort("created_at", DESCENDING).skip(skip).limit(limit))
    
    return {"users": users}

@app.post("/api/admin/users/{user_id}/action")
async def admin_user_action(
    user_id: str, 
    action_data: AdminAction, 
    current_user: dict = Depends(requires_admin)
):
    if action_data.action == "approve":
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"is_verified": True}}
        )
        return {"message": "User approved successfully"}
    elif action_data.action == "suspend":
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"is_active": False}}
        )
        return {"message": "User suspended successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

@app.get("/api/admin/analytics")
async def get_platform_analytics(current_user: dict = Depends(requires_admin)):
    # User analytics
    total_users = users_collection.count_documents({})
    new_users_today = users_collection.count_documents({
        "created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()}
    })
    
    # Listing analytics
    total_listings = listings_collection.count_documents({})
    active_listings = listings_collection.count_documents({"status": "available"})
    completed_listings = listings_collection.count_documents({"status": "picked_up"})
    
    # Request analytics
    total_requests = requests_collection.count_documents({})
    accepted_requests = requests_collection.count_documents({"status": "accepted"})
    
    return {
        "user_metrics": {
            "total_users": total_users,
            "new_users_today": new_users_today,
            "donors": users_collection.count_documents({"role": "donor"}),
            "ngos": users_collection.count_documents({"role": "ngo"}),
            "verified_ngos": users_collection.count_documents({"role": "ngo", "is_verified": True})
        },
        "listing_metrics": {
            "total_listings": total_listings,
            "active_listings": active_listings,
            "completed_listings": completed_listings,
            "success_rate": round((completed_listings / max(total_listings, 1)) * 100, 1)
        },
        "request_metrics": {
            "total_requests": total_requests,
            "accepted_requests": accepted_requests,
            "acceptance_rate": round((accepted_requests / max(total_requests, 1)) * 100, 1)
        },
        "impact_metrics": {
            "estimated_meals_saved": completed_listings * 10,
            "estimated_food_saved_kg": completed_listings * 5
        }
    }

# Background task to expire old listings
async def cleanup_expired_listings():
    """Mark expired listings as expired"""
    while True:
        try:
            current_time = datetime.utcnow().isoformat()
            
            result = listings_collection.update_many(
                {
                    "status": "available",
                    "expiry_time": {"$lt": current_time}
                },
                {"$set": {"status": "expired"}}
            )
            
            if result.modified_count > 0:
                print(f"✅ Marked {result.modified_count} listings as expired")
            
            # Sleep for 1 hour
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"⚠️  Error in cleanup task: {e}")
            await asyncio.sleep(300)  # Sleep 5 minutes on error

# Start background tasks
@app.on_event("startup")
async def startup_event():
    # Start the cleanup task
    asyncio.create_task(cleanup_expired_listings())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)