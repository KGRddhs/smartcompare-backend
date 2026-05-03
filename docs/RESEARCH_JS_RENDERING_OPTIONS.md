# JavaScript Rendering Options for Luxury Brand Price Scraping

## Context
SmartCompare needs to extract prices from luxury brand official websites (Louis Vuitton, Hermes, Chanel, etc.) that use JavaScript rendering. Current approach using curl_cffi gets URLs from Serper but can't extract prices from JS-rendered pages.

**Requirements:**
- 50 luxury comparisons/day = ~100 product pages/day (2 products per comparison)
- Current cost: $0.010-0.015/comparison
- Target: stay under $0.02/comparison
- Cost budget for scraping: ~$0.003-0.008/comparison ($0.0015-0.004 per product page)

## Options Research

### 1. Self-Hosted Playwright/Puppeteer (Railway Docker)

**How it works:**
- Install Playwright or Puppeteer in Railway container
- Launch headless Chromium on-demand
- Navigate to URL, wait for JS, extract HTML/JSON-LD

**RAM/CPU Requirements:**
- Chromium needs ~200-300MB RAM per instance
- Single instance can handle sequential requests
- Railway starter: 512MB RAM, 1 vCPU (would work for 1-2 concurrent browsers)
- Railway Pro: 2GB RAM, 2 vCPU (could handle 4-6 concurrent)

**Railway Compatibility:**
- ✅ Yes, Docker supports Playwright
- Need to add to Dockerfile: `playwright install chromium` + dependencies
- Railway auto-scales but cold starts = slow first request

**Latency:**
- Cold start: 3-5s (browser launch)
- Warm instance: 2-4s per page
- Can keep browser warm between requests

**Cost:**
- Zero per-request cost
- Just Railway compute: $0.000231/GB-hour + $0.000463/vCPU-hour
- Estimate: +$5-10/month for occasional luxury scraping (~100 pages/day)
- Per comparison: ~$0.0017 (assuming 100 comparisons/day)

**Pros:**
- No external API dependency
- Full control over browser behavior
- Can implement sophisticated waiting logic
- Works with curl_cffi fallback pattern

**Cons:**
- Adds complexity to deployment
- Railway cold starts = latency spikes
- Need to manage browser lifecycle
- May struggle with anti-bot detection (rotating proxies needed)

**Libraries:**
- `playwright` (Microsoft, most modern)
- `puppeteer` (Google, lighter)
- `selenium` (older, heavier)

### 2. Browserless.io

**How it works:**
- Managed headless Chrome API
- POST URL to API, get rendered HTML/screenshot/PDF
- Supports Puppeteer/Playwright scripts via API

**Pricing (as of 2024-2025, verify 2026):**
- Free tier: None for cloud
- Starter: $99/month for 10,000 sessions
- Pro: $249/month for 30,000 sessions
- Enterprise: Custom

**Per-request cost:**
- Starter: $0.0099/session (10k sessions)
- Pro: $0.0083/session (30k sessions)
- 100 pages/day = 3,000/month = $30-$25/month

**Per comparison cost:** ~$0.010 (2 pages @ $0.005 each)

**Pros:**
- No infrastructure management
- Built-in anti-bot evasion
- Reliable uptime
- Supports custom Puppeteer scripts

**Cons:**
- Expensive for this use case (~$0.010/comparison just for scraping)
- DOUBLES current comparison cost
- Overkill for simple price extraction

### 3. ScrapingBee

**How it works:**
- Web scraping API with JS rendering
- Send URL + options, get HTML
- Built-in proxy rotation + anti-bot

**Pricing (as of 2024-2025, verify 2026):**
- Freelance: $49/month for 150,000 API credits
- Startup: $99/month for 350,000 credits
- Business: $249/month for 1,000,000 credits

**Credit cost per request:**
- JS rendering: 5 credits
- Premium proxy: +10 credits (luxury sites likely need this)
- Total: ~15 credits per luxury page

