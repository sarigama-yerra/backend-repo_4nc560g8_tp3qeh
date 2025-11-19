"""
Database Schemas for Dalilah

Each Pydantic model represents a MongoDB collection. The collection name
is the lowercase of the class name.

- Opportunity -> "opportunity"
- UserProfile -> "userprofile"
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal
from datetime import datetime

SaudiCity = Literal[
    "Riyadh",
    "Jeddah",
    "Dammam",
    "Khobar",
    "Dhahran",
    "Madinah",
    "Makkah",
    "Tabuk",
    "Abha",
    "Taif",
    "Qassim",
    "Hail",
    "Jazan",
    "Najran",
    "Al Baha",
    "Al Jouf",
    "Al Ahsa",
    "Other"
]

OpportunityCategory = Literal[
    "hackathon",
    "event",
    "course",
    "accelerator",
    "incubator",
    "program"
]

OpportunityMode = Literal["online", "offline", "hybrid"]

class Opportunity(BaseModel):
    """
    Curated professional opportunity in KSA
    Collection: "opportunity"
    """
    title: str = Field(..., description="Opportunity title")
    description: str = Field(..., description="Short description")
    category: OpportunityCategory = Field(..., description="Type of opportunity")
    organization: Optional[str] = Field(None, description="Organizer/Host")
    country: str = Field("Saudi Arabia", description="Country")
    city: Optional[SaudiCity] = Field(None, description="City in KSA")
    mode: OpportunityMode = Field("online", description="Delivery mode")
    is_paid: bool = Field(False, description="Paid vs free")
    price: Optional[float] = Field(None, ge=0, description="Price if paid")
    url: HttpUrl = Field(..., description="Official URL to apply/learn more")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    eligibility: Optional[str] = Field(None, description="Eligibility criteria")
    tags: List[str] = Field(default_factory=list, description="Keywords/tags")
    verified: bool = Field(False, description="Manually verified flag")
    status: Literal["draft", "pending_review", "published"] = Field(
        "pending_review", description="Moderation status"
    )

class UserProfile(BaseModel):
    """
    User profile captured for personalization
    Collection: "userprofile"
    """
    name: str
    email: str
    location: Optional[SaudiCity] = None
    experience_level: Optional[Literal["student", "junior", "mid", "senior", "founder"]] = None
    interests: List[str] = Field(default_factory=list, description="Keywords and categories of interest")
    goals: Optional[str] = None
