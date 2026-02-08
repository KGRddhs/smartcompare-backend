"""
Test Client - Test the SmartCompare API endpoints
Run with: poetry run python test_client.py
"""
import asyncio
import httpx
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"


async def test_health():
    """Test health endpoints"""
    print("\n🔍 Testing Health Endpoints...")
    
    async with httpx.AsyncClient() as client:
        # Basic health
        response = await client.get(f"{BASE_URL}/health")
        print(f"   /health: {response.status_code} - {response.json()}")
        
        # Services health
        response = await client.get(f"{BASE_URL}/api/v1/health/services")
        print(f"   /api/v1/health/services: {response.status_code}")
        data = response.json()
        for service, status in data.get("services", {}).items():
            print(f"      - {service}: {status.get('status', 'unknown')}")


async def test_rate_limit():
    """Test rate limit status"""
    print("\n🔍 Testing Rate Limit...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/rate-limit/status")
        data = response.json()
        print(f"   Current usage: {data.get('current_usage', 0)}")
        print(f"   Daily limit: {data.get('daily_limit', 'Unlimited')}")
        print(f"   Remaining: {data.get('remaining', 'Unlimited')}")


async def test_quick_compare():
    """Test quick comparison endpoint"""
    print("\n🔍 Testing Quick Comparison...")
    
    payload = {
        "products": [
            {"brand": "Nido", "name": "Full Cream Milk Powder", "size": "2.5kg"},
            {"brand": "Almarai", "name": "Milk Powder", "size": "2.5kg"}
        ],
        "country": "Bahrain"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("   ⏳ Running comparison (10-20 seconds)...")
        response = await client.post(
            f"{BASE_URL}/api/v1/compare/quick",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success!")
            print(f"   🏆 Winner: Product {data.get('winner_index', 0) + 1}")
            print(f"   💰 Cost: ${data.get('total_cost', 0):.6f}")
            print(f"   📊 Source: {data.get('data_freshness', 'unknown')}")
            
            for i, product in enumerate(data.get("products", [])):
                print(f"   Product {i+1}: {product.get('brand')} {product.get('name')} - {product.get('price', 'N/A')} {product.get('currency', '')}")
        
        elif response.status_code == 429:
            print(f"   ⚠️ Rate limit exceeded: {response.json()}")
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")


async def test_image_compare(image_paths: list):
    """Test image upload comparison"""
    print("\n🔍 Testing Image Comparison...")
    
    if not image_paths:
        print("   ⚠️ No images provided. Usage: poetry run python test_client.py --images path1.jpg path2.jpg")
        return
    
    # Validate files exist
    for path in image_paths:
        if not Path(path).exists():
            print(f"   ❌ File not found: {path}")
            return
    
    # Prepare multipart form data
    files = []
    for path in image_paths:
        file_path = Path(path)
        content_type = "image/jpeg" if file_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"
        files.append(
            ("images", (file_path.name, open(path, "rb"), content_type))
        )
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"   ⏳ Uploading {len(image_paths)} images and comparing (30-60 seconds)...")
            response = await client.post(
                f"{BASE_URL}/api/v1/compare",
                files=files,
                params={"country": "Bahrain"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success!")
                print(f"   🏆 Winner: Product {data.get('winner_index', 0) + 1}")
                print(f"   💰 Cost: ${data.get('total_cost', 0):.6f}")
                print(f"   📊 Source: {data.get('data_freshness', 'unknown')}")
                
                print("\n   📦 Products identified:")
                for i, product in enumerate(data.get("products", [])):
                    print(f"      {i+1}. {product.get('brand', 'Unknown')} {product.get('name', 'Unknown')}")
                    print(f"         Size: {product.get('size', 'N/A')}")
                    print(f"         Price: {product.get('price', 'N/A')} {product.get('currency', '')}")
                    print(f"         Source: {product.get('source', 'unknown')}")
                
                print(f"\n   💡 Recommendation: {data.get('recommendation', 'N/A')[:200]}...")
                
                print("\n   📋 Key Differences:")
                for diff in data.get("key_differences", [])[:5]:
                    print(f"      - {diff}")
            
            elif response.status_code == 429:
                print(f"   ⚠️ Rate limit exceeded: {response.json()}")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
    
    finally:
        # Close file handles
        for _, file_tuple in files:
            file_tuple[1].close()


async def test_history():
    """Test comparison history"""
    print("\n🔍 Testing Comparison History...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/comparisons/history")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Total comparisons: {data.get('total', 0)}")
            
            comparisons = data.get("comparisons", [])
            if comparisons:
                print(f"   Recent comparisons:")
                for comp in comparisons[:3]:
                    print(f"      - ID: {comp.get('id', 'N/A')[:8]}...")
                    print(f"        Created: {comp.get('created_at', 'N/A')}")
                    print(f"        Products: {len(comp.get('products', []))}")
            else:
                print("   No comparisons yet.")
        else:
            print(f"   ❌ Failed: {response.status_code}")


async def main():
    print("=" * 50)
    print("SmartCompare API Test Client")
    print("=" * 50)
    print(f"Target: {BASE_URL}")
    
    # Parse command line arguments
    args = sys.argv[1:]
    
    if "--images" in args:
        # Image comparison mode
        image_index = args.index("--images") + 1
        image_paths = args[image_index:]
        await test_image_compare(image_paths)
    
    elif "--quick" in args:
        # Quick comparison mode
        await test_quick_compare()
    
    elif "--history" in args:
        # History mode
        await test_history()
    
    else:
        # Full test suite
        await test_health()
        await test_rate_limit()
        
        print("\n" + "=" * 50)
        print("Quick Test Commands:")
        print("=" * 50)
        print("  Test quick compare:")
        print("    poetry run python test_client.py --quick")
        print("")
        print("  Test with images:")
        print("    poetry run python test_client.py --images product1.jpg product2.jpg")
        print("")
        print("  View history:")
        print("    poetry run python test_client.py --history")


if __name__ == "__main__":
    asyncio.run(main())
