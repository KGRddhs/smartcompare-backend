import sys, json
r = json.load(sys.stdin)
for p in r.get('products', []):
    name = p.get('name', 'unknown')
    price = p.get('price', {})
    amt = price.get('amount', 'N/A')
    cur = price.get('currency', '?')
    method = price.get('source_method', 'unknown')
    retailer = price.get('retailer', 'unknown')
    est = price.get('estimated', False)
    print(f'{name}: {cur} {amt} | method={method} | retailer={retailer} | estimated={est}')
print(f"Total cost: ${r.get('total_cost', '?')}")
