// Permanent static fallback listings.
// These render ALWAYS — regardless of API/DB status, filters, or live data —
// so the feed never looks empty or broken.
//
// Data pulled from real Feb 2026 listings (already 30+ days old, so they
// never collide with real time-window filters or appear duplicated).
//
// HOW TO FILL THIS IN:
// Run the SQL query provided in chat against Supabase, export the results
// as JSON, and paste each row into the objects below — matching field names.
// Sale prices are in MILLIONS AED (e.g. 5.2 = 5.2M). Rental prices are RAW
// AED/year (e.g. 320000).

export const FALLBACK_SALE_DROPS = [
  {
    id: "fallback-sale-1",
    listing_id: "FILL_ME",
    title: "FILL_ME",
    building: "FILL_ME",
    area: "FILL_ME",
    type: "apartment", // apartment | villa | penthouse | townhouse
    beds: 2,
    size_sqft: 1400,
    image_url: "FILL_ME",
    url: "FILL_ME",
    drop_pct: 8.5,
    drop_abs_aed: 0.45,     // millions
    drop_abs_usd: 0.12,     // millions
    old_price_aed: 5.3,     // millions
    old_price_usd: 1.44,    // millions
    new_price_aed: 4.85,    // millions
    new_price_usd: 1.32,    // millions
    detected_at: "2026-02-15T10:00:00Z",
    is_example: true,
  },
  // ...repeat for 9 more sale entries
];

export const FALLBACK_RENTAL_DROPS = [
  {
    id: "fallback-rental-1",
    listing_id: "FILL_ME",
    title: "FILL_ME",
    building: "FILL_ME",
    area: "FILL_ME",
    type: "apartment",
    beds: 2,
    size_sqft: 1200,
    image_url: "FILL_ME",
    url: "FILL_ME",
    drop_pct: 6.2,
    drop_abs_aed: 25000,     // raw AED/yr
    drop_abs_usd: 6800,
    old_price_aed: 400000,   // raw AED/yr
    old_price_usd: 108900,
    new_price_aed: 375000,   // raw AED/yr
    new_price_usd: 102100,
    detected_at: "2026-02-18T10:00:00Z",
    is_example: true,
  },
  // ...repeat for 9 more rental entries
];
