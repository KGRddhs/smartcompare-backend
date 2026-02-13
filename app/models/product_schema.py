"""
Product Schema - Structured data models for product extraction
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ProductCategory(str, Enum):
    ELECTRONICS = "electronics"
    GROCERY = "grocery"
    BEAUTY = "beauty"
    FASHION = "fashion"
    HOME = "home"
    SPORTS = "sports"
    AUTOMOTIVE = "automotive"
    OTHER = "other"


class PriceInfo(BaseModel):
    """Price information for a specific region/retailer"""
    amount: Optional[float] = None
    currency: str = "BHD"
    retailer: Optional[str] = None
    url: Optional[str] = None
    in_stock: Optional[bool] = None
    last_updated: Optional[str] = None


class RegionalPrices(BaseModel):
    """Prices across GCC regions"""
    bahrain: Optional[PriceInfo] = None
    saudi_arabia: Optional[PriceInfo] = None
    uae: Optional[PriceInfo] = None
    kuwait: Optional[PriceInfo] = None
    qatar: Optional[PriceInfo] = None
    oman: Optional[PriceInfo] = None
    best_price: Optional[PriceInfo] = None
    best_region: Optional[str] = None


class ProductSpecs(BaseModel):
    """Technical specifications"""
    # Common specs
    brand: str
    model: str
    variant: Optional[str] = None  # e.g., "128GB", "Pro Max"
    category: ProductCategory = ProductCategory.OTHER
    
    # Dimensions
    weight: Optional[str] = None
    dimensions: Optional[str] = None
    
    # Electronics specific
    display: Optional[str] = None
    processor: Optional[str] = None
    ram: Optional[str] = None
    storage: Optional[str] = None
    battery: Optional[str] = None
    camera: Optional[str] = None
    os: Optional[str] = None
    connectivity: Optional[List[str]] = None
    
    # Grocery specific
    size: Optional[str] = None
    ingredients: Optional[List[str]] = None
    nutrition: Optional[Dict[str, str]] = None
    expiry: Optional[str] = None
    
    # Generic specs (key-value for flexibility)
    additional_specs: Optional[Dict[str, str]] = None


class ReviewSummary(BaseModel):
    """Aggregated review data"""
    average_rating: Optional[float] = Field(None, ge=0, le=5)
    total_reviews: Optional[int] = None
    rating_breakdown: Optional[Dict[str, int]] = None  # {"5": 100, "4": 50, ...}

    # Sentiment analysis
    positive_percentage: Optional[float] = None
    common_praises: Optional[List[str]] = None  # Simple string list (backward compat)
    common_complaints: Optional[List[str]] = None  # Simple string list (backward compat)

    # Source breakdown
    sources: Optional[List[Dict[str, Any]]] = None  # [{"source": "Amazon", "rating": 4.5, "count": 1000}]

    # Enhanced review fields
    rating_distribution: Optional[Dict[str, float]] = None  # {"5_star": 45.0, "4_star": 25.0, ...}
    category_scores: Optional[Dict[str, float]] = None  # {"camera": 9.0, "battery": 7.5, ...}
    source_ratings: Optional[List[Dict[str, Any]]] = None  # [{source, rating, review_count}]
    detailed_praises: Optional[List[Dict[str, Any]]] = None  # [{text, frequency, quote}]
    detailed_complaints: Optional[List[Dict[str, Any]]] = None  # [{text, frequency, quote}]
    user_quotes: Optional[List[Dict[str, Any]]] = None  # [{text, sentiment, source, aspect}]
    summary: Optional[str] = None  # 2-3 sentence opinionated summary
    verified_rating: Optional[Dict[str, Any]] = None  # {rating, review_count, source, verified}


class ProsCons(BaseModel):
    """Pros and cons analysis"""
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)


class StructuredProduct(BaseModel):
    """Complete structured product data"""
    # Identification
    id: Optional[str] = None
    query: str  # Original search query
    
    # Basic info
    brand: str
    name: str
    full_name: str  # "Apple iPhone 15 Pro 256GB"
    variant: Optional[str] = None
    category: ProductCategory = ProductCategory.OTHER
    
    # Detailed data
    specs: Optional[ProductSpecs] = None
    prices: Optional[RegionalPrices] = None
    reviews: Optional[ReviewSummary] = None
    pros_cons: Optional[ProsCons] = None
    
    # Metadata
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    data_freshness: str = "unknown"  # "live", "cached", "partial"
    confidence: float = 0.0  # 0-1 confidence in data accuracy
    
    # Cache info
    cached_at: Optional[str] = None
    cache_ttl: Optional[int] = None  # seconds


class ComparisonResult(BaseModel):
    """Structured comparison between products"""
    products: List[StructuredProduct]
    
    # Winner analysis
    winner_index: int
    winner_reason: str
    
    # Detailed comparison
    price_comparison: Dict[str, Any]
    specs_comparison: Dict[str, Any]
    value_score: List[float]  # Value for money score per product
    
    # Recommendations
    recommendation: str
    best_for: Dict[str, int]  # {"budget": 0, "performance": 1, "camera": 0}
    
    # Key differences
    key_differences: List[str]
    
    # Metadata
    comparison_date: str
    total_cost: float
    data_sources: List[str]


class TextComparisonRequest(BaseModel):
    """Request for text-based comparison"""
    query: str  # "iPhone 15 vs S24" or "compare Nido vs Almarai milk"
    region: str = "bahrain"
    include_specs: bool = True
    include_reviews: bool = True
    include_pros_cons: bool = True