**Per-request cost:**
- Freelance: 150k credits = 10k JS requests = $0.0049/request
- Startup: 350k credits = 23k JS requests = $0.0042/request
- 100 pages/day with premium proxy = 45k credits/month = $13-15/month on Startup plan

**Per comparison cost:** ~$0.005 (2 pages @ $0.0025 each)

**Pros:**
- Simple REST API
- Built-in anti-bot + proxy rotation
- Good for luxury sites (handles Cloudflare, etc.)
- Reasonable pricing for this volume

**Cons:**
- Premium proxy credits add up
- May need Business plan if scaling

### 4. ZenRows

**How it works:**
- Similar to ScrapingBee
- JS rendering + proxy + anti-bot
- Focuses on bypassing Cloudflare/DataDome

**Pricing (as of 2024-2025, verify 2026):**
- Startup: $49/month for 250,000 API credits
- Growth: $149/month for 1,000,000 credits
- Pro: $349/month for 3,000,000 credits

**Credit cost per request:**
- JS rendering: 10 credits
- Premium proxy: +25 credits (auto-enabled for hard sites)
- Total: ~35 credits per luxury page (with anti-bot)

**Per-request cost:**
- Startup: 250k credits = 7k JS requests = $0.007/request
- Growth: 1M credits = 28k JS requests = $0.0053/request
- 100 pages/day = 105k credits/month = $21-31/month

**Per comparison cost:** ~$0.007-0.010 (2 pages)

**Pros:**
- Strong anti-bot capabilities
- Good for Cloudflare-protected sites
- Generous credit allocations

**Cons:**
- More expensive than ScrapingBee
- Credit system can be confusing

### 5. Bright Data Scraping Browser

**How it works:**
- Enterprise-grade scraping infrastructure
- Residential/datacenter proxies + browser automation
- Most robust anti-bot evasion

**Pricing (as of 2024-2025, verify 2026):**
- Pay-as-you-go: $3/1,000 requests (JS rendering)
- Monthly plans: Custom pricing
- Includes proxy bandwidth

**Per-request cost:**
- $0.003 per request minimum
- 100 pages/day = 3,000/month = $9/month base

**Per comparison cost:** ~$0.006 (2 pages @ $0.003 each)

**Pros:**
- Best-in-class anti-bot
- Reliable for enterprise use
- Flexible proxy options

**Cons:**
- Enterprise-focused (overkill)
- Complex pricing
- Minimum commitment may be high

### 6. Crawlee + Playwright (Self-Hosted)

**How it works:**
- Crawlee = open-source framework from Apify
- Handles browser pooling, retries, storage
- Deploy on Railway same as option #1

