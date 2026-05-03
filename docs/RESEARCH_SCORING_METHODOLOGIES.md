# Product Scoring Methodology Research

**Research Date:** March 20, 2026
**Purpose:** Understand how major product review/comparison sites score and rank products to inform SmartCompare's scoring engine improvements.

---

## Executive Summary

This research examines the scoring methodologies of 7 major product comparison platforms. Key findings:

1. **No single "best" approach exists** - methodologies vary widely based on product category, target audience, and business model
2. **Transparency builds trust** - sites that publish their methodology see 25-40% higher engagement
3. **Category-specific scoring is essential** - Consumer Reports weights reliability heavily for appliances (up to 20%) but lower for electronics
4. **Absolute vs relative scores** - most sites use absolute scores (fixed benchmarks) but present them in relative context (rankings within category)
5. **Value scoring is complex** - luxury vs budget products require different evaluation frameworks, not just price normalization

### Key Innovation Opportunities for SmartCompare

- **Performance Usage Scores** (RTINGS model): Standalone dimension scores (brightness, color, motion) that users can weight based on their priorities
- **Transparent methodology** with visible scoring breakdown increases user trust by 25-40%
- **Category-adaptive weighting** like Consumer Reports (reliability matters more for appliances than phones)
- **Value-tier awareness** - explicitly acknowledge when comparing across price tiers and adjust expectations

---

## 1. Wirecutter (NYT)

### Overview
- **Owned by:** The New York Times
- **Approach:** Editorial recommendations, not numeric scores
- **Philosophy:** "Best product at a reasonable price" - value-focused, not premium-focused

### Methodology

**Testing Process:**
1. **Research phase:** 20-40 hours reviewing scientific literature and expert opinions
2. **Selection phase:** Narrow 50-100 products down to 10-15 finalists based on criteria
3. **Testing phase:** Weeks or months of real-world use by multiple testers
4. **Expert consultation:** Interviews with doctors, scientists, specialists
5. **Periodic re-testing:** Ensure recommendations stay current

**Key Characteristics:**
- **No numeric scores** - editorial "Best Pick" and "Also Great" recommendations
- **Obsessive spreadsheeting** - comparison tables assess each product's features
- **Bias protection:** Writers/editors never know which products have affiliate deals
- **Long-term testing:** Focus on durability and real-world performance, not just launch specs
- **Paid tester program:** Monthly sessions with external testers for feedback

### Category Differences
- Historically used separate brand (The Sweethome) for home goods vs electronics
- Testing approach adapts to product type but maintains consistent quality bar
- No evidence of luxury vs budget different scoring - focus on "best value"

### Scoring Dimension Approach
**Implicit dimensions** (no published weights):
- Functionality (reliable performance under varied conditions)
- Durability (withstand regular use without failing)
- Value (good performance at reasonable price)
- User experience (ease of use, setup, maintenance)

### Innovation Insights
- **Transparency via disclosure:** Clearly state testing methods and potential biases
- **Anti-gaming design:** Financial incentives hidden from reviewers prevents bias
- **Value philosophy:** "Best at reasonable price" > "absolute best regardless of price"

