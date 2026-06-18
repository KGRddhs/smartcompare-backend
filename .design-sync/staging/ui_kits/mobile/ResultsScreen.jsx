/**
 * Qaren — ResultsScreen (reference, web) — CATEGORY-DRIVEN.
 *
 * Source of truth: AI/smartcompare/SmartCompareApp/src/components/results/
 *   ResultsContent.tsx  (+ ResultsAccordion.tsx, RunnerUpWinsCard.tsx,
 *    CategoryProfile.tsx, DimensionBars.tsx, ConfidencePills.tsx,
 *    FactualVerdict.tsx, PersonalizationChip.tsx, TopMatchBadge.tsx).
 *   Per-category structure: app/services/scoring_service.py CATEGORY_DIMENSIONS
 *   + DIMENSION_DISPLAY_NAMES, extraction_service.py CATEGORY_SPEC_SCHEMAS +
 *   build_category_profile, price_service.py CATEGORY_FAIRNESS.
 *   Synced to the shipped state 2026-06-18.
 *
 * ── ONE shell, NINE categories ──────────────────────────────────────────
 * The Results page is a SINGLE generic shell. The category determines the
 * DATA, not the layout: the backend emits `dimensions[]`,
 * `category_profile.fields[]`, and `specs_comparison[]` already shaped for the
 * product's category, and the FE renders them generically (CategoryProfile
 * renders any fields[]; DimensionBars renders any dimensions[]). So each of the
 * 9 Qaren categories — Electronics, Grocery, Supplements, Makeup, Skincare,
 * Haircare, Fragrances, Fashion, Other — gets its OWN dimensions, "At a glance"
 * fields, Specs schema, and price-comparability basis, through the SAME shell.
 *
 * Render a specific category:  <QarenResultsScreen category="fragrances" />
 * (default "electronics"). window.QAREN_RESULT_CATEGORIES lists all 9 keys.
 *
 * Single-scroll anatomy (top → bottom):
 *   1. Header — back + share + emerald "Top match" eyebrow
 *   2. Hero — two product cards (name · brand · variant · price), winner
 *      outlined emerald; comparable basis caption (CATEGORY_FAIRNESS like-for-
 *      like, e.g. "Compared at the same 100 ml") — omitted for fashion/other,
 *      which have no single comparable unit.
 *   3. "Why this fits you" — FactualVerdict (line1 factual deltas, NO
 *      evaluative words; line2 runner-up conditional, italic) + PersonalizationChip
 *   4. "Where the runner-up wins" — runner-up name + tradeoff + winning dims
 *      (NEUTRAL gray — emerald is reserved for the winner)
 *   5. Dimension bars — ONE compact "A · B" legend, then per-category dims
 *      (single split track, emerald = the higher-scoring side per dim)
 *   6. "What we know" — confidence pills (dot: high=emerald / med=amber / low=gray)
 *   7. Cohort line — "N shoppers in <governorate> leaned the same way"
 *   8. "Dig deeper" — At a glance · Reviews · Pros & Cons · Specs
 *   9. Feedback — "Was this helpful?" (Accurate / Detailed / Fast)
 *
 * Hard invariants the design agent MUST preserve:
 *   - Ratings are NEVER AI-generated — stars render ONLY with a real rating.
 *   - Reviews are PARAPHRASED praise — no verbatim quotes / source domains / [N].
 *   - FactualVerdict line1 carries NO evaluative words (best/better/beats/…).
 *   - The runner-up block stays gray; emerald = winner signal only.
 *   - Like-for-like: never compare across different storage/size/count.
 */

const T_res = window.qarenTokens || {};
const C_res = T_res.colors || {};

