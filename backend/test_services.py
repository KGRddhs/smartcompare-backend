"""
Test Script - Verify all services are working
Run with: poetry run python test_services.py
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_openai():
    """Test OpenAI connection"""
    print("\n🔍 Testing OpenAI...")
    
    from openai import AsyncOpenAI
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.startswith("sk-"):
        print("   ❌ OPENAI_API_KEY not set or invalid")
        return False
    
    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
            max_tokens=10
        )
        result = response.choices[0].message.content
        print(f"   ✅ OpenAI working! Response: {result}")
        return True
    except Exception as e:
        print(f"   ❌ OpenAI error: {e}")
        return False


async def test_serper():
    """Test Serper connection"""
    print("\n🔍 Testing Serper...")
    
    import httpx
    
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("   ❌ SERPER_API_KEY not set")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json"
                },
                json={"q": "Nido milk powder price Bahrain", "num": 3}
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("organic", [])
                print(f"   ✅ Serper working! Got {len(results)} search results")
                if results:
                    print(f"   📝 First result: {results[0].get('title', 'N/A')[:50]}...")
                return True
            else:
                print(f"   ❌ Serper error: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"   ❌ Serper error: {e}")
        return False


async def test_redis():
    """Test Redis/Upstash connection"""
    print("\n🔍 Testing Redis (Upstash)...")
    
    redis_url = os.getenv("UPSTASH_REDIS_URL")
    redis_token = os.getenv("UPSTASH_REDIS_TOKEN")
    
    if not redis_url or not redis_token:
        print("   ❌ UPSTASH_REDIS_URL or UPSTASH_REDIS_TOKEN not set")
        return False
    
    try:
        import redis
        
        # Convert REST URL to Redis URL
        if redis_url.startswith("https://"):
            host = redis_url.replace("https://", "").rstrip("/")
            connection_url = f"rediss://default:{redis_token}@{host}:6379"
        else:
            connection_url = redis_url
        
        client = redis.from_url(connection_url, decode_responses=True)
        
        # Test set/get
        client.setex("test_key", 60, "test_value")
        value = client.get("test_key")
        client.delete("test_key")
        
        if value == "test_value":
            print("   ✅ Redis working! Set/Get/Delete successful")
            return True
        else:
            print("   ❌ Redis read/write mismatch")
            return False
    except Exception as e:
        print(f"   ❌ Redis error: {e}")
        return False


async def test_supabase():
    """Test Supabase connection"""
    print("\n🔍 Testing Supabase...")
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("   ❌ SUPABASE_URL or SUPABASE_ANON_KEY not set")
        return False
    
    try:
        from supabase import create_client
        
        client = create_client(url, key)
        
        # Just try to access the client (actual queries need auth)
        print(f"   ✅ Supabase client created for {url[:30]}...")
        return True
    except Exception as e:
        print(f"   ❌ Supabase error: {e}")
        return False


async def test_quick_comparison():
    """Test the quick comparison feature (no images)"""
    print("\n🔍 Testing Quick Comparison (text only)...")
    
    try:
        from app.services.comparison_service import quick_compare
        
        product1 = {
            "brand": "Nido",
            "name": "Full Cream Milk Powder",
            "size": "2.5kg"
        }
        product2 = {
            "brand": "Almarai",
            "name": "Milk Powder",
            "size": "2.5kg"
        }
        
        print("   ⏳ Running comparison (this may take 10-20 seconds)...")
        result = await quick_compare(product1, product2, "Bahrain")
        
        if result.get("success"):
            print(f"   ✅ Comparison successful!")
            print(f"   🏆 Winner: Product {result['winner_index'] + 1}")
            print(f"   💰 API Cost: ${result['total_cost']:.6f}")
            print(f"   📊 Data source: {result['data_freshness']}")
            
            for product in result["products"]:
                print(f"   - {product['brand']} {product['name']}: {product.get('price', 'N/A')} {product.get('currency', '')}")
            
            return True
        else:
            print(f"   ❌ Comparison failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"   ❌ Comparison error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("=" * 50)
    print("SmartCompare Service Tests")
    print("=" * 50)
    
    results = {}
    
    # Test each service
    results["OpenAI"] = await test_openai()
    results["Serper"] = await test_serper()
    results["Redis"] = await test_redis()
    results["Supabase"] = await test_supabase()
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    print("=" * 50)
    
    all_passed = True
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {service}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All basic services working!")
        print("\nWould you like to run a full comparison test? (uses ~$0.002 in API credits)")
        print("Run: poetry run python test_services.py --full")
    else:
        print("\n⚠️  Some services failed. Fix the issues above before continuing.")
    
    # Check for --full flag
    import sys
    if "--full" in sys.argv and all_passed:
        print("\n" + "=" * 50)
        print("Running Full Comparison Test")
        print("=" * 50)
        await test_quick_comparison()


if __name__ == "__main__":
    asyncio.run(main())
