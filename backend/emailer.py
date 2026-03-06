"""
emailer.py — Email alert system for DXB Dips
Uses Resend (free tier: 3,000 emails/month, 100/day)
Called from runner.py after each scrape run via send_alerts()
Mirrors the background-thread pattern used in twitter.py
"""
import os
import threading
import httpx
from backend.db import get_client, _with_retry

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "DXB Dips <alerts@dxbdips.com>"
SITE_URL = "https://dxbdips.com"


# ─── Supabase helpers ──────────────────────────────────────────────────────────

def get_confirmed_subscribers() -> list[dict]:
    """Fetch all confirmed subscribers from Supabase."""
    db = get_client(use_service_key=True)
    result = _with_retry(lambda: db.table("email_subscribers")
                         .select("*")
                         .eq("confirmed", True)
                         .execute())
    return result.data or []


def filter_drops_for_subscriber(drops: list[dict], subscriber: dict) -> list[dict]:
    """Apply per-subscriber preferences to a drop list."""
    min_pct   = subscriber.get("min_drop_pct") or 0
    prop_type = subscriber.get("property_type")  # "apartment" | "villa" | None = all

    filtered = []
    for d in drops:
        if d.get("drop_pct", 0) < min_pct:
            continue
        if prop_type and d.get("type", "").lower() != prop_type.lower():
            continue
        filtered.append(d)
    return filtered


def should_send_listing_type(listing_type: str | None, is_rental: bool) -> bool:
    """
    Check if a subscriber's listing_type preference includes this drop type.
    "both" or None = send everything; "sale" = sale only; "rental" = rental only.
    """
    if not listing_type or listing_type == "both":
        return True
    if listing_type == "rental":
        return is_rental
    if listing_type == "sale":
        return not is_rental
    return True


# ─── Email template ────────────────────────────────────────────────────────────

def _drop_card_html(drop: dict, is_rental: bool = False) -> str:
    title     = drop.get("title") or "Property"
    area      = drop.get("area") or ""
    building  = drop.get("building") or ""
    beds      = drop.get("beds")
    size      = drop.get("size_sqft")
    drop_pct  = drop.get("drop_pct", 0)
    old_price = drop.get("old_price_aed", 0)
    new_price = drop.get("new_price_aed", 0)
    drop_abs  = drop.get("drop_abs_aed", 0)
    url       = drop.get("url") or SITE_URL

    subtitle_parts = []
    if beds is not None:
        subtitle_parts.append("Studio" if beds == 0 else f"{beds} BR")
    if area:
        subtitle_parts.append(area)
    if building:
        subtitle_parts.append(building)
    subtitle = " · ".join(subtitle_parts)

    if is_rental:
        old_fmt   = f"AED {old_price:,.0f}/yr"
        new_fmt   = f"AED {new_price:,.0f}/yr"
        saved_fmt = f"AED {drop_abs:,.0f}/yr"
    else:
        old_fmt   = f"AED {old_price:.2f}M"
        new_fmt   = f"AED {new_price:.2f}M"
        saved_fmt = f"AED {drop_abs:.2f}M"

    size_html = (
        f'<span style="color:#9ca3af;font-size:12px;margin-top:2px;display:block;">'
        f'{size:,.0f} sqft</span>'
    ) if size else ""

    return f"""
<div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:18px 20px;margin-bottom:12px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
    <div style="flex:1;min-width:0;">
      <div style="font-weight:700;font-size:14px;color:#111827;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{title}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:3px;">{subtitle}</div>
      {size_html}
    </div>
    <div style="background:#7c3aed;color:#ffffff;border-radius:20px;padding:4px 11px;font-size:13px;font-weight:800;white-space:nowrap;flex-shrink:0;">
      -{drop_pct}%
    </div>
  </div>
  <div style="display:flex;gap:20px;margin-top:14px;">
    <div>
      <div style="font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px;">Was</div>
      <div style="font-size:13px;color:#9ca3af;text-decoration:line-through;">{old_fmt}</div>
    </div>
    <div>
      <div style="font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px;">Now</div>
      <div style="font-size:15px;font-weight:800;color:#111827;">{new_fmt}</div>
    </div>
    <div>
      <div style="font-size:10px;color:#9ca3af;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:2px;">Saving</div>
      <div style="font-size:13px;font-weight:700;color:#16a34a;">{saved_fmt}</div>
    </div>
  </div>
  <a href="{url}" style="display:inline-block;margin-top:13px;font-size:12px;color:#7c3aed;text-decoration:none;font-weight:600;">View listing →</a>
</div>"""


