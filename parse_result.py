import json
import sys
fname = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\SynAckITPC\Documents\AI\smartcompare\tmp_result.json'
r = json.load(open(fname))
for p in r.get('products', []):
    name = p.get('name', 'Unknown')
    price = p.get('price', {})
    amt = price.get('amount', 'N/A')
    curr = price.get('currency', '')
    retailer = price.get('retailer', 'none')
    method = price.get('source_method', 'unknown')
    estimated = price.get('estimated', False)
    print(f"{name}")
    print(f"  Price: {curr} {amt}")
    print(f"  Retailer: {retailer}")
    print(f"  Method: {method}")
    print(f"  Estimated: {estimated}")
    print()
print(f"Category: {r.get('category_used', '?')}")
print(f"Cost: ${r.get('total_cost', 0):.4f}")
print(f"API calls: {r.get('api_calls', 0)}")