// ════════════════════════════════════════════════════════════════════════
// Per-category content — realistic GCC-market sample data. Field ORDER and
// dimension/spec KEYS follow the backend schemas verbatim; only the example
// values are illustrative. `dimensions` show the 4 highest-weighted dims (the
// app's hero cap; the remaining 2 sit behind "See full breakdown").
// `winner` is the index (0=left/A, 1=right/B). At a glance / Reviews / Pros &
// Cons are authored winner-first; Specs stay in A→B product order.
// ════════════════════════════════════════════════════════════════════════
const CATEGORIES = {
  electronics: {
    label: 'Electronics',
    winner: 1,
    products: [
      { name: 'iPhone 15', brand: 'Apple', variant: '256GB · Black', price: '329 BHD', imageColor: '#E8E9ED' },
      { name: 'Galaxy S24', brand: 'Samsung', variant: '256GB · Onyx', price: '299 BHD', imageColor: '#1B1C1F' },
    ],
    basis: 'Compared at the same 256 GB',
    verdict: {
      line1: '30 BHD less · 0.2★ higher rating · longer battery life.',
      line2: 'If you’re already in Apple’s ecosystem, the iPhone 15 stays the easier switch.',
    },
    personalization: '↑ Performance · ↑ Value',
    runnerUp: { name: 'iPhone 15', prose: 'iPhone 15 pulls ahead on raw performance and long-term software support.', dims: ['Faster chipset', 'Longer software support', 'Lighter in hand'] },
    dimensions: [
      { label: 'Performance', a: 80, b: 84 },
      { label: 'Value', a: 72, b: 88 },
      { label: 'Features', a: 79, b: 85 },
      { label: 'Build quality', a: 86, b: 82 },
    ],
    confidence: [ ['Price · High', 'high'], ['Reviews · Medium', 'medium'], ['Specs · High', 'high'] ],
    cohort: '2,000+ shoppers in Capital leaned the same way.',
    atGlance: [
      { name: 'Galaxy S24', isWinner: true, fields: [['Display', '6.2″ AMOLED'], ['Processor','Snapdragon 8 Gen 3'], ['Battery', '4,000 mAh'], ['Rear camera', '50 MP']] },
      { name: 'iPhone 15', fields: [['Display', '6.1″ OLED'], ['Processor','A16 Bionic'], ['Battery', '3,349 mAh'], ['Rear camera', '48 MP']] },
    ],
    reviews: [
      { name: 'Galaxy S24', rating: 4.6, count: 2140, praise: 'Owners call out the bright display and all-day battery, with low-light photos a frequent standout.' },
      { name: 'iPhone 15', rating: 4.7, count: 3520, praise: 'Reviewers highlight the smooth performance and polished software, though several note the shorter battery.' },
    ],
    prosCons: [
      { name: 'Galaxy S24', isWinner: true, pros: ['Stronger camera', 'Longer battery', '30 BHD less'], cons: ['Slower app updates'] },
      { name: 'iPhone 15', pros: ['Faster CPU', 'Better ecosystem'], cons: ['Lower camera score', 'Shorter battery'] },
    ],
    specs: { a: 'iPhone 15', b: 'Galaxy S24', rows: [
      { label: 'Display', left: '6.1″ OLED', right: '6.2″ AMOLED', win: null },
      { label: 'Processor', left: 'A16 Bionic', right: 'Snapdragon 8 Gen 3', win: 'right' },
      { label: 'RAM', left: '6 GB', right: '8 GB', win: 'right' },
      { label: 'Storage', left: '256 GB', right: '256 GB', win: null },
      { label: 'Battery', left: '3,349 mAh', right: '4,000 mAh', win: 'right' },
      { label: 'Rear camera', left: '48 MP', right: '50 MP', win: 'right' },
      { label: 'Weight', left: '171 g', right: '167 g', win: 'right' },
    ] },
  },

  grocery: {
    label: 'Grocery',
    winner: 0,
    products: [
      { name: 'Nido Fortified', brand: 'Nestlé', variant: '1 kg tin', price: '4.20 BHD', imageColor: '#F4D35E' },
      { name: 'Anchor Full Cream', brand: 'Anchor', variant: '1 kg pouch', price: '3.80 BHD', imageColor: '#1F6FB2' },
    ],
    basis: 'Compared at the same 1 kg',
    verdict: {
      line1: '0.40 BHD more · fortified with 28 vitamins & minerals · higher protein.',
      line2: 'If price per gram is all that matters, Anchor lands cheaper.',
    },
    personalization: null,
    runnerUp: { name: 'Anchor Full Cream', prose: 'Anchor is the cheaper pour and a touch creamier for tea and coffee.', dims: ['Lower price per gram', 'Richer mouthfeel'] },
    dimensions: [
      { label: 'Nutrition', a: 88, b: 74 },
      { label: 'Ingredients', a: 82, b: 78 },
      { label: 'Taste', a: 79, b: 83 },
      { label: 'Value per serving', a: 76, b: 84 },
    ],
    confidence: [ ['Price · High', 'high'], ['Reviews · Medium', 'medium'], ['Specs · Medium', 'medium'] ],
    cohort: '1,500+ families in Muharraq leaned the same way.',
    atGlance: [
      { name: 'Nido Fortified', isWinner: true, fields: [['Size', '1 kg'], ['Calories', '490 / 100g'], ['Protein', '24 g / 100g'], ['Origin', 'Netherlands']] },
      { name: 'Anchor Full Cream', fields: [['Size', '1 kg'], ['Calories', '496 / 100g'], ['Protein', '26 g / 100g'], ['Origin', 'New Zealand']] },
    ],
    reviews: [
      { name: 'Nido Fortified', rating: 4.7, count: 1880, praise: 'Parents trust the added vitamins and say it dissolves smoothly with no clumping.' },
      { name: 'Anchor Full Cream', rating: 4.5, count: 1240, praise: 'Shoppers like the creamier taste and the lower price for everyday use.' },
    ],
    prosCons: [
      { name: 'Nido Fortified', isWinner: true, pros: ['28 added nutrients', 'Dissolves cleanly', 'Trusted for kids'], cons: ['Costs more'] },
      { name: 'Anchor Full Cream', pros: ['Cheaper per gram', 'Richer flavour'], cons: ['Not fortified'] },
    ],
    specs: { a: 'Nido Fortified', b: 'Anchor Full Cream', rows: [
      { label: 'Size', left: '1 kg', right: '1 kg', win: null },
      { label: 'Calories', left: '490 / 100g', right: '496 / 100g', win: null },
      { label: 'Protein', left: '24 g', right: '26 g', win: 'right' },
      { label: 'Fat', left: '26 g', right: '28 g', win: null },
      { label: 'Origin', left: 'Netherlands', right: 'New Zealand', win: null },
      { label: 'Organic', left: 'No', right: 'No', win: null },
    ] },
  },

  supplements: {
    label: 'Supplements',
    winner: 1,
    products: [
      { name: 'NOW Magnesium', brand: 'NOW Foods', variant: '60 caps · 400mg', price: '5.50 BHD', imageColor: '#E4EEE0' },
      { name: 'Solgar Magnesium', brand: 'Solgar', variant: '60 tabs · 400mg', price: '7.90 BHD', imageColor: '#7A1F2B' },
    ],
    basis: 'Compared at the same 60 count',
    verdict: {
      line1: '2.40 BHD more · citrate form · third-party tested.',
      line2: 'If cost per capsule is the priority, the NOW Foods bottle is cheaper.',
    },
    personalization: '↑ Efficacy · ↑ Safety',
    runnerUp: { name: 'NOW Magnesium', prose: 'NOW Foods delivers the same dose for less per capsule.', dims: ['Lower cost per serving', 'Wider availability'] },
    dimensions: [
      { label: 'Efficacy', a: 80, b: 86 },
      { label: 'Safety', a: 82, b: 88 },
      { label: 'Dosage', a: 84, b: 84 },
      { label: 'Value per serving', a: 86, b: 76 },
    ],
    confidence: [ ['Price · High', 'high'], ['Reviews · Medium', 'medium'], ['Specs · High', 'high'] ],
    cohort: '900+ shoppers in Capital leaned the same way.',
    atGlance: [
      { name: 'Solgar Magnesium', isWinner: true, fields: [['Count', '60 tablets'], ['Active ingredient', 'Magnesium citrate'], ['Dosage', '400 mg'], ['Form', 'Tablet']] },
      { name: 'NOW Magnesium', fields: [['Count', '60 capsules'], ['Active ingredient', 'Magnesium oxide'], ['Dosage', '400 mg'], ['Form', 'Capsule']] },
    ],
    reviews: [
      { name: 'Solgar Magnesium', rating: 4.7, count: 980, praise: 'Users report easy digestion and value the third-party testing on every batch.' },
      { name: 'NOW Magnesium', rating: 4.5, count: 2310, praise: 'Buyers like the dependable dose at a budget price for daily use.' },
    ],
    prosCons: [
      { name: 'Solgar Magnesium', isWinner: true, pros: ['Citrate (better absorbed)', 'Third-party tested', 'Gentle on stomach'], cons: ['Costs more'] },
      { name: 'NOW Magnesium', pros: ['Cheaper per serving', 'Easy to find'], cons: ['Oxide form'] },
    ],
    specs: { a: 'NOW Magnesium', b: 'Solgar Magnesium', rows: [
      { label: 'Count', left: '60 capsules', right: '60 tablets', win: null },
      { label: 'Active ingredient', left: 'Magnesium oxide', right: 'Magnesium citrate', win: 'right' },
      { label: 'Dosage', left: '400 mg', right: '400 mg', win: null },
      { label: 'Form', left: 'Capsule', right: 'Tablet', win: null },
      { label: 'Certifications', left: 'GMP', right: 'GMP · Non-GMO', win: 'right' },
      { label: 'Origin', left: 'USA', right: 'USA', win: null },
    ] },
  },

  makeup: {
    label: 'Makeup',
    winner: 1,
    products: [
      { name: 'Fit Me Foundation', brand: 'Maybelline', variant: '30 ml · 220 Natural', price: '4.50 BHD', imageColor: '#E7C9A9' },
      { name: 'True Match', brand: 'L’Oréal', variant: '30 ml · 3N Creamy', price: '6.90 BHD', imageColor: '#D8B38C' },
    ],
    basis: 'Compared at the same 30 ml',
    verdict: {
      line1: '2.40 BHD more · 45 shades · longer wear in heat.',
      line2: 'If budget is the priority, Fit Me covers the basics for less.',
    },
    personalization: null,
    runnerUp: { name: 'Fit Me Foundation', prose: 'Fit Me is the budget pick and skews more matte for oily skin.', dims: ['Lower price', 'More matte finish'] },
    dimensions: [
      { label: 'Longevity', a: 78, b: 86 },
      { label: 'Shade match', a: 80, b: 85 },
      { label: 'Skin compatibility', a: 82, b: 84 },
      { label: 'Finish', a: 83, b: 84 },
    ],
    confidence: [ ['Price · High', 'high'], ['Reviews · Medium', 'medium'], ['Specs · Medium', 'medium'] ],
    cohort: '1,100+ shoppers in Capital leaned the same way.',
    atGlance: [
      { name: 'True Match', isWinner: true, fields: [['Shade range', '45 shades'], ['Finish', 'Natural'], ['Coverage', 'Medium–buildable'], ['Volume', '30 ml']] },
      { name: 'Fit Me Foundation', fields: [['Shade range', '40 shades'], ['Finish', 'Matte'], ['Coverage', 'Medium'], ['Volume', '30 ml']] },
    ],
    reviews: [
      { name: 'True Match', rating: 4.6, count: 1620, praise: 'Reviewers praise the seamless shade match and a natural finish that lasts through the day.' },
      { name: 'Fit Me Foundation', rating: 4.4, count: 3010, praise: 'Fans love the value and the matte control on oily skin.' },
    ],
    prosCons: [
      { name: 'True Match', isWinner: true, pros: ['Truer shade match', 'Wears longer', 'Natural finish'], cons: ['Costs more'] },
      { name: 'Fit Me Foundation', pros: ['Cheaper', 'Great for oily skin'], cons: ['Fewer shades'] },
    ],
    specs: { a: 'Fit Me Foundation', b: 'True Match', rows: [
      { label: 'Shade range', left: '40 shades', right: '45 shades', win: 'right' },
      { label: 'Finish', left: 'Matte', right: 'Natural', win: null },
      { label: 'Coverage', left: 'Medium', right: 'Medium–buildable', win: 'right' },
      { label: 'Skin type', left: 'Oily', right: 'Normal–dry', win: null },
      { label: 'Cruelty-free', left: 'No', right: 'No', win: null },
      { label: 'Volume', left: '30 ml', right: '30 ml', win: null },
    ] },
  },

  skincare: {
    label: 'Skincare',
    winner: 1,
    products: [
      { name: 'Hyaluronic Acid 2%', brand: 'The Ordinary', variant: '30 ml serum', price: '2.90 BHD', imageColor: '#EDEDE7' },
      { name: 'Hyalu B5 Serum', brand: 'La Roche-Posay', variant: '30 ml serum', price: '16.90 BHD', imageColor: '#DCE9F2' },
    ],
    basis: 'Compared at the same 30 ml',
    verdict: {
      line1: '14 BHD more · vitamin B5 added · stronger clinical backing.',
      line2: 'If you want the lowest entry price, The Ordinary delivers the core active.',
    },
    personalization: '↑ Active ingredients · ↑ Skin compatibility',
    runnerUp: { name: 'Hyaluronic Acid 2%', prose: 'The Ordinary gives you the same headline active for a fraction of the price.', dims: ['Far lower price', 'Fragrance-free base'] },
    dimensions: [
      { label: 'Active ingredients', a: 78, b: 86 },
      { label: 'Efficacy evidence', a: 74, b: 88 },
      { label: 'Skin compatibility', a: 84, b: 85 },
      { label: 'Formulation', a: 80, b: 86 },
    ],
    confidence: [ ['Price · High', 'high'], ['Reviews · Medium', 'medium'], ['Specs · High', 'high'] ],
    cohort: '1,300+ shoppers in Capital leaned the same way.',
    atGlance: [
      { name: 'Hyalu B5 Serum', isWinner: true, fields: [['Skin type', 'All / sensitive'], ['Active ingredient', 'Hyaluronic acid + B5'], ['Fragrance-free', 'Yes'], ['Volume', '30 ml']] },
      { name: 'Hyaluronic Acid 2%', fields: [['Skin type', 'All'], ['Active ingredient', 'Hyaluronic acid'], ['Fragrance-free', 'Yes'], ['Volume', '30 ml']] },
    ],
    reviews: [
      { name: 'Hyalu B5 Serum', rating: 4.7, count: 2040, praise: 'Users report plumper, calmer skin within weeks and praise the lightweight, fast-absorbing feel.' },
      { name: 'Hyaluronic Acid 2%', rating: 4.5, count: 5120, praise: 'Buyers love the results-for-price and the no-frills, fragrance-free formula.' },
    ],
    prosCons: [
      { name: 'Hyalu B5 Serum', isWinner: true, pros: ['B5 boosts repair', 'Stronger evidence', 'Sensitive-skin safe'], cons: ['Much pricier'] },
      { name: 'Hyaluronic Acid 2%', pros: ['Lowest price', 'Fragrance-free'], cons: ['No added B5'] },
    ],
    specs: { a: 'Hyaluronic Acid 2%', b: 'Hyalu B5 Serum', rows: [
      { label: 'Skin type', left: 'All', right: 'All / sensitive', win: null },
      { label: 'Skin concern', left: 'Hydration', right: 'Hydration · repair', win: 'right' },
      { label: 'Active ingredient', left: 'Hyaluronic acid', right: 'Hyaluronic acid + B5', win: 'right' },
      { label: 'Fragrance-free', left: 'Yes', right: 'Yes', win: null },
      { label: 'Volume', left: '30 ml', right: '30 ml', win: null },
      { label: 'pH level', left: '6.0', right: '5.5', win: null },
    ] },
  },

  haircare: {
    label: 'Haircare',
    winner: 1,
    products: [
      { name: 'Total Repair 5', brand: 'L’Oréal Elvive', variant: '400 ml shampoo', price: '2.80 BHD', imageColor: '#C9A24B' },
      { name: 'Argan Oil Shampoo', brand: 'OGX', variant: '400 ml shampoo', price: '4.90 BHD', imageColor: '#E7D8B0' },
    ],
    basis: 'Compared at the same 400 ml',
    verdict: {
      line1: '2.10 BHD more · sulfate-free · argan-oil formula.',
      line2: 'If you want a wallet-friendly daily wash, Elvive does the job for less.',
    },
    personalization: null,
    runnerUp: { name: 'Total Repair 5', prose: 'Elvive is the everyday-value option and lathers richer.', dims: ['Lower price', 'Richer lather'] },
    dimensions: [
      { label: 'Hair type match', a: 80, b: 86 },
      { label: 'Results', a: 78, b: 85 },
      { label: 'Ingredients', a: 76, b: 86 },
      { label: 'Scent', a: 83, b: 84 },
    ],
    confidence: [ ['Price · High', 'high'], ['Reviews · Medium', 'medium'], ['Specs · Medium', 'medium'] ],
    cohort: '800+ shoppers in Capital leaned the same way.',
    atGlance: [
      { name: 'Argan Oil Shampoo', isWinner: true, fields: [['Hair type', 'Dry / damaged'], ['Sulfate-free', 'Yes'], ['Volume', '400 ml'], ['Scent', 'Argan']] },
      { name: 'Total Repair 5', fields: [['Hair type', 'Damaged'], ['Sulfate-free', 'No'], ['Volume', '400 ml'], ['Scent', 'Floral']] },
    ],
    reviews: [
      { name: 'Argan Oil Shampoo', rating: 4.6, count: 1740, praise: 'Users say hair feels softer and frizz drops, with a scent many describe as salon-like.' },
      { name: 'Total Repair 5', rating: 4.4, count: 2890, praise: 'Shoppers like the value and the rich lather for everyday washing.' },
    ],
    prosCons: [
      { name: 'Argan Oil Shampoo', isWinner: true, pros: ['Sulfate-free', 'Tames frizz', 'Argan nourishment'], cons: ['Costs more'] },
      { name: 'Total Repair 5', pros: ['Cheaper', 'Rich lather'], cons: ['Contains sulfates'] },
    ],
    specs: { a: 'Total Repair 5', b: 'Argan Oil Shampoo', rows: [
      { label: 'Hair type', left: 'Damaged', right: 'Dry / damaged', win: null },
      { label: 'Hair concern', left: 'Breakage', right: 'Frizz · dryness', win: null },
      { label: 'Sulfate-free', left: 'No', right: 'Yes', win: 'right' },
      { label: 'Paraben-free', left: 'No', right: 'Yes', win: 'right' },
      { label: 'Volume', left: '400 ml', right: '400 ml', win: null },
      { label: 'Scent', left: 'Floral', right: 'Argan', win: null },
    ] },
  },

  fragrances: {
    label: 'Fragrances',
    winner: 0,
    products: [
      { name: 'Black Orchid', brand: 'Tom Ford', variant: '100 ml · EDP', price: '89 BHD', imageColor: '#2B2230' },
      { name: 'Black Opium', brand: 'Yves Saint Laurent', variant: '100 ml · EDP', price: '62 BHD', imageColor: '#14110F' },
    ],
    basis: 'Compared at the same 100 ml',
    verdict: {
      line1: '27 BHD more · longer wear · stronger projection.',
      line2: 'If you prefer a sweeter coffee-vanilla signature, Black Opium fits.',
    },
    personalization: '↑ Longevity · ↑ Scent character',
    runnerUp: { name: 'Black Opium', prose: 'Black Opium is the lighter, sweeter crowd-pleaser and lands 27 BHD cheaper.', dims: ['Lower price', 'More versatile for daytime'] },
    dimensions: [
      { label: 'Scent character', a: 88, b: 80 },
      { label: 'Longevity', a: 86, b: 78 },
      { label: 'Projection', a: 85, b: 82 },
      { label: 'Versatility', a: 76, b: 84 },
    ],
    confidence: [ ['Price · High', 'high'], ['Reviews · High', 'high'], ['Specs · Medium', 'medium'] ],
    cohort: '1,900+ shoppers in Capital leaned the same way.',
    atGlance: [
      { name: 'Black Orchid', isWinner: true, fields: [['Scent family', 'Oriental floral'], ['Top notes', 'Truffle, blackcurrant'], ['Longevity', '8–10 hrs'], ['Concentration', 'Eau de Parfum']] },
      { name: 'Black Opium', fields: [['Scent family', 'Oriental vanilla'], ['Top notes', 'Coffee, pear'], ['Longevity', '6–8 hrs'], ['Concentration', 'Eau de Parfum']] },
    ],
    reviews: [
      { name: 'Black Orchid', rating: 4.7, count: 3120, praise: 'Wearers describe it as bold and long-lasting, with a rich dark-floral signature that turns heads.' },
      { name: 'Black Opium', rating: 4.6, count: 4480, praise: 'Fans love the sweet coffee-vanilla warmth and call it an easy everyday signature.' },
    ],
    prosCons: [
      { name: 'Black Orchid', isWinner: true, pros: ['Longer wear', 'Stronger projection', 'Distinctive character'], cons: ['Costs more', 'Heavy for daytime'] },
      { name: 'Black Opium', pros: ['Cheaper', 'More versatile'], cons: ['Softer longevity'] },
    ],
    specs: { a: 'Black Orchid', b: 'Black Opium', rows: [
      { label: 'Scent family', left: 'Oriental floral', right: 'Oriental vanilla', win: null },
      { label: 'Top notes', left: 'Truffle, blackcurrant', right: 'Coffee, pear', win: null },
      { label: 'Heart notes', left: 'Black orchid, spice', right: 'Jasmine, orange blossom', win: null },
      { label: 'Base notes', left: 'Patchouli, incense', right: 'Vanilla, patchouli', win: null },
      { label: 'Longevity', left: '8–10 hrs', right: '6–8 hrs', win: 'left' },
      { label: 'Sillage', left: 'Strong', right: 'Moderate', win: 'left' },
      { label: 'Volume', left: '100 ml', right: '100 ml', win: null },
      { label: 'Concentration', left: 'Eau de Parfum', right: 'Eau de Parfum', win: null },
    ] },
  },

  fashion: {
    label: 'Fashion',
    winner: 0,
    products: [
      { name: 'Club Fleece Hoodie', brand: 'Nike', variant: 'Size M · Black', price: '18.90 BHD', imageColor: '#222' },
      { name: 'Trefoil Hoodie', brand: 'Adidas', variant: 'Size M · Navy', price: '21.90 BHD', imageColor: '#1B2A4A' },
    ],
    basis: null, // fashion has no single comparable unit (CATEGORY_FAIRNESS unit=None)
    verdict: {
      line1: '3 BHD less · heavier cotton-blend fleece · roomier fit.',
      line2: 'If you want the classic Trefoil branding, the Adidas hoodie carries it.',
    },
    personalization: null,
    runnerUp: { name: 'Trefoil Hoodie', prose: 'Adidas leans on heritage branding and a slightly slimmer cut.', dims: ['Iconic Trefoil logo', 'Slimmer silhouette'] },
    dimensions: [
      { label: 'Craftsmanship', a: 84, b: 82 },
      { label: 'Fit & comfort', a: 86, b: 80 },
      { label: 'Style', a: 82, b: 84 },
      { label: 'Durability', a: 85, b: 83 },
    ],
    confidence: [ ['Price · High', 'high'], ['Reviews · Medium', 'medium'], ['Specs · Medium', 'medium'] ],
    cohort: '700+ shoppers in Capital leaned the same way.',
    atGlance: [
      { name: 'Club Fleece Hoodie', isWinner: true, fields: [['Material', 'Cotton-blend fleece'], ['Style', 'Pullover hoodie'], ['Closure type', 'Pullover'], ['Size options', 'XS–XXL']] },
      { name: 'Trefoil Hoodie', fields: [['Material', 'Cotton-blend fleece'], ['Style', 'Pullover hoodie'], ['Closure type', 'Pullover'], ['Size options', 'XS–XXL']] },
    ],
    reviews: [
      { name: 'Club Fleece Hoodie', rating: 4.6, count: 2600, praise: 'Buyers praise the heavy, soft fleece and a relaxed fit that holds up wash after wash.' },
      { name: 'Trefoil Hoodie', rating: 4.5, count: 1980, praise: 'Fans love the classic logo look, though a few find the cut slimmer than expected.' },
    ],
    prosCons: [
      { name: 'Club Fleece Hoodie', isWinner: true, pros: ['Heavier fleece', 'Roomier fit', 'Cheaper'], cons: ['Plainer branding'] },
      { name: 'Trefoil Hoodie', pros: ['Iconic logo', 'Crisp colour'], cons: ['Slimmer fit', 'Costs more'] },
    ],
    specs: { a: 'Club Fleece Hoodie', b: 'Trefoil Hoodie', rows: [
      { label: 'Material', left: 'Cotton-blend fleece', right: 'Cotton-blend fleece', win: null },
      { label: 'Style', left: 'Pullover hoodie', right: 'Pullover hoodie', win: null },
      { label: 'Closure type', left: 'Pullover', right: 'Pullover', win: null },
      { label: 'Size options', left: 'XS–XXL', right: 'XS–XXL', win: null },
      { label: 'Care instructions', left: 'Machine wash', right: 'Machine wash', win: null },
      { label: 'Color', left: 'Black', right: 'Navy', win: null },
    ] },
  },

  other: {
    label: 'Other',
    winner: 0,
    products: [
      { name: 'PowerCore 20000', brand: 'Anker', variant: '20,000 mAh · Black', price: '13.90 BHD', imageColor: '#222' },
      { name: 'Mi Power Bank 3', brand: 'Xiaomi', variant: '20,000 mAh · White', price: '9.90 BHD', imageColor: '#EDEDED' },
    ],
    basis: null, // "other" has no single comparable unit (CATEGORY_FAIRNESS unit=None)
    verdict: {
      line1: '4 BHD more · higher review score · sturdier casing.',
      line2: 'If you want the lowest price for the same capacity, the Xiaomi fits.',
    },
    personalization: null,
    runnerUp: { name: 'Mi Power Bank 3', prose: 'Xiaomi matches the capacity for 4 BHD less.', dims: ['Lower price', 'Lighter build'] },
    dimensions: [
      { label: 'Core function', a: 86, b: 82 },
      { label: 'Reviews', a: 87, b: 83 },
      { label: 'Build quality', a: 85, b: 80 },
      { label: 'Value', a: 78, b: 86 },
    ],
    confidence: [ ['Price · High', 'high'], ['Reviews · High', 'high'], ['Specs · Medium', 'medium'] ],
    cohort: '600+ shoppers in Capital leaned the same way.',
    atGlance: [
      { name: 'PowerCore 20000', isWinner: true, fields: [['Dimensions', '166 × 62 × 22 mm'], ['Weight', '344 g'], ['Material', 'ABS + PC'], ['Warranty', '18 months']] },
      { name: 'Mi Power Bank 3', fields: [['Dimensions', '150 × 74 × 24 mm'], ['Weight', '434 g'], ['Material', 'Aluminium'], ['Warranty', '6 months']] },
    ],
    reviews: [
      { name: 'PowerCore 20000', rating: 4.7, count: 5400, praise: 'Owners highlight the reliable fast charging and a compact, durable build for travel.' },
      { name: 'Mi Power Bank 3', rating: 4.5, count: 4120, praise: 'Buyers call it great value and praise the dual-port charging for the price.' },
    ],
    prosCons: [
      { name: 'PowerCore 20000', isWinner: true, pros: ['Higher rated', 'Sturdier casing', 'Lighter'], cons: ['Costs more'] },
      { name: 'Mi Power Bank 3', pros: ['Cheaper', 'Same capacity'], cons: ['Heavier', 'Shorter warranty'] },
    ],
    specs: { a: 'PowerCore 20000', b: 'Mi Power Bank 3', rows: [
      { label: 'Dimensions', left: '166 × 62 × 22 mm', right: '150 × 74 × 24 mm', win: null },
      { label: 'Weight', left: '344 g', right: '434 g', win: 'left' },
      { label: 'Material', left: 'ABS + PC', right: 'Aluminium', win: null },
      { label: 'Color', left: 'Black', right: 'White', win: null },
      { label: 'Warranty', left: '18 months', right: '6 months', win: 'left' },
    ] },
  },
};