def build_email_html(sale_drops: list[dict], rental_drops: list[dict]) -> str:
    total = len(sale_drops) + len(rental_drops)

    sale_section = ""
    if sale_drops:
        cards = "".join(_drop_card_html(d, is_rental=False) for d in sale_drops[:10])
        sale_section = f"""
<h2 style="font-size:15px;font-weight:700;color:#111827;margin:28px 0 12px 0;">
  🏠 Sale Price Drops <span style="color:#7c3aed;">({len(sale_drops)})</span>
</h2>
{cards}"""

    rental_section = ""
    if rental_drops:
        cards = "".join(_drop_card_html(d, is_rental=True) for d in rental_drops[:10])
        rental_section = f"""
<h2 style="font-size:15px;font-weight:700;color:#111827;margin:28px 0 12px 0;">
  🔑 Rental Price Drops <span style="color:#7c3aed;">({len(rental_drops)})</span>
</h2>
{cards}"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>DXB Dips — New Price Drops</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:560px;margin:0 auto;padding:32px 16px;">

    <!-- Header -->
    <div style="text-align:center;margin-bottom:24px;">
      <div style="font-size:28px;font-weight:900;color:#7c3aed;letter-spacing:-1px;">DXB Dips</div>
      <div style="font-size:12px;color:#9ca3af;margin-top:5px;text-transform:uppercase;letter-spacing:0.8px;">Dubai Luxury Real Estate · Price Drop Tracker</div>
    </div>

    <!-- Hero banner -->
    <div style="background:linear-gradient(135deg,#6d28d9 0%,#7c3aed 50%,#8b5cf6 100%);border-radius:16px;padding:28px 24px;text-align:center;margin-bottom:8px;">
      <div style="font-size:48px;font-weight:900;color:#ffffff;line-height:1;">{total}</div>
      <div style="font-size:15px;color:rgba(255,255,255,0.85);margin-top:6px;font-weight:500;">new price drop{"s" if total != 1 else ""} detected</div>
      <a href="{SITE_URL}" style="display:inline-block;margin-top:18px;background:#ffffff;color:#7c3aed;padding:11px 28px;border-radius:8px;font-weight:700;font-size:14px;text-decoration:none;">
        View all on DXB Dips →
      </a>
    </div>

    {sale_section}
    {rental_section}

    <!-- Footer -->
    <div style="text-align:center;margin-top:36px;padding-top:20px;border-top:1px solid #e5e7eb;">
      <p style="font-size:12px;color:#9ca3af;margin:0;line-height:1.6;">
        You're receiving this because you subscribed to DXB Dips price alerts.<br>
        <a href="{SITE_URL}" style="color:#7c3aed;text-decoration:none;font-weight:600;">dxbdips.com</a>
      </p>
    </div>

  </div>
</body>
</html>"""


