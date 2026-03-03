# 📉 Dubai Dips (dxbdips.com)

> Real-time price drop tracker for Dubai real estate.
> Monitors 2M+ AED properties on Bayut every 6 hours and surfaces meaningful price drops.

---

## What It Does

Dubai Dips scrapes Bayut.com every 6 hours, compares new prices against stored historical prices, and surfaces any property that dropped in price. Users can filter by property type, time window (24h / 7d / 30d), and drop size. Clicking a listing opens a modal with a full SVG price history chart.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DUBAI DIPS STACK                        │
├──────────────────┬──────────────────┬───────────────────────┤
│   DATA LAYER     │   API LAYER      │   FRONTEND LAYER      │
│                  │                  │                        │
│  GitHub Actions  │  FastAPI         │  React + Vite         │
│  (cron, free)    │  (Render, free)  │  (Vercel, free)       │
│       ↓          │       ↓          │       ↓               │
│  Bayut Scraper   │  /api/drops      │  Drop Feed            │
│  (httpx/Algolia) │  /api/stats      │  Price History Modal  │
│       ↓          │  /api/history    │  Filters & Sort       │
│  Supabase        │       ↑          │  USD / AED Toggle     │
│  (Postgres, free)│  reads Supabase  │  24h / 7d / 30d       │
└──────────────────┴──────────────────┴───────────────────────┘
```

### Data Flow

1. **GitHub Actions** triggers every 6 hours → runs `scraper/runner.py`
2. **Scraper** hits Bayut's internal Algolia API (no browser needed, pure JSON)
3. Each listing is **upserted** into Supabase — if price dropped vs last known, a `price_drop` row is written
4. **FastAPI on Render** serves `/api/drops`, `/api/stats`, `/api/history/{id}` by reading from Supabase
5. **React on Vercel** fetches from the API, renders the drop feed with filters, auto-refreshes every 5 minutes

---

## Project Structure

```
dxbdips/
├── .github/
│   └── workflows/
│       └── scrape.yml          ← GitHub Actions cron job
├── backend/
│   ├── main.py                 ← FastAPI app (Render)
│   ├── db.py                   ← Supabase client + all DB operations
│   └── schema.sql              ← Run once in Supabase SQL editor
├── scraper/
│   ├── scraper_bayut.py        ← Bayut Algolia API scraper
│   └── runner.py               ← Orchestrator (called by GitHub Actions)
├── frontend/
│   ├── src/
│   │   ├── App.jsx             ← Root component, state management
│   │   ├── index.css           ← Global styles (Syne + DM Mono fonts)
│   │   ├── components/
│   │   │   ├── Header.jsx      ← Logo, live stats, time/currency toggles
│   │   │   ├── StatBar.jsx     ← 4 stat cards (biggest drop, total value etc)
│   │   │   ├── FilterBar.jsx   ← Type filters, sort dropdown
│   │   │   ├── DropFeed.jsx    ← List of drop cards + skeleton loading
│   │   │   └── HistoryModal.jsx← Click-through modal with SVG price chart
│   │   └── lib/
│   │       └── utils.js        ← formatPrice, formatDrop, timeAgo helpers
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── vercel.json
├── requirements.txt
├── render.yaml                 ← Render deployment config
└── README.md
```

---

## Database Schema (Supabase / Postgres)

### `listings`
Stores one row per unique Bayut listing ID. Updated on every scrape.

| Column | Type | Description |
|--------|------|-------------|
| id | text PK | `by_{externalID}` |
| source | text | `bayut` |
| type | text | apartment / villa / penthouse / townhouse |
| beds / baths | integer | bedroom/bathroom count |
| size_sqft | real | area in sqft |
| title | text | listing title |
| area | text | neighbourhood |
| building | text | building/community name |
| url | text | full Bayut listing URL |
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
| source | text | `bayut` |
| started_at | timestamptz | scrape start time |
| finished_at | timestamptz | scrape end time |
| listings_found | integer | total listings processed |
| drops_detected | integer | price drops found this run |
| status | text | `running` / `done` / `error` |

---

## Setup & Deployment

### Step 1 — Supabase

1. Go to [supabase.com](https://supabase.com) → create project `dxbdips`
2. Go to **SQL Editor** → paste and run `backend/schema.sql`
3. Go to **Settings → API** → copy:
   - Project URL
   - `anon` public key
   - `service_role` key (keep private — used for writes)

### Step 2 — GitHub Repository

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create dxbdips --public
git push -u origin main
```