const CATEGORY_ORDER = ['electronics', 'grocery', 'supplements', 'makeup', 'skincare', 'haircare', 'fragrances', 'fashion', 'other'];

// ════════════════════════════════════════════════════════════════════════
// Shared presentational components (category-agnostic)
// ════════════════════════════════════════════════════════════════════════

function TopMatchBadge() {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      paddingInline: 12, height: 26, borderRadius: 999,
      background: C_res.accentLight, color: C_res.accentDark,
      font: '600 11px/1.4 var(--qaren-font-en, system-ui)',
      letterSpacing: '1.1px', textTransform: 'uppercase',
    }}>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>
      Top match
    </div>
  );
}

// name / brand / variant / price. Pass price={null} to preview the price-pending
// state ("Pricing lands in an upcoming update." — never a number, never "estimated").
function ProductCard({ name, brand, variant, price, isWinner, imageColor }) {
  const pending = price == null;
  return (
    <div style={{
      flex: 1, minWidth: 0, borderRadius: 20,
      background: isWinner ? C_res.accentLight : C_res.bg.secondary,
      border: `${isWinner ? 2 : 1}px solid ${isWinner ? C_res.accent : C_res.border.light}`,
      padding: 14, display: 'flex', flexDirection: 'column', gap: 10, position: 'relative',
    }}>
      <div style={{ aspectRatio: '1 / 1', borderRadius: 14, background: imageColor || '#EEEFF4', display: 'grid', placeItems: 'center', color: C_res.text.placeholder }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="5" y="2" width="14" height="20" rx="2.5"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>
      </div>
      <div style={{ font: '600 15px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.primary }}>{name}</div>
      {brand ? <div style={{ font: '400 12px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.secondary }}>{brand}</div> : null}
      {variant ? <div style={{ font: '400 11px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.secondary }}>{variant}</div> : null}
      <div style={{
        marginTop: 'auto',
        font: pending ? '500 14px/1.3 var(--qaren-font-en, system-ui)' : '700 18px/1 var(--qaren-font-en, system-ui)',
        color: pending ? C_res.text.secondary : C_res.text.primary, fontVariantNumeric: 'tabular-nums',
      }}>
        {pending ? 'Pricing lands in an upcoming update.' : price}
      </div>
    </div>
  );
}

// Single-split bar: gray product-A share | 2px gap | gray product-B share, the
// HIGHER-scoring side painted emerald (per-dim winner). Names appear ONCE in the
// section legend above (walk-fix 2026-06-17) — never repeated per row.
function DimensionBar({ label, a, b, winnerIndex }) {
  const total = Math.max(1, a + b);
  const leftPct = (a / total) * 100;
  const rightPct = (b / total) * 100;
  // Per-dim winner = the higher score; a tie goes to the OVERALL winner
  // (mirrors DimensionBars.tsx: score_a===score_b && winnerIndex===0 → A wins).
  const aWins = a > b || (a === b && winnerIndex === 0);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ font: '500 13px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.primary }}>{label}</div>
      <div style={{ display: 'flex', height: 8, borderRadius: 999, overflow: 'hidden', background: C_res.border.light }}>
        <div style={{ width: `${leftPct}%`, background: aWins ? C_res.accent : C_res.text.secondary }} />
        <div style={{ width: 2, background: C_res.bg.primary }} />
        <div style={{ width: `${rightPct}%`, background: aWins ? C_res.text.secondary : C_res.accent }} />
      </div>
    </div>
  );
}

function ConfidencePill({ label, level }) {
  const ring = level === 'high' ? C_res.accent : level === 'medium' ? C_res.warning : C_res.border.medium;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6, paddingInline: 10, paddingBlock: 6,
      borderRadius: 999, background: C_res.bg.secondary, border: `1px solid ${C_res.border.light}`,
      font: '500 12px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.primary,
    }}>
      <span style={{ width: 8, height: 8, borderRadius: 4, background: ring }} />
      {label}
    </span>
  );
}

// "Where the runner-up wins" — neutral gray, never emerald. Self-hides when
// there is neither a winning dim nor tradeoff prose.
function RunnerUpWins({ name, prose, dims }) {
  if ((!dims || dims.length === 0) && !prose) return null;
  return (
    <section style={{ marginBottom: 24 }}>
      <h3 style={{ margin: '0 0 8px', font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase', color: C_res.text.secondary }}>
        Where the runner-up wins
      </h3>
      {name ? <div style={{ font: '600 13px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.primary, marginBottom: 4 }}>{name}</div> : null}
      {prose ? <p style={{ margin: 0, font: '400 13px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, textWrap: 'pretty' }}>{prose}</p> : null}
      {dims && dims.length > 0 ? (
        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {dims.map((d, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, font: '500 13px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.primary }}>
              <span style={{ color: C_res.text.secondary, marginTop: 1 }}>+</span>
              <span>{d}</span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

// "At a glance" 2-up — winner column first (★ + accentDark name). Each product
// renders its OWN ordered label·value list (category_profile.fields, in schema
// order). A field a product lacks is simply omitted (never dashed).
function CategoryProfileGrid({ columns }) {
  return (
    <div style={{ display: 'flex', gap: 16 }}>
      {columns.map((col, ci) => (
        <div key={ci} style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8,
            font: `${col.isWinner ? 700 : 600} 12px/1.3 var(--qaren-font-en, system-ui)`,
            color: col.isWinner ? C_res.accentDark : C_res.text.primary,
          }}>
            {col.isWinner && <span style={{ color: C_res.accentDark }}>★</span>}
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{col.name}</span>
          </div>
          {col.fields.map(([label, value], i) => (
            <div key={i} style={{ marginBottom: 8 }}>
              <div style={{ font: '400 11px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, letterSpacing: '0.3px', textTransform: 'uppercase', marginBottom: 2 }}>{label}</div>
              <div style={{ font: '500 13px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.primary }}>{value}</div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

// Paraphrased praise (replaces source-quote ReviewLine). Product name + (real
// stars + "rating · count reviews") + one synthesized, non-verbatim line. Stars
// render ONLY when a real rating exists.
function ReviewPraise({ name, rating, count, praise }) {
  const hasRating = typeof rating === 'number' && rating > 0;
  const filled = hasRating ? Math.max(0, Math.min(5, Math.round(rating))) : 0;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{ font: '600 12px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.primary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
        {hasRating ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
            <span style={{ display: 'inline-flex', gap: 1 }}>
              {[1,2,3,4,5].map(s => (
                <svg key={s} width="10" height="10" viewBox="0 0 24 24" fill={s <= filled ? C_res.warning : 'transparent'} stroke={s <= filled ? C_res.warning : C_res.border.medium} strokeWidth="2">
                  <path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
                </svg>
              ))}
            </span>
            <span style={{ font: '500 11px/1 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, fontVariantNumeric: 'tabular-nums' }}>
              {rating.toFixed(1)} · {count.toLocaleString()} reviews
            </span>
          </span>
        ) : null}
      </div>
      {praise ? <div style={{ font: '500 12px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.primary, textWrap: 'pretty' }}>{praise}</div> : null}
    </div>
  );
}

function ProsConsCol({ name, pros, cons, winner }) {
  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8,
        font: `${winner ? 700 : 600} 12px/1.3 var(--qaren-font-en, system-ui)`,
        color: winner ? C_res.accentDark : C_res.text.primary,
      }}>
        {winner && <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>}
        {name}
      </div>
      {pros.map((p, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, font: '500 11px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.primary, marginBottom: 3 }}>
          <span style={{ color: C_res.accentDark, marginTop: 1 }}>+</span><span>{p}</span>
        </div>
      ))}
      {cons.map((c, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, font: '500 11px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, marginBottom: 3 }}>
          <span style={{ color: C_res.text.placeholder, marginTop: 1 }}>−</span><span>{c}</span>
        </div>
      ))}
    </div>
  );
}

function SpecsHeader({ left, right }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 96px 1fr', alignItems: 'center', gap: 12, paddingBlock: 8, borderBlockEnd: `1px solid ${C_res.border.light}` }}>
      <div style={{ textAlign: 'end', font: '600 12px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.primary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{left}</div>
      <div />
      <div style={{ font: '600 12px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.primary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{right}</div>
    </div>
  );
}

function SpecRow({ label, left, right, win }) {
  // value · CENTERED-label · value. Winning cell paints emerald (per-row winner).
  const leftWin = win === 'left';
  const rightWin = win === 'right';
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 96px 1fr', alignItems: 'center', gap: 12, paddingBlock: 8, borderBlockEnd: `1px solid ${C_res.border.light}` }}>
      <div style={{ textAlign: 'end', font: `${leftWin ? 700 : 500} 12px/1.3 var(--qaren-font-en, system-ui)`, color: leftWin ? C_res.accent : C_res.text.primary }}>{left}</div>
      <div style={{ textAlign: 'center', font: '500 11px/1.3 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, letterSpacing: '0.4px', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ font: `${rightWin ? 700 : 500} 12px/1.3 var(--qaren-font-en, system-ui)`, color: rightWin ? C_res.accent : C_res.text.primary }}>{right}</div>
    </div>
  );
}

// "Dig deeper" — At a glance / Reviews / Pros & Cons / Specs, fed from the
// category data. One-toggle-at-a-time; calm closed default.
function DetailsAccordion({ data }) {
  const [open, setOpen] = React.useState(null);
  const toggle = (k) => setOpen((curr) => (curr === k ? null : k));
  const specRowCount = data.specs.rows.length;
  const sections = [
    {
      key: 'profile', label: 'At a glance', sub: 'Key details, both products',
      icon: (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>),
      body: <CategoryProfileGrid columns={data.atGlance} />,
    },
    {
      key: 'reviews', label: 'Reviews', sub: reviewsSub(data.reviews),
      icon: (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>),
      body: (<div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>{data.reviews.map((r, i) => <ReviewPraise key={i} {...r} />)}</div>),
    },
    {
      key: 'proscons', label: 'Pros & Cons', sub: 'Each product, both sides',
      icon: (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>),
      body: (<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>{data.prosCons.map((c, i) => <ProsConsCol key={i} {...c} />)}</div>),
    },
    {
      key: 'specs', label: 'Specs', sub: `${specRowCount} dimensions`,
      icon: (<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>),
      body: (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <SpecsHeader left={data.specs.a} right={data.specs.b} />
          {data.specs.rows.map((r, i) => <SpecRow key={i} {...r} />)}
        </div>
      ),
    },
  ];

  return (
    <section style={{ marginBottom: 8 }}>
      <h3 style={{ margin: '0 0 10px', font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase', color: C_res.text.secondary }}>Dig deeper</h3>
      <div style={{ borderRadius: 16, background: C_res.bg.secondary, border: `1px solid ${C_res.border.light}`, overflow: 'hidden' }}>
        {sections.map((s, i) => {
          const isOpen = open === s.key;
          return (
            <div key={s.key} style={{ borderBlockEnd: i < sections.length - 1 ? `1px solid ${C_res.border.light}` : 'none' }}>
              <button onClick={() => toggle(s.key)} aria-expanded={isOpen} style={{
                display: 'flex', alignItems: 'center', gap: 12, width: '100%', minHeight: 60,
                paddingBlock: 14, paddingInline: 16, background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'start', color: C_res.text.primary,
              }}>
                <span style={{ width: 32, height: 32, borderRadius: 16, background: C_res.bg.primary, color: isOpen ? C_res.accentDark : C_res.text.secondary, display: 'grid', placeItems: 'center', flexShrink: 0, transition: 'color 220ms ease' }}>{s.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ font: '600 14px/1.3 var(--qaren-font-en, system-ui)' }}>{s.label}</div>
                  <div style={{ font: '400 12px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, marginTop: 2 }}>{s.sub}</div>
                </div>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={C_res.text.placeholder} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 220ms ease' }}><polyline points="6 9 12 15 18 9"/></svg>
              </button>
              {isOpen && (
                <div style={{ paddingInline: 16, paddingBottom: 16, background: C_res.bg.primary, borderBlockStart: `1px solid ${C_res.border.light}` }}>
                  <div style={{ paddingTop: 14 }}>{s.body}</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// "{avg}★ avg · {total} reviews across both" — weighted by count, real ratings only.
function reviewsSub(reviews) {
  const rated = reviews.filter((r) => typeof r.rating === 'number' && r.rating > 0);
  const total = reviews.reduce((acc, r) => acc + (r.count || 0), 0);
  const tail = total > 0 ? `${total.toLocaleString()} reviews across both` : 'reviews across both';
  if (rated.length === 0) return tail;
  const wTotal = rated.reduce((acc, r) => acc + (r.count || 0), 0);
  const avg = wTotal > 0
    ? rated.reduce((acc, r) => acc + r.rating * (r.count || 0), 0) / wTotal
    : rated.reduce((acc, r) => acc + r.rating, 0) / rated.length;
  return `${avg.toFixed(1)}★ avg · ${tail}`;
}

// ════════════════════════════════════════════════════════════════════════
// The shell
// ════════════════════════════════════════════════════════════════════════
function QarenResultsScreen({ category = 'electronics' } = {}) {
  const data = CATEGORIES[category] || CATEGORIES.electronics;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', paddingTop: 50, background: C_res.bg.primary, fontFamily: 'var(--qaren-font-en, system-ui)', color: C_res.text.primary, overflow: 'hidden' }}>
      {/* Header */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingInline: 20, paddingBlock: 8 }}>
        <button aria-label="Back" style={{ width: 36, height: 36, borderRadius: 18, background: C_res.bg.secondary, border: 'none', display: 'grid', placeItems: 'center', cursor: 'pointer' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_res.text.primary} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
        <TopMatchBadge />
        <button aria-label="Share" style={{ width: 36, height: 36, borderRadius: 18, background: C_res.bg.secondary, border: 'none', display: 'grid', placeItems: 'center', cursor: 'pointer' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={C_res.text.primary} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
        </button>
      </header>

      {/* Scrolling body */}
      <main style={{ flex: 1, overflowY: 'auto', paddingInline: 20, paddingTop: 12, paddingBottom: 24 }}>
        {/* Hero — product pair (winner outlined emerald) */}
        <div style={{ display: 'flex', gap: 10, marginBottom: data.basis ? 8 : 20, position: 'relative' }}>
          {data.products.map((p, idx) => (
            <ProductCard key={idx} {...p} isWinner={idx === data.winner} />
          ))}
          <div style={{ position: 'absolute', insetBlockStart: '50%', insetInlineStart: '50%', transform: 'translate(-50%, -50%)', zIndex: 1 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', height: 24, paddingInline: 10, borderRadius: 999, background: C_res.accentLight, color: C_res.accentDark, font: '600 11px/1 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase', border: `2px solid ${C_res.bg.primary}` }}>vs</span>
          </div>
        </div>
        {/* Comparable basis — the CATEGORY_FAIRNESS like-for-like guarantee.
            Omitted for fashion/other (no single comparable unit). */}
        {data.basis ? (
          <div style={{ marginBottom: 20, font: '500 11px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.placeholder, letterSpacing: '0.2px' }}>
            {data.basis}
          </div>
        ) : null}

        {/* Why this fits you — FactualVerdict (line1 factual, NO evaluative
            words; line2 runner-up conditional italic) + PersonalizationChip. */}
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 8px', font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase', color: C_res.text.secondary }}>Why this fits you</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ font: '500 15px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.primary }}>{data.verdict.line1}</div>
            {data.verdict.line2 ? <div style={{ font: '400 14px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, fontStyle: 'italic' }}>{data.verdict.line2}</div> : null}
          </div>
          {/* PersonalizationChip — arrows only (↑/↓), never %, never coefficients.
              Hidden when the user set no priorities. */}
          {data.personalization ? (
            <div style={{ display: 'inline-flex', marginTop: 8, paddingInline: 12, paddingBlock: 4, borderRadius: 999, background: C_res.bg.secondary, font: '500 12px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.secondary }}>
              Weighted {data.personalization} (based on your priorities)
            </div>
          ) : null}
        </section>

        {/* Where the runner-up wins — neutral gray */}
        <RunnerUpWins name={data.runnerUp.name} prose={data.runnerUp.prose} dims={data.runnerUp.dims} />

        {/* Dimension bars — ONE compact "A · B" legend, then per-category dims */}
        <section style={{ marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', font: '600 12px/1.4 var(--qaren-font-en, system-ui)' }}>
            <span style={{ flex: 1, color: C_res.text.secondary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{data.products[0].name}</span>
            <span style={{ color: C_res.text.placeholder, paddingInline: 4 }}>·</span>
            <span style={{ flex: 1, textAlign: 'right', color: C_res.text.secondary, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{data.products[1].name}</span>
          </div>
          {data.dimensions.map((d, i) => <DimensionBar key={i} {...d} winnerIndex={data.winner} />)}
          <div style={{ font: '500 12px/1.4 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, textAlign: 'center', paddingTop: 2 }}>See full breakdown</div>
        </section>

        {/* What we know — confidence pills (dot: high=emerald / med=amber) */}
        <section style={{ marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 10px', font: '600 11px/1.4 var(--qaren-font-en, system-ui)', letterSpacing: '1.1px', textTransform: 'uppercase', color: C_res.text.secondary }}>What we know</h3>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {data.confidence.map(([label, level], i) => <ConfidencePill key={i} label={label} level={level} />)}
          </div>
        </section>

        {/* Cohort line — softened framing */}
        <p style={{ margin: '12px 0 20px', font: '500 12px/1.5 var(--qaren-font-en, system-ui)', color: C_res.text.secondary, padding: '10px 12px', borderRadius: 12, background: C_res.bg.secondary }}>
          {data.cohort}
        </p>

        {/* Dig deeper — At a glance / Reviews / Pros & Cons / Specs */}
        <DetailsAccordion data={data} />

        {/* Feedback prompt */}
        <section style={{ padding: 16, borderRadius: 16, border: `1px solid ${C_res.border.light}`, background: C_res.bg.secondary }}>
          <div style={{ font: '600 15px/1.4 var(--qaren-font-en, system-ui)', marginBottom: 10 }}>Was this helpful?</div>
          <div style={{ display: 'flex', gap: 8 }}>
            {['Accurate', 'Detailed', 'Fast'].map((l) => (
              <button key={l} style={{ paddingInline: 14, height: 36, borderRadius: 999, background: C_res.bg.primary, border: `1px solid ${C_res.border.light}`, color: C_res.text.primary, font: '500 13px/1 var(--qaren-font-en, system-ui)', cursor: 'pointer' }}>{l}</button>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

window.QarenResultsScreen = QarenResultsScreen;
window.QAREN_RESULT_CATEGORIES = CATEGORY_ORDER;
