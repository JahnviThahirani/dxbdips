"""
twitter.py — Posts price drop alerts to @DXBDips on X (Twitter)
Called by runner.py after each scrape run.

Strategy:
  - Main tweet: Claude-written hook + biggest SALE drop + one stats line
  - Auto-reply to own tweet: biggest RENTAL drop (if exists)
  - Clean, minimal format — no walls of text
"""
import json
import os
import threading

import anthropic
import tweepy


# ── Twitter & Anthropic clients ─────────────────────────────────────────────

def get_twitter_client():
    return tweepy.Client(
        consumer_key=os.environ.get("TWITTER_API_KEY"),
        consumer_secret=os.environ.get("TWITTER_API_SECRET"),
        access_token=os.environ.get("TWITTER_ACCESS_TOKEN"),
        access_token_secret=os.environ.get("TWITTER_ACCESS_TOKEN_SECRET"),
    )


def get_anthropic_client():
    return anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ── Formatting helpers ───────────────────────────────────────────────────────

def fmt_aed(value_m: float) -> str:
    """
    Format a sale price stored in millions of AED.
    Examples: 9.88 → 'AED 9.9M' | 0.5 → 'AED 500K'
    """
    if value_m >= 1:
        return f"AED {value_m:.1f}M"
    else:
        return f"AED {value_m * 1000:.0f}K"


def fmt_rental(value_aed: float) -> str:
    """
    Format a rental price stored in raw AED/yr.
    Examples: 850000 → 'AED 850K/yr' | 1200000 → 'AED 1.2M/yr'
    """
    if value_aed >= 1_000_000:
        return f"AED {value_aed / 1_000_000:.1f}M/yr"
    elif value_aed >= 1_000:
        return f"AED {value_aed / 1_000:.0f}K/yr"
    else:
        return f"AED {value_aed:.0f}/yr"


def fmt_pct(pct: float) -> str:
    """Format percentage drop. e.g. 5.882 → '5.9%'"""
    return f"{pct:.1f}%"


# ── Claude copy generation ───────────────────────────────────────────────────

def generate_hook(
    area: str,
    drop_abs: str,
    old_price: str,
    new_price: str,
    pct: str,
    total_drops: int,
    total_value: str,
) -> str:
    """
    Ask Claude for one punchy opening hook line for the main tweet.
    Falls back to a clean static line if Claude fails.
    """
    client = get_anthropic_client()

    prompt = f"""You write tweets for @DXBDips — a Dubai luxury real estate price drop tracker.
Tone: dry, data-driven, slightly dramatic. Never salesy. Never generic. No hashtags. No emojis.

Data for this scrape:
- Biggest sale drop: {drop_abs} on a property in {area} ({old_price} → {new_price}, -{pct})
- Total drops this run: {total_drops}
- Total value reduced: {total_value}

Write ONE short punchy opening line (max 12 words) that makes someone stop scrolling.
Reference the drop or area specifically. No quotes around it. Return only the line, nothing else."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip().strip('"').strip("'")
    except Exception as e:
        print(f"[Twitter] Claude hook generation failed: {e}", flush=True)
        return f"A {area} property just dropped {drop_abs}."


def generate_rental_hook(
    area: str,
    drop_abs: str,
    old_price: str,
    new_price: str,
    pct: str,
) -> str:
    """
    Ask Claude for one short opener for the rental reply tweet.
    Falls back to a static line if Claude fails.
    """
    client = get_anthropic_client()

    prompt = f"""You write tweets for @DXBDips — a Dubai luxury real estate price drop tracker.
Tone: dry, data-driven, slightly dramatic. Never salesy. No hashtags. No emojis.

Data:
- Biggest rental drop: {drop_abs}/yr on a property in {area} ({old_price} → {new_price}, -{pct})

Write ONE short line (max 10 words) that introduces this rental drop as a reply to a sale drop tweet.
Make it feel like the drops are spreading. No quotes. Return only the line, nothing else."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip().strip('"').strip("'")
    except Exception as e:
        print(f"[Twitter] Claude rental hook generation failed: {e}", flush=True)
        return "Rentals are moving too."


# ── Tweet builders ───────────────────────────────────────────────────────────

