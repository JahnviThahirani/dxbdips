-- DXB Dips — Supabase Schema
-- Run this in Supabase SQL Editor

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Master listings table
create table if not exists listings (
  id            text primary key,
  source        text not null default 'bayut',
  type          text,
  beds          integer,
  baths         integer,
  size_sqft     real,
  title         text,
  area          text,
  building      text,
  city          text default 'Dubai',
  url           text,
  image_url     text,
  listed_date   text,
  first_seen    timestamptz not null default now(),
  last_seen     timestamptz not null default now(),
  last_price    real,
  is_active     boolean default true
);

-- Price history
create table if not exists price_history (
  id          bigserial primary key,
  listing_id  text not null references listings(id),
  price_aed   real not null,
  scraped_at  timestamptz not null default now()
);

-- Price drops
create table if not exists price_drops (
  id              bigserial primary key,
  listing_id      text not null references listings(id),
  old_price_aed   real not null,
  new_price_aed   real not null,
  drop_abs_aed    real not null,
  drop_pct        real not null,
  detected_at     timestamptz not null default now()
);

-- Scrape runs log
create table if not exists scrape_runs (
  id              bigserial primary key,
  started_at      timestamptz not null default now(),
  finished_at     timestamptz,
  source          text not null,
  listings_found  integer default 0,
  drops_detected  integer default 0,
  status          text default 'running'
);

-- Indexes for performance
create index if not exists idx_price_drops_detected_at on price_drops(detected_at desc);
create index if not exists idx_price_drops_listing_id on price_drops(listing_id);
create index if not exists idx_price_history_listing_id on price_history(listing_id);
create index if not exists idx_listings_last_seen on listings(last_seen desc);
create index if not exists idx_listings_active on listings(is_active);

-- Enable Row Level Security (read-only public access)
alter table listings enable row level security;
alter table price_history enable row level security;
alter table price_drops enable row level security;
alter table scrape_runs enable row level security;

-- Public read access
create policy "Public read listings" on listings for select using (true);
create policy "Public read price_history" on price_history for select using (true);
create policy "Public read price_drops" on price_drops for select using (true);
create policy "Public read scrape_runs" on scrape_runs for select using (true);
