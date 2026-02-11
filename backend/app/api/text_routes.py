"""
Text Comparison Routes - Natural language product comparison
Supports: lite, full, and v3 (production) modes
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/text", tags=["text-comparison"])


class TextCompareRequest(BaseModel):
    query: str
    region: str = "bahrain"
    mode: str = "v3"  # "lite", "full", or "v3"


@router.get("/compare")
async def compare_text_get(
    q: str = Query(..., description="Comparison query, e.g., 'iPhone 15 vs Galaxy S24'"),
    region: str = Query("bahrain", description="Region for pricing"),
    mode: str = Query("v3", description="Mode: 'lite' (~$0.004), 'full' (~$0.01), 'v3' (~$0.006, recommended)")
):
    """
    Compare products using natural language.
    
    **Modes:**
    - `v3` (recommended): Complete data with validation (~$0.006, 10-15s)
    - `lite`: Fast & cheap (~$0.004, 5-10s)
    - `full`: Most detailed (~$0.01, 20-30s)
    
    **v3 Features:**
    - Guaranteed complete responses
    - All fields validated
    - Database caching (faster repeat searches)
    - Fallback strategies for missing data
    
    **Examples:**
    - iPhone 15 vs Galaxy S24
    - MacBook Air vs Dell XPS 13
    - Xbox Series X vs PlayStation 5
    """
    return await _do_comparison(q, region, mode)


@router.post("/compare")
async def compare_text_post(request: TextCompareRequest):
    """POST version for complex queries."""
    return await _do_comparison(request.query, request.region, request.mode)


async def _do_comparison(query: str, region: str, mode: str):
    """Execute comparison in specified mode."""
    
    try:
        if mode == "v3":
            from app.services.comparison_service_v3 import compare_v3
            result = await compare_v3(query, region)
        elif mode == "lite":
            from app.services.lite_comparison_service import compare_text_lite
            result = await compare_text_lite(query, region)
        else:  # full
            from app.services.structured_comparison_service import StructuredComparisonService
            service = StructuredComparisonService()
            result = await service.compare_from_text(query, region)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Comparison failed")
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parse")
async def parse_query(q: str = Query(..., description="Query to parse")):
    """Debug: Parse a query without doing full comparison."""
    from app.services.extraction_service import parse_product_query
    
    result = await parse_product_query(q)
    return {"query": q, "parsed": result}


@router.get("/quick")
async def quick_compare(
    p1: str = Query(..., description="First product"),
    p2: str = Query(..., description="Second product"),
    region: str = Query("bahrain", description="Region")
):
    """
    Quick comparison with product names directly.
    Uses v3 mode for best results.
    
    Example: /quick?p1=iPhone 15&p2=Galaxy S24
    """
    query = f"{p1} vs {p2}"
    from app.services.comparison_service_v3 import compare_v3
    
    result = await compare_v3(query, region)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/costs")
async def get_cost_info():
    """Get information about API costs per comparison mode."""
    return {
        "modes": {
            "v3": {
                "cost_per_comparison": "$0.005-0.007",
                "time": "10-15 seconds",
                "features": [
                    "✅ Guaranteed complete data",
                    "✅ All fields validated",
                    "✅ Database caching",
                    "✅ Fallback strategies",
                    "✅ Price from multiple sources",
                    "✅ Specs validation",
                    "✅ Auto-generated pros/cons"
                ],
                "recommended": True
            },
            "lite": {
                "cost_per_comparison": "$0.003-0.004",
                "time": "5-10 seconds",
                "features": [
                    "Basic specs extraction",
                    "Price comparison",
                    "Simple pros/cons",
                    "Winner recommendation"
                ],
                "recommended": False
            },
            "full": {
                "cost_per_comparison": "$0.008-0.012",
                "time": "20-30 seconds",
                "features": [
                    "Detailed specs extraction",
                    "Multi-region pricing",
                    "Review aggregation",
                    "Detailed pros/cons",
                    "Value scoring"
                ],
                "recommended": False
            }
        },
        "pricing": {
            "serper": "$0.001 per search",
            "openai_gpt4o_mini": {
                "input": "$0.15 per 1M tokens",
                "output": "$0.60 per 1M tokens"
            }
        },
        "caching_benefit": "Repeat searches cost $0.001 (95% savings)"
    }


@router.get("/stats")
async def get_stats():
    """Get search statistics (requires database)."""
    try:
        from app.services.comparison_service_v3 import get_supabase
        
        supabase = get_supabase()
        if not supabase:
            return {"error": "Database not configured"}
        
        # Total searches
        total = supabase.table("search_logs").select("id", count="exact").execute()
        
        # Today's searches
        from datetime import datetime
        today = datetime.utcnow().strftime("%Y-%m-%d")
        today_result = supabase.table("search_logs").select("id", count="exact").gte("created_at", today).execute()
        
        # Success rate
        success = supabase.table("search_logs").select("id", count="exact").eq("success", True).execute()
        
        # Total cost
        costs = supabase.table("search_logs").select("cost").execute()
        total_cost = sum(c["cost"] or 0 for c in costs.data) if costs.data else 0
        
        # Product count
        products = supabase.table("products").select("id", count="exact").execute()
        
        return {
            "total_searches": total.count if total else 0,
            "today_searches": today_result.count if today_result else 0,
            "success_rate": f"{(success.count / total.count * 100):.1f}%" if total and total.count > 0 else "N/A",
            "total_cost": f"${total_cost:.2f}",
            "products_cached": products.count if products else 0
        }
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": str(e)}