def build_sale_tweet(
    top_sale: dict,
    total_drops: int,
    total_value_dropped_aed: float,
) -> str:
    """
    Build the main sale tweet. Clean format:

    [hook]

    [Area] — [drop_abs] drop
    [old] → [new] (-pct%)

    [X] drops tracked. [total value] reduced.

    dxbdips.com
    """
    area     = top_sale.get("area") or "Dubai"
    drop_abs = fmt_aed(top_sale.get("drop_abs_aed", 0))
    old      = fmt_aed(top_sale.get("old_price_aed", 0))
    new      = fmt_aed(top_sale.get("new_price_aed", 0))
    pct      = fmt_pct(top_sale.get("drop_pct", 0))
    total_v  = fmt_aed(total_value_dropped_aed)

    hook = generate_hook(
        area=area,
        drop_abs=drop_abs,
        old_price=old,
        new_price=new,
        pct=pct,
        total_drops=total_drops,
        total_value=total_v,
    )

    tweet = (
        f"{hook}\n"
        f"\n"
        f"{area} — {drop_abs} drop\n"
        f"{old} → {new} (-{pct})\n"
        f"\n"
        f"{total_drops} drops tracked this run. {total_v} reduced.\n"
        f"\n"
        f"dxbdips.com"
    )

    return tweet


def build_rental_reply(top_rental: dict) -> str:
    """
    Build the rental reply tweet. Clean format:

    [hook]

    [Area] — [drop_abs]/yr drop
    [old]/yr → [new]/yr (-pct%)
    """
    area     = top_rental.get("area") or "Dubai"
    drop_abs = fmt_rental(top_rental.get("drop_abs_aed", 0))  # raw AED/yr
    old      = fmt_rental(top_rental.get("old_price_aed", 0))
    new      = fmt_rental(top_rental.get("new_price_aed", 0))
    pct      = fmt_pct(top_rental.get("drop_pct", 0))

    hook = generate_rental_hook(
        area=area,
        drop_abs=drop_abs,
        old_price=old,
        new_price=new,
        pct=pct,
    )

    tweet = (
        f"{hook}\n"
        f"\n"
        f"{area} — {drop_abs}/yr drop\n"
        f"{old} → {new} (-{pct})"
    )

    return tweet


# ── Posting ──────────────────────────────────────────────────────────────────

def _post_thread(sale_tweet: str, rental_tweet, client):
    """Post sale tweet, then reply with rental tweet if available."""
    try:
        response = client.create_tweet(text=sale_tweet)
        tweet_id = response.data["id"]
        print(f"[Twitter] ✅ Sale tweet posted (id={tweet_id})", flush=True)
        print(f"[Twitter] Content:\n{sale_tweet}", flush=True)

        if rental_tweet and tweet_id:
            reply = client.create_tweet(
                text=rental_tweet,
                in_reply_to_tweet_id=tweet_id,
            )
            print(f"[Twitter] ✅ Rental reply posted (id={reply.data['id']})", flush=True)
            print(f"[Twitter] Content:\n{rental_tweet}", flush=True)

    except Exception as e:
        print(f"[Twitter] ❌ Error posting: {e}", flush=True)


# ── Public entry point ───────────────────────────────────────────────────────

def post_drops(
    sale_drops: list,
    rental_drops: list,
    total_sale_listings: int = 0,
    total_rental_listings: int = 0,
):
    """
    Called by runner.py after each scrape.
    Posts one main sale tweet + optional rental reply.
    Fires in a background daemon thread so it doesn't block the runner.
    """
    print(
        f"[Twitter] post_drops() called — "
        f"{len(sale_drops)} sale drops, {len(rental_drops)} rental drops",
        flush=True,
    )

    if not os.environ.get("TWITTER_API_KEY"):
        print("[Twitter] No Twitter credentials found, skipping.", flush=True)
        return

    if not sale_drops:
        print("[Twitter] No sale drops this run — skipping tweet.", flush=True)
        return

    # Pick biggest drop by absolute AED value
    top_sale   = max(sale_drops,   key=lambda d: d.get("drop_abs_aed", 0))
    top_rental = max(rental_drops, key=lambda d: d.get("drop_abs_aed", 0)) if rental_drops else None

    # Stats for main tweet
    # Sale prices stored in millions (e.g. 2.5 = AED 2.5M)
    # Rental prices stored in raw AED/yr — different unit, don't mix them
    total_drops         = len(sale_drops) + len(rental_drops)
    total_value_dropped = sum(d.get("drop_abs_aed", 0) for d in sale_drops)  # millions

    print("[Twitter] Building tweets...", flush=True)

    sale_tweet   = build_sale_tweet(top_sale, total_drops, total_value_dropped)
    rental_tweet = build_rental_reply(top_rental) if top_rental else None

    print(f"[Twitter] Sale tweet ({len(sale_tweet)} chars):\n{sale_tweet}", flush=True)
    if rental_tweet:
        print(f"[Twitter] Rental reply ({len(rental_tweet)} chars):\n{rental_tweet}", flush=True)

    twitter_client = get_twitter_client()
    t = threading.Thread(
        target=_post_thread,
        args=(sale_tweet, rental_tweet, twitter_client),
        daemon=True,
        name="twitter-poster",
    )
    t.start()
    print(f"[Twitter] Background thread started (id={t.ident}).", flush=True)