def build_email_text(sale_drops: list[dict], rental_drops: list[dict]) -> str:
    """Plain-text fallback."""
    total = len(sale_drops) + len(rental_drops)
    lines = [
        f"DXB DIPS — {total} New Price Drop{'s' if total != 1 else ''} Detected",
        f"View all at {SITE_URL}",
        "",
    ]
    if sale_drops:
        lines += [f"SALE DROPS ({len(sale_drops)})", "=" * 40]
        for d in sale_drops[:10]:
            beds_str = f"{d.get('beds')} BR · " if d.get("beds") is not None else ""
            lines += [
                d.get("title", "Property"),
                f"  {beds_str}{d.get('area', '')}",
                f"  AED {d['old_price_aed']:.2f}M → {d['new_price_aed']:.2f}M  (-{d['drop_pct']}%)",
                f"  Saving: AED {d['drop_abs_aed']:.2f}M",
                f"  {d.get('url', SITE_URL)}",
                "",
            ]
    if rental_drops:
        lines += [f"RENTAL DROPS ({len(rental_drops)})", "=" * 40]
        for d in rental_drops[:10]:
            beds_str = f"{d.get('beds')} BR · " if d.get("beds") is not None else ""
            lines += [
                d.get("title", "Property"),
                f"  {beds_str}{d.get('area', '')}",
                f"  AED {d['old_price_aed']:,.0f} → {d['new_price_aed']:,.0f}/yr  (-{d['drop_pct']}%)",
                f"  Saving: AED {d['drop_abs_aed']:,.0f}/yr",
                f"  {d.get('url', SITE_URL)}",
                "",
            ]
    lines += ["--", f"DXB Dips · {SITE_URL}"]
    return "\n".join(lines)


# ─── Resend API ────────────────────────────────────────────────────────────────

def _send_via_resend(to: str, subject: str, html: str, text: str) -> bool:
    """POST a single email via Resend REST API. Returns True on success."""
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"from": FROM_EMAIL, "to": [to], "subject": subject, "html": html, "text": text},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return True
        print(f"  [Email] Resend error {resp.status_code}: {resp.text[:200]}", flush=True)
        return False
    except Exception as e:
        print(f"  [Email] Request failed to {to}: {e}", flush=True)
        return False


# ─── Background sender (mirrors twitter.py) ────────────────────────────────────

def _send_alerts_background(sale_drops: list[dict], rental_drops: list[dict]) -> None:
    """Runs in a daemon thread — sends one personalised digest per subscriber."""
    subscribers = get_confirmed_subscribers()
    if not subscribers:
        print("[Email] No confirmed subscribers.", flush=True)
        return

    total_drops = len(sale_drops) + len(rental_drops)
    subject = f"🏙️ {total_drops} new Dubai price drop{'s' if total_drops != 1 else ''} detected"
    sent = skipped = failed = 0

    for sub in subscribers:
        email = sub.get("email")
        if not email:
            continue

        lt = sub.get("listing_type")  # "both" | "sale" | "rental" | None
        f_sale   = filter_drops_for_subscriber(sale_drops, sub)   if should_send_listing_type(lt, is_rental=False) else []
        f_rental = filter_drops_for_subscriber(rental_drops, sub) if should_send_listing_type(lt, is_rental=True)  else []

        if not f_sale and not f_rental:
            skipped += 1
            print(f"  [Email] Skipped {email} — no drops matched their filters", flush=True)
            continue

        ok = _send_via_resend(
            email, subject,
            build_email_html(f_sale, f_rental),
            build_email_text(f_sale, f_rental),
        )
        if ok:
            sent += 1
            print(f"  ✉️  Sent → {email}  ({len(f_sale)} sale, {len(f_rental)} rental)", flush=True)
        else:
            failed += 1

    print(f"[Email] Done — {sent} sent, {skipped} skipped (filters), {failed} failed", flush=True)


# ─── Public entry point ────────────────────────────────────────────────────────

def send_alerts(sale_drops: list[dict], rental_drops: list[dict]) -> None:
    """
    Send email digest to all confirmed subscribers.
    Called from runner.py after each scrape run — same pattern as post_drops().
    Fires in a background daemon thread so runner.py is never blocked.
    """
    total = len(sale_drops) + len(rental_drops)
    print(
        f"\n[Email] send_alerts() called — "
        f"{len(sale_drops)} sale drops, {len(rental_drops)} rental drops",
        flush=True,
    )

    if total == 0:
        print("[Email] No drops this run — skipping.", flush=True)
        return

    if not RESEND_API_KEY:
        print("[Email] RESEND_API_KEY not set — skipping.", flush=True)
        return

    t = threading.Thread(
        target=_send_alerts_background,
        args=(sale_drops, rental_drops),
        daemon=True,
        name="email-alerts",
    )
    t.start()
    print(f"[Email] Background thread started (id={t.ident}). Runner continuing...", flush=True)
