import json, sys

with open(sys.argv[1]) as f:
    r = json.load(f)

for i, p in enumerate(r.get('products', [])):
    name = p.get('name', 'Unknown')
    price = p.get('price', {})
    print(f"Product {i+1}: {name}")
    print(f"  Price: {price.get('amount')} {price.get('currency')}")
    print(f"  Retailer: {price.get('retailer')}")
    print(f"  source_method: {price.get('source_method')}")
    print(f"  estimated: {price.get('estimated')}")
    print(f"  url: {str(price.get('url', 'N/A'))[:80]}")
    print()

meta = r.get('metadata', {})
print(f"API calls: {meta.get('api_calls')}")
print(f"Total cost: ${meta.get('total_cost', 0):.4f}")
print(f"Category: {r.get('category_used')}")
print(f"price_method_mismatch: {r.get('price_method_mismatch')}")

# Check for scoring/overview
if 'overview' in r:
    ov = r['overview']
    w = ov.get('winner', {})
    print(f"\nWinner: {w.get('name')} ({w.get('declaration', '')})")
    for j, op in enumerate(ov.get('products', [])):
        print(f"  Product {j+1}: badge={op.get('value_badge')}, best_for={op.get('best_for')}")

# Check confidence
conf = r.get('overview', {}).get('confidence', r.get('scoring', {}).get('confidence', {}))
if conf:
    print(f"\nConfidence: price={conf.get('price')}, rating={conf.get('rating')}, specs={conf.get('specs')}, overall={conf.get('overall')}")