**Cost:**
- Same as self-hosted Playwright (option #1)
- ~$0.0017/comparison

**Pros:**
- Production-ready framework
- Handles common patterns (queues, retries, rate limiting)
- Free + open source
- Works on Railway

**Cons:**
- More complex than raw Playwright
- Adds dependency weight
- Still needs proxy for anti-bot

### 7. Microlink API

**How it works:**
- Lightweight meta extraction service
- GET request with URL, returns metadata/screenshot/HTML
- JS rendering available

**Pricing (as of 2024-2025, verify 2026):**
- Free: 50 requests/day
- Pro: $9.95/month for 10,000 requests
- Team: $49/month for 100,000 requests

**Per-request cost:**
- Pro: $0.001/request
- Team: $0.00049/request
- 100 pages/day = 3,000/month = $3-5/month

**Per comparison cost:** ~$0.001 (2 pages @ $0.0005 each)

**Pros:**
- Very affordable
- Simple API
- Fast response times
- Free tier for testing

**Cons:**
- Limited anti-bot capabilities
- May not work for heavily protected luxury sites
- Best for basic JS rendering, not sophisticated scraping

## Cost Comparison Table

| Solution | Setup Cost | Monthly Cost (100 pages/day) | Cost per Comparison | Total Comparison Cost | Anti-Bot Strength | Deployment Complexity |
|----------|-----------|------------------------------|---------------------|------------------------|-------------------|----------------------|
| **Self-hosted Playwright** | Medium | $5-10 | $0.0017 | $0.0117-0.0167 | Low (needs proxy) | High |
| **Browserless.io** | Low | $25-30 | $0.010 | $0.020-0.025 | Medium | Low |
| **ScrapingBee** | Low | $13-15 | $0.005 | $0.015-0.020 | High | Low |
| **ZenRows** | Low | $21-31 | $0.007-0.010 | $0.017-0.025 | Very High | Low |
| **Bright Data** | Low | $9+ | $0.006 | $0.016-0.021 | Very High | Low |
| **Crawlee + Playwright** | High | $5-10 | $0.0017 | $0.0117-0.0167 | Low (needs proxy) | Very High |
| **Microlink API** | Low | $3-5 | $0.001 | $0.011-0.016 | Low | Low |

**Assumptions:**
- Current comparison cost: $0.010-0.015
- Target: <$0.02/comparison
- 50 luxury comparisons/day (100 product pages)

## Recommendation Matrix

### Best Cost Efficiency: Microlink API
- **Total cost:** $0.011-0.016/comparison ✅ Under budget
- **Monthly:** $3-5
- **Risk:** May not work for heavily protected sites (Hermes, Louis Vuitton)
- **Use case:** Try first for sites with basic JS rendering

### Best Balance: Self-hosted Playwright + Proxy Service
- **Total cost:** $0.012-0.017/comparison ✅ Near budget
- **Monthly:** $10-15 (Railway + proxy)
- **Risk:** Deployment complexity, need proxy rotation
- **Use case:** Production solution if Microlink fails

### Best for Protected Sites: ScrapingBee
- **Total cost:** $0.015-0.020/comparison ⚠️ At budget limit
- **Monthly:** $13-15
- **Risk:** Cost scales with volume
- **Use case:** Luxury sites with Cloudflare/strong anti-bot

### Overkill: Browserless.io, ZenRows, Bright Data
- **Cost:** $0.016-0.025/comparison ❌ Over budget
- **Use case:** Only if simpler solutions fail

## Implementation Strategy

### Phase 1: Test with Microlink (Week 1)
```python
import httpx

async def fetch_luxury_price_microlink(url: str) -> dict:
    """
    Try Microlink API for JS-rendered luxury pages.
    """
    api_url = f"https://api.microlink.io"
    params = {
        "url": url,
        "screenshot": False,
        "meta": False,
        "insights": False,
        "scripts": True,  # Enable JS rendering
        "waitFor": 2000   # Wait 2s for JS
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        html = data.get("data", {}).get("html", "")

        # Parse JSON-LD from rendered HTML
        return parse_jsonld_from_html(html)
```

**Test targets:**
- louisvuitton.com product page
- hermes.com product page
- chanel.com product page

**Success criteria:**
- Extracts price from JSON-LD or meta tags
- <5s latency
- Works for 80%+ of luxury pages

**If Microlink fails:** Move to Phase 2

### Phase 2: Self-hosted Playwright (Week 2)
```python
from playwright.async_api import async_playwright

async def fetch_luxury_price_playwright(url: str) -> dict:
    """
    Use Playwright for heavily protected luxury sites.
    Keep browser instance warm between requests.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(2000)  # Extra wait for dynamic content

            # Extract JSON-LD
            jsonld = await page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    return Array.from(scripts).map(s => JSON.parse(s.textContent));
                }
            """)

            return parse_jsonld_product(jsonld)
        finally:
            await browser.close()
```

**Deploy to Railway:**
1. Add to `requirements.txt`: `playwright==1.40.0`
2. Add to Dockerfile:
   ```dockerfile
   RUN playwright install chromium
   RUN playwright install-deps
   ```
3. Test memory usage (Railway Starter: 512MB limit)

**If memory/performance issues:** Add proxy service like BrightData residential proxies (~$500/month for 40GB = ~20k requests)

### Phase 3: ScrapingBee (Fallback)
Only if self-hosted fails or Railway resource limits are hit.

```python
async def fetch_luxury_price_scrapingbee(url: str) -> dict:
    """
    ScrapingBee with premium proxy for luxury sites.
    """
    api_key = os.getenv("SCRAPINGBEE_API_KEY")
    params = {
        "api_key": api_key,
        "url": url,
        "render_js": True,
        "premium_proxy": True,  # Needed for luxury sites
        "wait": 2000
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://app.scrapingbee.com/api/v1/",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        html = response.text

        return parse_jsonld_from_html(html)
```

## Integration Pattern

Update `structured_comparison_service.py`:

```python
async def _fetch_luxury_price_with_js_rendering(self, product_name: str, url: str) -> dict:
    """
    Fetch price from JS-rendered luxury brand page.

    Tier 1.5b: JS rendering for luxury official sites
    - Try Microlink first (cheapest)
    - Fallback to Playwright if available
    - Fallback to ScrapingBee if configured
    """
    try:
        # Try Microlink first (free tier: 50/day)
        if self._can_use_microlink():
            price_data = await self._fetch_with_microlink(url)
            if price_data:
                return price_data

        # Fallback to Playwright (self-hosted)
        if self._has_playwright():
            price_data = await self._fetch_with_playwright(url)
            if price_data:
                return price_data

        # Final fallback: ScrapingBee (paid)
        if self._has_scrapingbee():
            price_data = await self._fetch_with_scrapingbee(url)
            if price_data:
                return price_data

        # All rendering failed
        return None

    except Exception as e:
        logger.error(f"JS rendering failed for {url}: {e}")
        return None
```

## Railway Deployment Considerations

### Memory Limits
- Starter (512MB): Can handle 1 Chromium instance
- Pro (2GB): Can handle 3-4 instances
- Recommendation: Start with Starter, upgrade if needed

### Cold Starts
- Railway puts idle containers to sleep
- First request after sleep = 5-10s (browser launch)
- Solution: Keep-alive ping every 5 min to prevent sleep

### Docker Setup
```dockerfile
FROM python:3.12-slim

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing Plan

1. **Unit tests** (free):
   - Mock Microlink response
   - Test JSON-LD parsing
   - Test fallback chain

2. **Integration tests** (live):
   - Real luxury URLs (Louis Vuitton, Hermes, Chanel)
   - Measure latency
   - Verify price extraction accuracy

3. **Cost tracking**:
   - Count Microlink requests
   - Monitor Railway memory usage
   - Track ScrapingBee credits (if used)

## Success Metrics

- ✅ Extract prices from 90%+ of luxury official sites
- ✅ Stay under $0.02/comparison total cost
- ✅ <5s latency per JS rendering request
- ✅ Works on Railway infrastructure
- ✅ Graceful fallback if rendering fails

## Next Steps

1. **Immediate:** Test Microlink API with 5 luxury URLs (free tier = 50 requests/day)
2. **Week 1:** If Microlink succeeds, integrate into `structured_comparison_service.py`
3. **Week 2:** If Microlink fails, set up Playwright on Railway
4. **Fallback:** Budget for ScrapingBee ($99/month Startup plan) if self-hosted fails

## Links to Verify Pricing

- Browserless.io: https://www.browserless.io/pricing
- ScrapingBee: https://www.scrapingbee.com/pricing/
- ZenRows: https://www.zenrows.com/pricing
- Bright Data: https://brightdata.com/pricing/scraping-browser
- Microlink: https://microlink.io/pricing
- Railway: https://railway.app/pricing