**Sources:**
- [Wirecutter Product Recommendations - NYT Help Center](https://thenewyorktimeshelpcenter.helpjuice.com/21870729656596-Wirecutter-Product-Recommendations)
- [Wirecutter Wikipedia](https://en.wikipedia.org/wiki/Wirecutter_(website))
- [Wirecutter Testing Philosophy - TikTok](https://www.tiktok.com/@wirecutter/video/7431583804122336558)

---

## 2. Consumer Reports

### Overview
- **Scoring System:** 0-100 scale
- **Approach:** Lab testing + owner surveys + data privacy analysis
- **Strength:** Category-specific weighting based on consumer priorities

### Methodology

**Overall Score Components:**
- **Lab Tests:** up to 100% (varies by category)
- **Predicted Reliability:** up to 20% (higher for appliances, lower for electronics)
- **Owner Satisfaction:** up to 5%
- **Data Security & Privacy:** up to 40% (for connected devices)

*Percentages determined on a category-by-category basis based on technical considerations and consumer priorities.*

**Category-Specific Examples:**

**Appliances, Home Products, Consumer Electronics:**
- Lab testing (performance, ease of use, specifications)
- Predicted reliability (critical for appliances due to pivotal role in daily life)
- Owner satisfaction
- Data security/privacy (for connected devices)

**Automobiles:**
- Performance metrics (acceleration, braking, emergency handling, fuel economy)
- Safety systems evaluation
- Noise and ride quality
- Usability testing
- Reliability prediction (20 specific trouble areas evaluated)
- Severity weighting (minor issues vs major/expensive problems)

### Category Differences

**Key Insight:** Consumer Reports explicitly adjusts weighting based on product characteristics:

> "Consumers are very concerned about the reliability of large appliances given the pivotal role they play in their daily lives, and as a result, Predicted Reliability for large appliances has a higher weighting, in general, as opposed to many electronic devices. Electronics tend to be more reliable and may be kept for a shorter period of time, which results in a lower weighting in some categories."

**Car Rating Example:**
- Performance, comfort, usability, fit/finish ratings are comparable across all car types
- BUT each value is weighted differently by test group
- Example: Rear-seat access might score very low for a sports car, but won't impact Overall Score much

### Transparency vs Proprietary

- Publish general methodology and sample size thresholds
- Provide context on data prep and analysis
- **DO NOT** publish exact formulas or weighting factors (competitive advantage)

### Innovation Insights
- **Adaptive category weighting** based on consumer priorities (appliance reliability > electronics reliability)
- **Context-appropriate scoring** (sports car rear-seat access weighted low)
- **Severity-weighted reliability** (minor trim issues ≠ major drivetrain failures)
- **Multi-source data** (lab tests + owner surveys + reliability predictions)

**Sources:**
- [Consumer Reports Rating Methods](https://data.consumerreports.org/rating-methods/)
- [CR Car Reliability FAQ](https://www.consumerreports.org/cars/car-reliability-owner-satisfaction/consumer-reports-car-reliability-faq-a1099917197/)
- [CR Overall Score FAQ](https://www.consumerreports.org/cars/cars-what-goes-into-consumer-reports-overall-score-for-cars-a2015879559/)

---

## 3. Tom's Guide / Tom's Hardware

### Overview
- **Scoring System:** 1-5 star ratings (0.5 increments)
- **Approach:** Synthetic benchmarks + anecdotal use
- **Strength:** Clear rating meanings + award system

### Methodology

**Star Rating Scale:**
- **5 stars:** "Best of the best and close to perfect"
- **4.5 stars:** "Superb and among best in class, highly recommended"
- **4 stars:** "Excellent and recommended"
- **3.5 stars:** "Very good"
- **3 stars:** "Good but there are better options"
- **2.5 stars:** "Below average and not recommended"
- **2 stars:** "Poor and not recommended"
- **1 star:** "Very poor and among worst products we've tested"

**Award System:**
- **Editors' Choice:** Best-in-class
- **Recommended:** Among their favorites
- **Best Value:** Best combination of price and features (competitive price, robust selection, may lack some bells and whistles)

### Testing Approach

**Core Questions:**
1. Is this a good choice for readers?
2. If so, who should buy it?

**Method Transparency:**
- Describe how they tested each product
- Include synthetic benchmarks (objective)
- Include anecdotal use (subjective experiences)

**Category Differences:**
- **CPUs, GPUs, SSDs:** Highly scientific methods with standardized benchmarks
- **Gaming chairs, peripherals:** Primarily reviewer experience-based evaluation

### Scoring Philosophy
- **Comparative within category:** Tell readers whether alternatives are better/worse and in what ways
- **Absolute scale:** Star ratings are fixed benchmarks, but contextualized with comparisons
- **Value recognition:** Separate "Best Value" award acknowledges price/feature tradeoffs

### Innovation Insights
- **Clear rating semantics:** Each star level has explicit meaning (no ambiguity)
- **Award tiers:** Recognize different types of excellence (best overall vs best value)
- **Flexible methodology:** Scientific where possible (CPUs), experience-based where needed (chairs)
- **Guidance-focused:** Emphasize "who should buy it" alongside "is it good"

**Sources:**
- [How We Test - Tom's Guide](https://www.tomsguide.com/reference/how-we-test)
- [How We Test - Tom's Hardware](https://www.tomshardware.com/news/how-we-test)

---

## 4. RTINGS.com

### Overview
- **Scoring System:** 0-10 scale with dimension scores
- **Approach:** Standardized lab testing, full transparency
- **Strength:** Publicly documented methodology, objective benchmarks

### Methodology

**Core Principles:**
1. **Full transparency:** Testing methods, photos, videos all published
2. **Standardized procedures:** Same test bench for every product in category
3. **Self-purchased units:** No cherry-picked review units from brands
4. **Repeat measurements:** Objective benchmarks eliminate reviewer bias
5. **Quantitative comparison:** Users can compare products with identical metrics

### TV Test Bench 2.0 (March 2026 Update)

**Key Innovation: Performance Usage Scores**

Standalone scores for each performance dimension:
- **Brightness:** How much of reference color space reproducible across brightness levels (Gamut Rings for color volume)
- **Black Level:** Contrast and deep black performance
- **Color:** Color accuracy and saturation
  - New: Ambient Color Saturation (performance in bright rooms, not just dark lab)
- **Motion:** Response time including color transitions (critical for gaming/sports)
- **Other dimensions:** Varies by product category

**Changes in 2.0:**
- More rigorous scoring (tighter rubric, numbers better match real-world perception)
- Performance areas now weighted more clearly in overall Mixed Use score
- Color and motion categories especially re-weighted

### Category Coverage
- TVs (most comprehensive)
- Soundbars
- Monitors
- Headphones
- Earbuds
- Cameras
- Laptops
- Mice
- Keyboards

**All categories feature:**
- Real-world photos
- Quantitative test results
- Category-specific test methods
- Video reviews
- Benchmark test results

### Trust & Credibility
- **Trust rating:** 99.58% across 30 categories
- **Top performance:** 13 categories including TVs, soundbars, monitors
- **High Trust Tier** status reflects rigorous methodologies

### Business Model Note
- Recently moved to paid subscription for full results and ratings
- Basic information still free

### Innovation Insights
- **Dimension scores > single score:** Users can prioritize what matters to them (brightness vs color vs motion)
- **Transparent test bench:** Published methodology allows verification and trust
- **Quantitative benchmarks:** Eliminates subjective reviewer bias
- **Category-specific dimensions:** TV scores differ from headphone scores (appropriate for product type)
- **Living room reality:** Test under realistic conditions (bright rooms), not just ideal lab settings

**Sources:**
- [RTINGS.com](https://www.rtings.com)
- [Understanding Rtings - Oreate AI Blog](https://www.oreateai.com/blog/understanding-rtings-a-deep-dive-into-tv-ratings-and-their-impact/378cdb346cecc0fdbca3c461d1cebdaf)
- [RTINGS 2.0 Overview - Nanosys](https://www.nanosys.com/blog-newsroom/rtings-2-just-rewired-tv-reviews-and-quantum-dots-come-out-looking-really-good)

---

## 5. MKBHD (Marques Brownlee)

### Overview
- **Scoring System:** No formal numeric system; uses letter grades contextually
- **Approach:** Consumer perspective, narrative-driven reviews
- **Strength:** Authenticity, user-centric evaluation

### Methodology

**Core Philosophy:**
- "Talks about things from the perspective of the consumer—a person going out and buying things"
- Focus on **final result** rather than just technical specs
- Emphasis on **user experience** over spec sheet comparisons

**Review Process:**
1. Shape product narrative
2. Write scripts
3. Collaborate with team
4. Decide what becomes a video
5. Long-term real-world testing

### Scoring Approach

**Letter Grades (Contextual):**
- Uses grades like B+, A+, etc.
- **Not a single overall score** - rates for different use cases
- Example (MacBook Neo): "Podcasting: B+, Gaming: lowest rating"
- Tailored to specific user personas and workflows

### Transparency Principle
- "Transparency is non-negotiable"
- "We don't secretly take money from anyone. Ever."
- Clear disclosure of any brand relationships

### Category Differences
- No formal category-specific methodology
- Adapts evaluation criteria to product type naturally
- Emphasizes use-case fit over universal metrics

### Innovation Insights
- **Use-case scoring:** Product rated differently for different user needs (podcasting vs gaming)
- **Narrative over numbers:** Story-driven reviews make information accessible
- **Consumer proxy:** Represents buyer perspective, not technical enthusiast perspective
- **Transparency as trust:** Explicit disclosure of no paid relationships

**Sources:**
- [Marques Brownlee Wikipedia](https://en.wikipedia.org/wiki/Marques_Brownlee)
- [MKBHD Influence Article - Teach the 4 Ps](https://teachthe4ps.com/promotion/marques-brownlees-influence-on-tech-reviews-and-consumer-trends/)
- [State of the Workflow - Relay.fm](https://www.relay.fm/cortex/174)

---

## 6. Google Shopping

### Overview
- **Scoring System:** 1-5 star ratings (aggregated)
- **Approach:** Multi-source aggregation with spam filtering
- **Strength:** Massive data scale, product matching via GTINs

### Methodology

**Aggregation Process:**
1. **Gather reviews** from multiple sources:
   - Merchant websites
   - Third-party review aggregators (Trustpilot, etc.)
   - Google Customer Reviews
2. **Filter spam** and irrelevant content
3. **Calibrate ratings** to ensure consistency across different sources
4. **Aggregate** into single star rating (1-5) + total review count

**Product Matching:**
- **Primary:** GTIN (Global Trade Item Number) - globally unique identifier
- **Fallback:** SKU, Brand + MPN pairs, product URLs

### Display Format
- Star rating (1-5, with decimals)
- Total review count
- Shown in:
  - Google Search results
  - Google Shopping listings
  - Product ads
  - Free product listings

### No Scoring Methodology (Just Aggregation)
- Google doesn't "score" products - it aggregates existing ratings
- Acts as a meta-layer combining retailer/aggregator data
- No editorial judgment or testing

### Innovation Insights
- **Multi-source aggregation:** Combines merchant + aggregator + Google customer data
- **Spam filtering:** Algorithm removes low-quality reviews
- **Cross-source calibration:** Ensures consistency between different review platforms
- **GTIN-based matching:** Accurate product identification prevents review misattribution

**Sources:**
- [Product Ratings Basics - Google Merchant Center](https://support.google.com/merchants/answer/14620705?hl=en)
- [Ultimate Guide - Store Growers](https://www.storegrowers.com/product-ratings-in-google-shopping/)
- [Google Shopping Reviews Guide - Sellbrite](https://www.sellbrite.com/blog/google-shopping-reviews/)

---

## 7. Which? (UK Consumer Organization)

### Overview
- **Scoring System:** 0-100% scale
- **Approach:** Lab testing + reliability surveys + Best Buy threshold
- **Strength:** Combines performance testing with real-world reliability data

### Methodology

**TV Example (Detailed):**
Overall score based on:
- Picture quality
- Sound quality
- Ease of use
- Smart features
- Connections and tuners
- Running costs

**Scoring Tiers:**
- **71%+ = Best Buy** (recommended)
- **45% or below = Don't Buy** (avoid)

**Reliability Override:**
- Products with poor reliability (from owner surveys) do NOT get Best Buy designation
- **Even if they score well in lab tests**
- This prevents recommending products that perform well initially but fail quickly

### Best Buy Criteria
- Must score 71% or higher
- Must NOT have known poor reliability (from owner surveys)
- Must satisfy or exceed expert criteria
- Based on rigorous comparative testing and analysis

### Category Coverage
- Appliances
- Electronics
- Home products
- Cars
- Financial products
- And many more

### Innovation Insights
- **Reliability veto:** High performance doesn't overcome poor reliability
- **Owner survey integration:** Real-world longevity data overrides lab testing
- **Clear threshold:** 71% Best Buy cutoff is explicit and consistent
- **Comparative testing:** Products tested against competitors in same category

**Sources:**
- [Which? Best Buy 2024](https://www.which.co.uk/about-which/which-best-buy-aSxGr1B6pXCD)

---

## Key Findings: Absolute vs Relative Scoring

### Definitions

**Absolute Ratings:**
- Subjects receive scores based on **fixed, predefined scales**
- Measured against **predetermined benchmarks** that remain constant
- Enables judging products against **established quality standards**
- Example: Consumer Reports' 0-100 scale where 80 always means the same level of quality

**Relative Ratings:**
- Evaluate subjects by **comparing directly to others** in same category/peer group
- Generates rankings, percentiles, or comparative classifications
- Highlights **relative standing within specific contexts**
- Example: "Best in category" or "Top 10% of smartphones tested"

### When to Use Each

**Absolute Standards Preferred When:**
- Safety or quality concerns require minimum thresholds
- You want to ensure every product achieves a certain standard
- Comparing across different time periods (is this year's model better than last year's?)
- Need consistency over time (2024 scores comparable to 2025 scores)

**Relative Standards Preferred When:**
- Goal is to identify the top X% of options
- Market is highly competitive and differences are nuanced
- Users primarily care about "what's best" not "is this good enough"

### Best Practice: Hybrid Approach

**Most successful platforms integrate both:**
1. **Absolute scores** for individual product quality assessment
2. **Relative rankings** for comparison and shortlisting
3. **Context indicators** that show both absolute quality AND relative standing

**Example Hybrid:**
- Product A: Score 85/100 (absolute), Ranked #3 in category (relative)
- Product B: Score 82/100 (absolute), Ranked #5 in category (relative)

### Research Insights

> "Performance management systems are increasingly combining both approaches to provide comprehensive evaluation frameworks that capture both individual achievement and comparative standing."

> "Relative ranked satisfaction demonstrates superiority to absolute satisfaction measures in linking to customer behavior metrics like share of wallet."

**Sources:**
- [Relative vs Absolute Assessment - Comproved](https://comproved.com/en/abc-en/relative-vs-absolute-assessment-and-standards/)
- [Absolute vs Relative Metrics - Global Economics](https://www.elsevier.es/en-revista-global-economics-management-review-386-articulo-competitive-context-is-everything-moving-S2340154015000146)
- [Relative vs Absolute Scoring - rise.global](http://help.leaderboarded.com/knowledgebase/articles/613299-relative-scoring-vs-absolute-scoring-explained)

---

## Key Findings: Luxury vs Budget Product Comparison

### The Challenge

How do you fairly compare a $100 product with a $1,000 product? Different price tiers serve different market segments with different expectations.

### Market Segmentation

**Three Tiers of Luxury:**
1. **Standard Luxury:** Top 5-10% household income buyers
2. **High Luxury:** Top 1% household income buyers
3. **Ultra Luxury:** Top 0.1% household income buyers

Each tier has different value expectations and quality standards.

### Fair Comparison Strategies

#### 1. Tiered Pricing Structure
- **Basic tier:** Essential features for budget-conscious customers
- **Mid-range tier:** Added value for those willing to spend more
- **Premium tier:** Full package for customers who want the best

**Key principle:** Each tier has clear purpose and pricing logic that supports it.

#### 2. Value-for-Money Scoring
- Compare price to comparable products in same tier
- Consider brand reputation and customer satisfaction
- Evaluate uniqueness and exclusivity (for luxury)

**CarEdge Value Rating Example:**
> "Uses proprietary algorithm that compares average purchase price to future resale value and ongoing maintenance, repair, and insurance costs."

#### 3. Segment-Specific Expectations
- Budget shoppers: Compare prices across broad range, prioritize cost savings
- Luxury shoppers: Scrutinize premium brands, prioritize quality/exclusivity/craftsmanship

**Critical insight:**
> "Fair comparison requires adjusting evaluation criteria based on each price tier's target customer and value proposition, rather than applying identical standards across all price points."

#### 4. Price vs Features Balance Analysis
- Analyze costs, research the market, understand customer preferences
- Strike right balance between price and features for each tier
- Acknowledge tradeoffs explicitly

### Best Practices for Luxury vs Budget Scoring

**DO:**
- Evaluate within price tier first (compare $100 products to other $100 products)
- Use "value for money" as a dimension that accounts for price tier
- Acknowledge when comparing across tiers and adjust expectations
- Consider brand equity as a legitimate value factor for luxury

**DON'T:**
- Apply identical criteria to all price points (battery life ≠ craftsmanship)
- Penalize budget products for lacking luxury features
- Penalize luxury products for high price (if value justifies it)
- Ignore total cost of ownership (maintenance, repairs, insurance)

### Value for Money Formula Considerations

**Booking.com VFM Approach (Hospitality):**
1. **Price** - analyzed relative to similar properties
2. **Service quality** - cleanliness, facilities, staff friendliness
3. **Expectation matching** - does atmosphere meet expectations?

**Key insight:**
> "Higher prices reduce value for money, which on average worsens reviews. However, higher prices also induce only those consumers with a strong taste for the product to purchase, which on average improves reviews."

This creates a self-selection effect where luxury products may have higher satisfaction despite higher prices because buyers specifically wanted those features.

**Sources:**
- [Luxury Pricing Research - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0148296321002393)
- [3 Tier Pricing Strategy - Cone](https://www.getcone.io/blog/3-tier-pricing-strategy)
- [Three Tiers of Luxury - WARC](https://www.warc.com/content/feed/three-tiers-of-luxury/en-GB/8766)
- [Value for Money Methods - Better Evaluation](https://www.betterevaluation.org/methods-approaches/methods/value-for-money)
- [CarEdge Value Rating](https://caredge.com/ranks/value)
- [Booking.com VFM Score](https://partner.booking.com/en-gb/help/guest-reviews/general/understanding-value-money-score)

---

## Key Findings: General Best Practices

### Transparency Builds Trust

**Research Finding:**
> "Sites that publish their review methodology see 25-40% higher engagement than those that don't. Studies show that over 70% of consumers trust comparison sites only if they provide detailed review criteria and disclose how rankings are determined."

**Elements of Trustworthy Comparison:**
- Clear evaluation criteria
- Consistent structure across comparisons
- Honest tradeoffs acknowledged
- Verifiable details (specific enough to be checked)
- Visible update signals (when was this reviewed?)

### Category-Specific Methodology Essential

**Consumer Reports Insight:**
> "Predicted Reliability for large appliances has a higher weighting, in general, as opposed to many electronic devices. Electronics tend to be more reliable and may be kept for a shorter period of time."

Different product categories require different evaluation priorities. One-size-fits-all scoring fails to capture what actually matters for each category.

### Weighted Scoring Framework

**Best Practice Process:**
1. Identify most important attributes for the product category
2. Keep criteria consistent for fair comparison
3. **Assign weights** to reflect significance of each criterion
4. Rate each option against criteria on a scale
5. Multiply scores by weights to calculate weighted score

**Critical principle:**
> "Not all criteria are equally important—assign weights to reflect their significance."

### Audience Segmentation

**Key Insight:**
> "Tailor the comparison to your audience (e.g., budget shoppers vs. premium buyers) and emphasize the most decision-driving factors."

Different user segments care about different things:
- **Budget shoppers:** Price, durability, essential features
- **Premium buyers:** Quality, brand reputation, exclusive features
- **Tech enthusiasts:** Specifications, benchmarks, cutting-edge features
- **Mainstream users:** Ease of use, reliability, good-enough performance

### Data Quality & Triangulation

**Best Practice:**
> "Utilize diverse sources of information, as triangulating data from various reputable sources helps validate your findings and minimizes the risk of bias."

- Combine quantitative and qualitative data
- Use multiple independent sources
- Verify claims across sources
- Avoid cherry-picking scenarios that favor one product

### Comparison Scope Limits

**UX Best Practice:**
> "When more than 5 items need to be compared, add other mechanisms such as filters to help users narrow down the larger set of possibilities to 5 or fewer."

Too many comparison options creates decision paralysis. Help users narrow choices first, then compare finalists.

**Sources:**
- [Product Comparison Best Practices - Prismfly](https://prismfly.com/blog/product-comparisons)
- [Comparison Tables - Nielsen Norman Group](https://www.nngroup.com/articles/comparison-tables/)
- [Trustworthy Comparison Pages - NinjaTables](https://ninjatables.com/trustworthy-comparison-page/)
- [Product Review Sites Trust Study - WiserNotify](https://wisernotify.com/blog/product-review-websites/)

---

## Implications for SmartCompare

### Current State Analysis

**SmartCompare's Current Scoring (scoring_service.py):**
- 6 dimensions: price, spec, review, value, reliability, popularity
- 0-100 scale (absolute scoring)
- Personalized weights from user preferences (±30% max shift)
- Deterministic (pure math, $0 API cost)
- Single category weight set

**Strengths:**
- Deterministic and cost-free
- Personalization without extreme shifts
- Clear 0-100 scale

**Gaps Identified:**
1. **No category-specific weighting** - electronics and appliances use same dimension weights
2. **Limited transparency** - scoring breakdown not shown to users
3. **No dimension scores** - only overall score shown, not individual dimension performance
4. **Luxury vs budget** - no explicit handling of price tier expectations
5. **No reliability prediction** - relying only on review sentiment, not failure data
6. **Value score simplicity** - basic price/performance ratio, doesn't account for tier expectations

### Recommended Improvements

#### 1. Add Category-Specific Weight Profiles

**Implementation:**
```python
CATEGORY_WEIGHTS = {
    "electronics": {
        "spec": 0.25,
        "price": 0.20,
        "review": 0.20,
        "value": 0.15,
        "reliability": 0.10,  # Lower - electronics replaced more frequently
        "popularity": 0.10
    },
    "supplements": {
        "reliability": 0.25,  # Higher - health/safety critical
        "review": 0.25,
        "spec": 0.20,
        "value": 0.15,
        "price": 0.10,
        "popularity": 0.05
    },
    "fashion": {
        "review": 0.25,
        "spec": 0.20,  # Material, craftsmanship
        "value": 0.20,
        "popularity": 0.15,  # Brand matters more
        "price": 0.15,
        "reliability": 0.05  # Less critical
    },
    "grocery": {
        "value": 0.30,  # Price per unit critical
        "review": 0.25,
        "reliability": 0.20,  # Freshness, quality consistency
        "price": 0.15,
        "spec": 0.05,
        "popularity": 0.05
    }
}
```

**Rationale:** Follow Consumer Reports' lead - appliance reliability matters more than phone reliability.

#### 2. Expose Dimension Scores (RTINGS Model)

**Current:** Users only see overall winner + margin
**Proposed:** Show all 6 dimension scores for each product

**UI Changes:**
- Radar chart showing 6-dimension breakdown
- Individual dimension bars with scores
- Highlight which product wins each dimension
- Allow users to adjust dimension weights (advanced mode)

**Benefit:** Transparency builds trust (25-40% higher engagement). Users can see "Product A wins on price and value, Product B wins on specs and reviews."

#### 3. Price Tier Detection & Value Adjustment

**Implementation:**
```python
def detect_price_tier(price, category):
    """Classify product into budget/mid/premium tier."""
    if category == "electronics":
        if price < 300: return "budget"
        elif price < 800: return "mid"
        else: return "premium"
    elif category == "fashion":
        # Luxury brand detection already exists
        if is_luxury_brand(product_name): return "luxury"
        if price < 100: return "budget"
        elif price < 500: return "mid"
        else: return "premium"
    # ... category-specific thresholds

def calculate_value_score_tiered(product, tier, competitor_tier):
    """Adjust value expectations based on price tier."""
    base_value = calculate_value_score(product)

    # Cross-tier comparison adjustment
    if tier != competitor_tier:
        # Acknowledge comparing across tiers
        adjustment_factor = get_tier_adjustment(tier, competitor_tier)
        return base_value * adjustment_factor

    return base_value
```

**Response Addition:**
```json
{
  "product": {
    "price_tier": "premium",
    "value_score_context": "Evaluated against premium tier expectations"
  }
}
```

#### 4. Scoring Transparency in Response

**Add to comparison response:**
```json
{
  "scoring_methodology": {
    "dimensions": ["price", "spec", "review", "value", "reliability", "popularity"],
    "category": "electronics",
    "weights": {
      "price": 0.20,
      "spec": 0.25,
      "review": 0.20,
      "value": 0.15,
      "reliability": 0.10,
      "popularity": 0.10
    },
    "personalization_applied": true,
    "weight_shifts": {
      "price": -0.03,  // User prioritizes quality over price
      "spec": +0.05
    }
  },
  "products": [
    {
      "dimension_scores": {
        "price": 85,
        "spec": 92,
        "review": 78,
        "value": 88,
        "reliability": 82,
        "popularity": 90
      },
      "overall_score": 86.5,
      "dimension_wins": ["spec", "value", "popularity"]
    }
  ]
}
```

#### 5. Frontend Visualization Improvements

**ResultsScreen.tsx Additions:**
1. **Dimension Breakdown Section** (new tab or expandable)
   - 6-bar chart showing each dimension
   - Color-code winners (green = winning dimension)
   - Tap dimension for explanation

2. **Scoring Methodology Footnote**
   - "How we score" expandable section
   - Show category weights
   - Link to full methodology doc

3. **Price Tier Indicators**
   - Badge showing "Premium" / "Mid-range" / "Budget"
   - Note when comparing across tiers: "ℹ️ Comparing premium vs mid-range options"

#### 6. Reliability Data Enhancement (Future)

**Current:** Rely on review sentiment only
**Proposed:** Follow Which? model - integrate reliability data

**Potential Sources:**
- Owner surveys (requires scale)
- Return rate data (if available from retailers)
- Warranty claim data (if accessible)
- Community forums (scrape common complaints)

**Implementation:** Separate "reliability override" that can downgrade overall score if reliability is poor, even if other dimensions score well.

### Priority Ranking

**Phase 1 (High Impact, Low Cost):**
1. Add category-specific weight profiles ⭐
2. Expose dimension scores in response ⭐
3. Update frontend to show dimension breakdown ⭐
4. Add scoring methodology transparency section

**Phase 2 (Medium Impact, Medium Cost):**
5. Implement price tier detection and context
6. Adjust value scoring for cross-tier comparisons
7. Add price tier UI indicators

**Phase 3 (High Impact, High Cost):**
8. Build reliability data collection pipeline
9. Implement reliability override logic
10. Add owner survey system

### Testing Strategy

**Validation Questions:**
1. Do category-specific weights produce more accurate winners? (A/B test against current weights)
2. Does dimension score visibility increase user trust? (survey + engagement metrics)
3. Do users understand price tier context? (usability testing)
4. Does transparency increase perceived credibility? (before/after trust survey)

### Cost Analysis

- **Phase 1:** Zero API cost (all backend math + frontend display)
- **Phase 2:** Zero API cost (tier detection is deterministic logic)
- **Phase 3:** Moderate cost (reliability data collection requires infrastructure)

---

## Conclusion

The research reveals that successful product comparison sites share several key characteristics:

1. **Transparency is non-negotiable** - users trust sites that explain their methodology
2. **Category-specific approaches** - one size does NOT fit all
3. **Hybrid absolute/relative scoring** - show both quality level and competitive standing
4. **Price tier awareness** - acknowledge luxury vs budget differences
5. **Dimension visibility** - users want to see what drives the overall score
6. **Multi-source data** - combine lab tests, owner surveys, and real-world usage

SmartCompare's current scoring engine is solid but can be significantly improved by:
- Adding category-specific weight profiles (like Consumer Reports)
- Exposing dimension scores (like RTINGS)
- Implementing price tier context (like value-for-money frameworks)
- Increasing transparency (like all trusted sites)

These improvements align with SmartCompare's philosophy: "SMART, Not Just Cheap" - intelligent scoring that helps users make informed decisions, not just find the lowest price.

---

**Next Steps:**
1. Review this research document with team
2. Prioritize Phase 1 improvements
3. Create design doc for category-specific weights
4. Prototype dimension score visualization
5. Plan user testing for transparency features
