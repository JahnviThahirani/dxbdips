"""
twitter.py — Posts price drop alerts to @DXBDips on X (Twitter)
Called by runner.py after each scrape run.
Strategy: one summary tweet per scrape with Claude-generated dynamic language.
Format: hook → biggest sale drop → bridge → biggest rental drop → stats → close → CTA
"""
import os
import time
import threading
import anthropic
import tweepy


def get_twitter_client():
    return tweepy.Client(
        consumer_key=os.environ.get("TWITTER_API_KEY"),
        consumer_secret=os.environ.get("TWITTER_API_SECRET"),
        access_token=os.environ.get("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
    )


def get_anthropic_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def fmt_m(v):
    """Format sale price in AED millions."""
    return f"AED {v:.1f}M" if v >= 1 else f"AED {v * 1000:.0f}K"


def fmt_k(v):
    """Format rental price in AED thousands/yr."""
    return f"AED {v / 1000:.0f}K/yr" if v >= 1000 else f"AED {v:.0f}/yr"


def generate_dynamic_copy(
    top_sale: dict,
    top_rental: dict,
    total_listings: int,
    total_sale_drops: int,
    total_rental_drops: int,
    total_value_dropped_aed: float,
    biggest_pct_drop: float,
) -> dict:
    """
    Ask Claude to generate 3 dynamic text sections:
    - hook: opening line to stop the scroll
    - bridge: connects sale section to rental section
    - close: punchy closing line before CTA
    Returns dict with keys: hook, bridge, close
    """
    client = get_anthropic_client()

    sale_title    = (top_sale.get("title") or "Luxury Property")[:50]
    sale_area     = top_sale.get("area") or "Dubai"
    sale_drop_abs = fmt_m(top_sale.get("drop_abs_aed", 0))
    sale_old      = fmt_m(top_sale.get("old_price_aed", 0))
    sale_new      = fmt_m(top_sale.get("new_price_aed", 0))
    sale_pct      = top_sale.get("drop_pct", 0)

    rental_context = (
        f"Biggest rental drop: {fmt_k(top_rental.get('drop_abs_aed', 0))} "
        f"on {(top_rental.get('title') or 'Luxury Rental')[:50]} "
        f"in {top_rental.get('area') or 'Dubai'} "
        f"(-{top_rental.get('drop_pct', 0)}%)"
        if top_rental else "No rental drops this run."
    )

    prompt = f"""You write tweets for @DXBDips — a Dubai luxury real estate price drop tracker.
Your tone is slightly dramatic, data-driven, and intriguing. Never generic. Never salesy.
Vary the language every time — no two posts should sound the same.
No hashtags. No emojis unless very subtle.

Here is the data from this scrape run:
- Biggest sale drop: {sale_drop_abs} on {sale_title} in {sale_area} ({sale_old} → {sale_new}, -{sale_pct}%)
- {rental_context}
- Total listings monitored: {total_listings:,}
- Sale drops detected: {total_sale_drops}
- Rental drops detected: {total_rental_drops}
- Total value dropped: {fmt_m(total_value_dropped_aed)}
- Biggest % drop this run: {biggest_pct_drop}%

Write exactly 3 short pieces of copy. Return ONLY a JSON object with these exact keys, nothing else:
{{
  "hook": "one punchy opening line that makes someone stop scrolling. reference the biggest sale drop specifically.",
  "bridge": "one short sentence that transitions from the sale section to the rental section. make it feel like the drops are widespread, not isolated.",
  "close": "one punchy closing line. slightly dramatic. makes the reader feel like they need to check the site right now."
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        import json
        text = response.content[0].text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"[Twitter] Claude copy generation failed: {e}", flush=True)
        return {
            "hook": f"A {sale_area} property just dropped {sale_drop_abs} in asking price.",
            "bridge": "The rental market is shifting too.",
            "close": "Every drop. Every listing. In real time.",
        }


def build_tweet(
    top_sale: dict,
    top_rental: dict,
    total_listings: int,
    total_sale_drops: int,
    total_rental_drops: int,
    total_value_dropped_aed: float,
    biggest_pct_drop: float,
) -> str:
    """Build the full summary tweet."""

    copy = generate_dynamic_copy(
        top_sale=top_sale,
        top_rental=top_rental,
        total_listings=total_listings,
        total_sale_drops=total_sale_drops,
        total_rental_drops=total_rental_drops,
        total_value_dropped_aed=total_value_dropped_aed,
        biggest_pct_drop=biggest_pct_drop,
    )

    hook   = copy.get("hook", "")
    bridge = copy.get("bridge", "")
    close  = copy.get("close", "")

    # ── Sale block ──────────────────────────────────────
    sale_title    = (top_sale.get("title") or "Luxury Property")[:50]
    sale_building = top_sale.get("building") or ""
    sale_area     = top_sale.get("area") or "Dubai"
    sale_type     = (top_sale.get("type") or "Property").title()
    sale_beds     = top_sale.get("beds")
    sale_size     = top_sale.get("size_sqft")
    sale_old      = fmt_m(top_sale.get("old_price_aed", 0))
    sale_new      = fmt_m(top_sale.get("new_price_aed", 0))
    sale_drop_abs = fmt_m(top_sale.get("drop_abs_aed", 0))
    sale_pct      = top_sale.get("drop_pct", 0)

    location_parts = [p for p in [sale_building, sale_area] if p]
    sale_location  = " · ".join(location_parts) if location_parts else "Dubai"

    details_parts = [sale_type]
    if sale_beds: details_parts.append(f"{sale_beds} BR")
    if sale_size: details_parts.append(f"{int(sale_size):,} sqft")
    sale_details = " · ".join(details_parts)

    sale_block = (
        f"🔻 Sale — {sale_drop_abs} drop\n"
        f"{sale_title}\n"
        f"📍 {sale_location}\n"
        f"🏠 {sale_details}\n"
        f"{sale_old} → {sale_new} (-{sale_pct}%)"
    )

    # ── Rental block ────────────────────────────────────
    if top_rental:
        rental_title    = (top_rental.get("title") or "Luxury Rental")[:50]
        rental_building = top_rental.get("building") or ""
        rental_area     = top_rental.get("area") or "Dubai"
        rental_type     = (top_rental.get("type") or "Property").title()
        rental_beds     = top_rental.get("beds")
        rental_old      = fmt_k(top_rental.get("old_price_aed", 0))
        rental_new      = fmt_k(top_rental.get("new_price_aed", 0))
        rental_drop_abs = fmt_k(top_rental.get("drop_abs_aed", 0))
        rental_pct      = top_rental.get("drop_pct", 0)

        r_location_parts = [p for p in [rental_building, rental_area] if p]
        rental_location  = " · ".join(r_location_parts) if r_location_parts else "Dubai"

        r_details_parts = [rental_type]
        if rental_beds: r_details_parts.append(f"{rental_beds} BR")
        rental_details = " · ".join(r_details_parts)

        rental_block = (
            f"🔑 Rental — {rental_drop_abs} drop\n"
            f"{rental_title}\n"
            f"📍 {rental_location}\n"
            f"🏠 {rental_details}\n"
            f"{rental_old} → {rental_new} (-{rental_pct}%)"
        )
    else:
        rental_block = None

    # ── Stats block ─────────────────────────────────────
    total_drops = total_sale_drops + total_rental_drops
    stats_block = (
        f"Tracking {total_listings:,} Dubai properties:\n"
        f"→ {total_drops} price drops this run\n"
        f"→ {fmt_m(total_value_dropped_aed)} in total value reduced\n"
        f"→ Biggest % cut: {biggest_pct_drop}%"
    )

    # ── Assemble ─────────────────────────────────────────
    parts = [hook, sale_block]
    if rental_block:
        parts += [bridge, rental_block]
    parts += [stats_block, close, "dxbdips.com"]

    tweet = "\n".join(parts)

    if len(tweet) > 25000:
        tweet = tweet[:24997] + "..."

    return tweet


def _post_tweet_background(tweet: str, client):
    """Post the single summary tweet in a background daemon thread."""
    try:
        client.create_tweet(text=tweet)
        print(f"[Twitter] ✅ Summary tweet posted successfully.", flush=True)
        print(f"[Twitter] Tweet content:\n{tweet}", flush=True)
    except Exception as e:
        print(f"[Twitter] ❌ Error posting tweet: {e}", flush=True)


def post_drops(
    sale_drops: list,
    rental_drops: list,
    total_sale_listings: int = 0,
    total_rental_listings: int = 0,
):
    """
    Post one summary tweet per scrape run.
    - Leads with the biggest sale drop
    - Bridges to the biggest rental drop
    - Includes full stats block
    - Dynamic language generated by Claude each time
    - Fires in a background daemon thread
    """
    print(f"[Twitter] post_drops() called — {len(sale_drops)} sale, {len(rental_drops)} rental drops", flush=True)

    if not os.environ.get("TWITTER_API_KEY"):
        print("[Twitter] No Twitter credentials found, skipping.", flush=True)
        return

    if not sale_drops and not rental_drops:
        print("[Twitter] No drops to tweet about this run.", flush=True)
        return

    top_sale   = max(sale_drops,   key=lambda d: d.get("drop_abs_aed", 0)) if sale_drops   else None
    top_rental = max(rental_drops, key=lambda d: d.get("drop_abs_aed", 0)) if rental_drops else None

    if not top_sale:
        print("[Twitter] No sale drops this run — skipping tweet.", flush=True)
        return

    total_listings      = total_sale_listings + total_rental_listings
    total_value_dropped = sum(d.get("drop_abs_aed", 0) for d in sale_drops + rental_drops)
    all_pcts            = [d.get("drop_pct", 0) for d in sale_drops + rental_drops]
    biggest_pct         = round(max(all_pcts), 2) if all_pcts else 0

    print("[Twitter] Generating tweet copy via Claude...", flush=True)
    tweet = build_tweet(
        top_sale=top_sale,
        top_rental=top_rental,
        total_listings=total_listings,
        total_sale_drops=len(sale_drops),
        total_rental_drops=len(rental_drops),
        total_value_dropped_aed=total_value_dropped,
        biggest_pct_drop=biggest_pct,
    )

    print(f"[Twitter] Tweet generated ({len(tweet)} chars). Firing in background thread...", flush=True)

    twitter_client = get_twitter_client()
    t = threading.Thread(
        target=_post_tweet_background,
        args=(tweet, twitter_client),
        daemon=True,
        name="twitter-poster",
    )
    t.start()
    print(f"[Twitter] Background thread started (id={t.ident}). Runner continuing...", flush=True)
