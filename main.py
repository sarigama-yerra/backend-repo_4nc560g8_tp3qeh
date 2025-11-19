import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Opportunity, UserProfile

app = FastAPI(title="Dalilah API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Dalilah backend is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response

# ---------------------------
# Opportunities CRUD (reviewed curation flow)
# ---------------------------

@app.post("/opportunities", response_model=dict)
def create_opportunity(opportunity: Opportunity):
    # New entries are pending review by default unless already verified
    data = opportunity.model_dump()
    if data.get("verified"):
        data["status"] = "published"
    else:
        data["status"] = "pending_review"

    inserted_id = create_document("opportunity", data)
    return {"id": inserted_id}

@app.get("/opportunities", response_model=List[dict])
def list_opportunities(category: Optional[str] = None, city: Optional[str] = None, published_only: bool = True, q: Optional[str] = None, limit: int = 50):
    filter_query = {}
    if published_only:
        filter_query["status"] = "published"
    if category:
        filter_query["category"] = category
    if city:
        filter_query["city"] = city
    if q:
        filter_query["$text"] = {"$search": q}

    docs = get_documents("opportunity", filter_query, limit)
    # Convert ObjectId to string for frontend safety
    for d in docs:
        if isinstance(d.get("_id"), ObjectId):
            d["id"] = str(d.pop("_id"))
    return docs

@app.post("/opportunities/{id}/verify")
def verify_opportunity(id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        result = db["opportunity"].update_one({"_id": ObjectId(id)}, {"$set": {"verified": True, "status": "published"}})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        return {"ok": True}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

# ---------------------------
# User profiles & recommendations
# ---------------------------

@app.post("/profiles", response_model=dict)
def create_profile(profile: UserProfile):
    inserted_id = create_document("userprofile", profile)
    return {"id": inserted_id}

@app.get("/recommendations/{email}")
def get_recommendations(email: str, limit: int = 20):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # Fetch user profile
    profiles = get_documents("userprofile", {"email": email}, limit=1)
    if not profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = profiles[0]

    interests = set((profile.get("interests") or []))
    location = profile.get("location")

    # Build a relevance filter
    match_stage = {"status": "published"}
    if location:
        match_stage["$or"] = [
            {"city": location},
            {"mode": {"$in": ["online", "hybrid"]}}
        ]

    pipeline = [
        {"$match": match_stage},
        {"$addFields": {
            "interest_score": {"$size": {"$setIntersection": ["$tags", list(interests)]}},
            "recency_score": {"$cond": [
                {"$gt": ["$application_deadline", None]},
                {"$divide": [
                    {"$subtract": ["$application_deadline", 0]},
                    1000 * 60 * 60 * 24
                ]},
                0
            ]}
        }},
        {"$addFields": {"total_score": {"$add": ["$interest_score", {"$divide": ["$recency_score", 1000]}]}}},
        {"$sort": {"total_score": -1}},
        {"$limit": limit}
    ]

    try:
        docs = list(db["opportunity"].aggregate(pipeline))
        for d in docs:
            if isinstance(d.get("_id"), ObjectId):
                d["id"] = str(d.pop("_id"))
        return {"items": docs}
    except Exception as e:
        # Fallback: simple filter if aggregation not supported in env
        filter_query = {"status": "published"}
        docs = get_documents("opportunity", filter_query, limit)
        for d in docs:
            if isinstance(d.get("_id"), ObjectId):
                d["id"] = str(d.pop("_id"))
        return {"items": docs, "note": "Fallback recommendations"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