Add these **repository secrets** (Settings → Secrets → Actions):
- `SUPABASE_URL` — your project URL
- `SUPABASE_SERVICE_KEY` — your service_role key (for writes)

### Step 3 — Run First Scrape

Go to GitHub → Actions → **DXB Dips Scraper** → **Run workflow**

This builds the baseline. The second run (6 hours later) will start detecting drops.

To run locally:
```bash
pip install -r requirements.txt
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_SERVICE_KEY=eyJ...
python scraper/runner.py --pages 5
```

### Step 4 — Deploy Backend to Render

1. Go to [render.com](https://render.com) → New Web Service
2. Connect your GitHub repo
3. Render will auto-detect `render.yaml`
4. Add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_KEY`
5. Deploy → copy the URL (e.g. `https://dxbdips-api.onrender.com`)

### Step 5 — Deploy Frontend to Vercel

1. Go to [vercel.com](https://vercel.com) → New Project
2. Import your GitHub repo
3. Set **Root Directory** to `frontend`
4. Add environment variable:
   - `VITE_API_URL` = your Render URL (e.g. `https://dxbdips-api.onrender.com`)
5. Deploy → your site is live at `*.vercel.app`
6. Add custom domain `dxbdips.com` in Vercel settings

---

## Local Development

```bash
# Terminal 1 — Backend
pip install -r requirements.txt
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_ANON_KEY=eyJ...
python backend/main.py

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Scraper Details

**Source:** Bayut.com via their internal Algolia search API
- No browser, no Playwright, no Chromium
- Pure `httpx` JSON calls — ~0.3s per page vs ~4s with a browser
- Algolia app ID: `5BNAR5PY6Y` (reverse engineered from browser network tab)
- Filters: Dubai, for-sale, price ≥ 2,000,000 AED
- Pages: up to 50 pages × 24 results = ~1,200 listings per run
- Rate limiting: 300–800ms between pages (polite)

**Drop detection logic:**
```
if new_price < old_price:
    drop_abs = old_price - new_price
    drop_pct = (drop_abs / old_price) * 100
    → write to price_drops
```

Note: First scrape establishes baseline only. Drops appear from the second scrape onwards.

---

## Costs

| Service | Plan | Cost |
|---------|------|------|
| Supabase | Free | $0 |
| Render | Free | $0 (spins down after 15min inactivity) |
| Vercel | Free | $0 |
| GitHub Actions | Free | $0 (2000 min/month) |
| Domain (dxbdips.com) | — | ~$12/year |
| **Total** | | **~$12/year** |

> Note: Render free tier spins down after 15 minutes of inactivity. First API request after idle may take ~30 seconds. Upgrade to $7/month to keep it always-on.

---

## Adding PropertyFinder Later (v2)

The architecture supports multiple sources. To add PropertyFinder:
1. Create `scraper/scraper_propertyfinder.py`
2. Add `source = 'propertyfinder'` to listings
3. Update `runner.py` to call both scrapers
4. Frontend already has source filter UI ready

---

## Design

- **Fonts:** Syne (display) + DM Mono (data/numbers)
- **Palette:** Deep black (`#080810`) + purple spectrum + neon red for drops
- **Key UI decisions:**
  - Left border color on each card indicates drop severity (red = 10%+, amber = 5%+, purple = <5%)
  - SVG price chart built from scratch — no chart library dependency
  - Drop markers on chart show exactly when each price cut happened
  - Skeleton loading states match card layout exactly
