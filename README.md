# 📉 DXB Dips

> Real-time price drop tracker for Dubai luxury real estate.  
> Monitors 10,000+ listings on Property Finder every 6 hours and surfaces meaningful price reductions.

**Live:** [dxbdips.vercel.app](https://dxbdips.vercel.app)

---

## What It Does

DXB Dips scrapes Property Finder every 6 hours, compares new prices against stored historical prices, and surfaces any property that dropped in price. Users can filter by property type, price bracket, time window (24h / 7d / 30d), and drop size. Clicking a listing opens a modal with a full SVG price history chart and a direct link to the Property Finder listing.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DXB DIPS STACK                           │
├──────────────────┬────────────────────┬─────────────────────────┤
│   DATA LAYER     │   API LAYER        │   FRONTEND LAYER        │
│                  │                    │                         │
│  GitHub Actions  │  FastAPI           │  React + Vite           │
│  (cron, free)    │  (Railway)         │  (Vercel)               │
│       ↓          │       ↓            │       ↓                 │
│  PF Scraper      │  /api/drops        │  Drop Feed              │
│  (httpx +        │  /api/stats        │  Price History Modal    │
│   __NEXT_DATA__) │  /api/history      │  Area Analytics         │
│       ↓          │  /api/trigger-     │  Filters & Sort         │
│  Supabase        │    scrape          │  USD / AED Toggle       │
│  (Postgres)      │       ↑            │  24h / 7d / 30d         │
│                  │  reads Supabase    │                         │
└──────────────────┴────────────────────┴─────────────────────────┘
```

### Data Flow

1. **GitHub Actions** triggers every 6 hours → POSTs to `/api/trigger-scrape` on Railway
2. **Railway API** spawns the scraper as a background async task
3. **Scraper** fetches Property Finder search pages, extracts `__NEXT_DATA__` JSON (no browser needed)
4. Each listing is **upserted** into Supabase — if price dropped vs last known, a `price_drop` row is written
5. **FastAPI on Railway** serves `/api/drops`, `/api/stats`, `/api/history/{id}` by reading from Supabase
6. **React on Vercel** fetches from the API, renders the drop feed with filters, auto-refreshes every 5 minutes

---

## Project Structure

```
dxbdips/
├── .github/
│   └── workflows/
│       └── scrape.yml          ← GitHub Actions cron (triggers Railway every 6h)
├── backend/
│   ├── main.py                 ← FastAPI app (Railway)
│   ├── db.py                   ← Supabase client + all DB operations
│   └── schema.sql              ← Run once in Supabase SQL editor
├── scraper/
│   ├── scraper_pf.py           ← Property Finder __NEXT_DATA__ scraper
│   └── runner.py               ← Orchestrator (called by /api/trigger-scrape)
├── frontend/
│   ├── src/
│   │   ├── App.jsx             ← Root component, state management
│   │   ├── index.css           ← Global styles (Playfair Display + Manrope)
│   │   ├── components/
│   │   │   ├── Header.jsx      ← Logo, last scan badge, time/currency toggles
│   │   │   ├── StatBar.jsx     ← 4 stat cards (biggest drop, total value etc)
│   │   │   ├── FilterBar.jsx   ← Type filters, sort dropdown
│   │   │   ├── DropFeed.jsx    ← List of drop cards + skeleton loading
│   │   │   ├── AreaAnalytics.jsx ← Area-level drop breakdown
│   │   │   └── HistoryModal.jsx← Click-through modal with SVG price chart
│   │   └── lib/
│   │       └── utils.js        ← formatPrice, formatDrop, timeAgo helpers
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── vercel.json
├── requirements.txt
└── README.md
```

---

## Database Schema (Supabase / Postgres)

### `listings`
One row per unique Property Finder listing ID. Updated on every scrape.

| Column | Type | Description |
|--------|------|-------------|
| id | text PK | `pf_{listing_id}` |
| source | text | `propertyfinder` |
| type | text | apartment / villa / penthouse / townhouse |
| beds / baths | integer | bedroom/bathroom count |
| size_sqft | real | area in sqft |
| title | text | listing title |
| area | text | neighbourhood path (e.g. "Dubai, Jumeirah, La Mer") |
| building | text | building/community name |
| url | text | full Property Finder listing URL |
| image_url | text | cover photo URL |
| last_price | real | most recent price in AED millions |
| first_seen | timestamptz | when we first discovered this listing |
| last_seen | timestamptz | last time we saw it active |
| is_active | boolean | false if listing disappeared |

### `price_history`
One row per scrape per listing. Enables the price chart.

| Column | Type | Description |
|--------|------|-------------|
| listing_id | text FK | references listings.id |
| price_aed | real | price in AED millions at time of scrape |
| scraped_at | timestamptz | when this price was recorded |

### `price_drops`
Written only when `new_price < old_price`. Feeds the drop feed.

| Column | Type | Description |
|--------|------|-------------|
| listing_id | text FK | references listings.id |
| old_price_aed | real | previous price (millions AED) |
| new_price_aed | real | new lower price (millions AED) |
| drop_abs_aed | real | absolute drop (millions AED) |
| drop_pct | real | percentage dropped |
| detected_at | timestamptz | when drop was detected |

### `scrape_runs`
Audit log of every scrape run.

| Column | Type | Description |
|--------|------|-------------|
| source | text | `propertyfinder` |
| started_at | timestamptz | scrape start time |
| finished_at | timestamptz | scrape end time (NULL if still running) |
| listings_found | integer | total listings processed |
| drops_detected | integer | price drops found this run |
| status | text | `running` / `done` / `error` |

---

## Scraper Details

**Source:** Property Finder via embedded `__NEXT_DATA__` JSON

Property Finder renders its search results server-side using Next.js and embeds the full listing data as a JSON blob in the HTML. This means:
- No browser automation, no Playwright, no Chromium
- Pure `httpx` HTML fetch + regex extraction of `__NEXT_DATA__`
- Fast, lightweight, and reliable

**Search parameters:**
- `c=1` — for sale only
- `rp=y` — price reduced listings (prioritises motivated sellers)
- `ob=mr` — sorted by most recent
- Up to 500 pages × ~20 listings = ~10,000 listings per run
- 2.5 second delay between pages (polite crawling)

**Drop detection logic:**
```python
if new_price < last_known_price:
    drop_abs = last_known_price - new_price
    drop_pct = (drop_abs / last_known_price) * 100
    → write to price_drops table
    → update price_history table
```

**Important:** The first scrape establishes the baseline only. Price drops are detected from the second scrape onwards when the same listing ID appears with a lower price.

**Drop tiers:**
- 🔴 High — 10%+ drop
- 🟠 Medium — 5–10% drop  
- ⚪ Low — under 5% drop

---

## Automated Scraping

Scraping is triggered via GitHub Actions → Railway API (not directly from GitHub Actions), which avoids needing Python/Supabase credentials in GitHub and keeps the scrape logic server-side.

**scrape.yml flow:**
```
GitHub Actions cron (every 6h)
  → POST /api/trigger-scrape?pages=500&secret=***
    → Railway spawns async background task
      → scraper_pf.py runs 500 pages
        → upserts to Supabase
          → logs to scrape_runs table
```

**Scheduled times (UTC):** 00:00, 06:00, 12:00, 18:00  
**Dubai time:** 04:00, 10:00, 16:00, 22:00

---

## Setup & Deployment

### Step 1 — Supabase

1. Go to [supabase.com](https://supabase.com) → create project `dxbdips`
2. Go to **SQL Editor** → paste and run `backend/schema.sql`
3. Go to **Settings → API** → copy:
   - Project URL
   - `service_role` key (keep private — used for writes)

### Step 2 — Railway (Backend)

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Select your repo, set root to `/`
3. Add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `SCRAPE_SECRET` (any secret string, e.g. `dxbdips-scrape-2026`)
4. Deploy → copy the Railway URL (e.g. `https://dxbdips-api-production.up.railway.app`)

### Step 3 — GitHub Secrets

Go to **GitHub repo → Settings → Secrets → Actions** and add:

| Secret | Value |
|--------|-------|
| `API_URL` | Your Railway URL |
| `SCRAPE_SECRET` | Same secret as Railway env var |

### Step 4 — Run First Scrape

Go to **GitHub → Actions → Scrape Property Finder → Run workflow**

This builds the baseline (~10,000 listings). The second run (6 hours later) will start detecting drops.

To run locally:
```bash
pip install -r requirements.txt
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_SERVICE_KEY=eyJ...
python scraper/runner.py --pages 10
```

### Step 5 — Vercel (Frontend)

1. Go to [vercel.com](https://vercel.com) → New Project → Import GitHub repo
2. Set **Root Directory** to `frontend`
3. Add environment variable:
   - `VITE_API_URL` = your Railway URL
4. Deploy → live at `*.vercel.app`

---

## Local Development

```bash
# Terminal 1 — Backend
pip install -r requirements.txt
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_SERVICE_KEY=eyJ...
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Frontend Features

- **Light theme** — Airbnb/Notion-inspired design (Playfair Display + Manrope)
- **Last scan badge** — shows when data was last updated + countdown to next scan
- **Property images** — loads from Property Finder CDN with emoji fallback
- **View on Property Finder** — direct link appears on card hover
- **Price history modal** — SVG chart built from scratch, no chart library
- **Area Analytics tab** — breakdown of drops by neighbourhood
- **Responsive** — works on mobile, tablet, desktop
- **Skeleton loading** — smooth loading states matching card layout
- **Time windows** — 24h / 7D / 30D toggle
- **Currency toggle** — AED / USD (live conversion)
- **Filters** — by property type, price bracket, drop size

---

## Costs

| Service | Plan | Cost |
|---------|------|------|
| Supabase | Free | $0 |
| Railway | Hobby | ~$5/month |
| Vercel | Free | $0 |
| GitHub Actions | Free | $0 (2,000 min/month) |
| **Total** | | **~$5/month** |

---

## Design

- **Fonts:** Playfair Display (headings) + Manrope (body/data)
- **Palette:** Warm off-white (`#f8f7f5`) + crimson red (`#c0392b`) for drops
- **Key UI decisions:**
  - Left border colour on each card indicates drop severity (red = high, orange = medium, gray = low)
  - SVG price chart built from scratch — no chart library dependency
  - Drop markers on chart show exactly when each price cut happened
  - "View on Property Finder ↗" link fades in on card hover only
  - Last scan dot pulses green when fresh (<30 min), turns gray when stale
