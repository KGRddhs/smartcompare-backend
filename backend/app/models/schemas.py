"""
Pydantic Schemas - Request and Response models for the API
"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# Product Schemas
# ============================================

class ProductBase(BaseModel):
    """Base product information"""
    brand: str = Field(..., description="Product brand name")
    name: str = Field(..., description="Product name")
    size: Optional[str] = Field(None, description="Product size/weight/volume")


class ProductIdentified(ProductBase):
    """Product identified from image"""
    visible_price: Optional[str] = Field(None, description="Price visible on product/shelf")


class ProductWithPrice(ProductBase):
    """Product with price data"""
    price: Optional[float] = Field(None, description="Product price")
    currency: str = Field("BHD", description="Currency code")
    source: str = Field(..., description="Price source: live, cached, or estimated")
    confidence: Optional[str] = Field(None, description="Price confidence level")
    retailer: Optional[str] = Field(None, description="Retailer where price was found")
    note: Optional[str] = Field(None, description="Additional notes")


# ============================================
# Comparison Schemas
# ============================================

class ComparisonRequest(BaseModel):
    """Request model for quick comparison (without images)"""
    products: List[ProductBase] = Field(..., min_length=2, max_length=4)
    country: str = Field("Bahrain", description="Country for price search")


class ComparisonResponse(BaseModel):
    """Response model for product comparison"""
    success: bool
    products: List[ProductWithPrice] = Field(default_factory=list)
    winner_index: int = Field(0, description="Index of winning product (0-based)")
    recommendation: str = Field("", description="Recommendation text")
    key_differences: List[str] = Field(default_factory=list)
    total_cost: float = Field(0.0, description="Total API cost in USD")
    data_freshness: str = Field("unknown", description="Data source: live, cached, mixed, or estimated")
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")


class ComparisonError(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    details: Optional[Any] = None


# ============================================
# User & Subscription Schemas
# ============================================

class UserBase(BaseModel):
    """Base user information"""
    email: str


class UserCreate(UserBase):
    """User creation request"""
    password: str


class UserResponse(UserBase):
    """User response (no password)"""
    id: str
    subscription_tier: str = "free"
    created_at: datetime


class SubscriptionStatus(BaseModel):
    """User's subscription status"""
    user_id: str
    email: str
    subscription_tier: str
    daily_usage: int
    daily_limit: Optional[int] = Field(None, description="None for premium users")
    remaining_comparisons: Optional[int] = None


# ============================================
# Rate Limiting Schemas
# ============================================

class RateLimitStatus(BaseModel):
    """Rate limit status response"""
    allowed: bool
    current_usage: int
    daily_limit: Optional[int]
    remaining: Optional[int]


class RateLimitError(BaseModel):
    """Rate limit exceeded error"""
    error: str = "Daily limit reached"
    limit: int
    current: int
    message: str = "Upgrade to Premium for unlimited comparisons"


# ============================================
# Cost Tracking Schemas
# ============================================

class CostStatus(BaseModel):
    """Monthly cost status"""
    allowed: bool
    current_spend: float
    budget: float
    remaining: float
    percentage_used: float


# ============================================
# Health Check Schemas
# ============================================

class ServiceHealth(BaseModel):
    """Individual service health"""
    status: str
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str = "1.0.0"
    services: dict[str, ServiceHealth]


# ============================================
# Comparison History Schemas
# ============================================

class ComparisonHistoryItem(BaseModel):
    """Single comparison history item"""
    id: str
    products: List[ProductWithPrice]
    winner_index: int
    recommendation: str
    data_source: str
    total_cost: float
    created_at: datetime


class ComparisonHistoryResponse(BaseModel):
    """Comparison history list response"""
    comparisons: List[ComparisonHistoryItem]
    total: int
    page: int = 1
    per_page: int = 20
