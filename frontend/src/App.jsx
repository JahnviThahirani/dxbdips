import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import StatBar from "./components/StatBar";
import DropFeed from "./components/DropFeed";
import AreaAnalytics from "./components/AreaAnalytics";
import HistoryModal from "./components/HistoryModal";
import FloatingAlertButton from "./FloatingAlertButton";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TIME_WINDOWS = [
  { label: "24H", hours: 24 },
  { label: "7D", hours: 168 },
  { label: "30D", hours: 720 },
];

const SALE_PRICE_TIERS = [
  { id: "all",     label: "All",       min: 0,  max: Infinity },
  { id: "4to10m",  label: "4M – 10M",  min: 4,  max: 10 },
  { id: "10to20m", label: "10M – 20M", min: 10, max: 20 },
  { id: "20mplus", label: "20M+",      min: 20, max: Infinity },
];

// Rental tiers in raw AED/yr (not millions)
const RENTAL_PRICE_TIERS = [
  { id: "all",       label: "All",              min: 0,      max: Infinity },
  { id: "250to500k", label: "250K – 500K /yr",  min: 250000, max: 500000 },
  { id: "500to1m",   label: "500K – 1M /yr",    min: 500000, max: 1000000 },
  { id: "1mplus",    label: "1M+ /yr",          min: 1000000, max: Infinity },
];

const PROP_FILTERS = [
  { id: "all",       label: "All" },
  { id: "apartment", label: "Apartments" },
  { id: "villa",     label: "Villas" },
  { id: "penthouse", label: "Penthouses" },
  { id: "townhouse", label: "Townhouses" },
  { id: "10plus",    label: "10%+ Drop" },
  { id: "today",     label: "New Today" },
];

const SORTS = [
  { id: "abs",    label: "Biggest Value Drop" },
  { id: "pct",    label: "Biggest % Drop" },
  { id: "recent", label: "Most Recent" },
  { id: "price",  label: "Lowest Price" },
];

export default function App() {
  const [mode, setMode] = useState("sale"); // "sale" | "rental"
  const [drops, setDrops] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currency, setCurrency] = useState("AED");
  const [timeWindow, setTimeWindow] = useState(TIME_WINDOWS[2]);
  const [activeTier, setActiveTier] = useState("all");
  const [propFilter, setPropFilter] = useState("all");
  const [sort, setSort] = useState("abs");
  const [showAreas, setShowAreas] = useState(false);
  const [selectedListing, setSelectedListing] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const isRental = mode === "rental";
  const PRICE_TIERS = isRental ? RENTAL_PRICE_TIERS : SALE_PRICE_TIERS;

  const fetchData = useCallback(async (signal) => {
    try {
      setLoading(true);
      setError(null);
      const dropsEndpoint = isRental ? "rental-drops" : "drops";
      const statsEndpoint = isRental ? "rental-stats" : "stats";
      const [dropsRes, statsRes] = await Promise.all([
        fetch(`${API}/api/${dropsEndpoint}?hours=${timeWindow.hours}&limit=1000&sort=${sort}`, { signal }),
        fetch(`${API}/api/${statsEndpoint}?hours=${timeWindow.hours}`, { signal }),
      ]);
      if (!dropsRes.ok || !statsRes.ok) throw new Error("API error");
      const dropsData = await dropsRes.json();
      const statsData = await statsRes.json();
      setDrops(dropsData.drops || []);
      setStats(statsData);
    } catch (e) {
      if (e.name === "AbortError") return; // stale fetch cancelled, ignore
      // If we have existing data, silently keep it — no disruption to the user
      // Only show the hard error on first load when there's nothing to show
      setDrops(prev => {
        if (prev.length === 0) setError(e.message);
        return prev;
      });
    } finally {
      setLoading(false);
    }
  }, [timeWindow.hours, sort, isRental]);

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [fetchData]);
  useEffect(() => {
    const id = setInterval(() => {
      const controller = new AbortController();
      fetchData(controller.signal);
    }, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchData]);

  const handleRefresh = () => {
    const controller = new AbortController();
    fetchData(controller.signal);
  };

  const resetToHome = () => {
    setShowAreas(false);
    setActiveTier("all");
    setPropFilter("all");
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    setActiveTier("all");
    setPropFilter("all");
    setShowAreas(false);
    setDrops([]);
    setError(null);
    setStats({});
  };

  const openHistory = async (listing) => {
    setSelectedListing(listing);
    setHistoryLoading(true);
    try {
      const endpoint = isRental ? "rental-history" : "history";
      const res = await fetch(`${API}/api/${endpoint}/${listing.listing_id}`);
      const data = await res.json();
      setHistoryData(data);
    } catch (e) {
      setHistoryData(null);
    } finally {
      setHistoryLoading(false);
    }
  };

  const tier = PRICE_TIERS.find(t => t.id === activeTier);

  const tierFiltered = drops.filter(d => {
    const p = isRental
      ? (d.new_price_aed || 0)           // raw AED/yr for rentals
      : ((d.new_price_aed || 0));         // millions for sales
    return p >= tier.min && p < tier.max;
  });

  const filteredDrops = tierFiltered.filter(d => {
    if (propFilter === "all") return true;
    if (propFilter === "10plus") return d.drop_pct >= 10;
    if (propFilter === "today") {
      const detected = new Date(d.detected_at);
      const now = new Date();
      return (now - detected) <= 24 * 60 * 60 * 1000;
    }
    return d.type?.toLowerCase() === propFilter;
  });

  const tierCounts = PRICE_TIERS.reduce((acc, t) => {
    acc[t.id] = drops.filter(d => {
      const p = isRental ? (d.new_price_aed || 0) : (d.new_price_aed || 0);
      return p >= t.min && p < t.max;
    }).length;
    return acc;
  }, {});

  return (
    <div className="app">
      <div className="grain" />
      <Header
        stats={stats}
        currency={currency}
        setCurrency={setCurrency}
        timeWindow={timeWindow}
        setTimeWindow={setTimeWindow}
        timeWindows={TIME_WINDOWS}
        onRefresh={handleRefresh}
        loading={loading}
        onLogoClick={resetToHome}
      />

      {/* Buy / Rent Toggle */}
      <div className="mode-toggle-bar">
        <div className="mode-toggle">
          <button
            className={`mode-btn ${mode === "sale" ? "active" : ""}`}
            onClick={() => handleModeChange("sale")}
          >
            🏠 Buy
          </button>
          <button
            className={`mode-btn ${mode === "rental" ? "active" : ""}`}
            onClick={() => handleModeChange("rental")}
          >
            🔑 Rent
          </button>
        </div>
        <span className="mode-label">
          {isRental ? "Luxury rentals · 250K+ AED/yr · price drop tracker" : "Luxury sales · 4M+ AED · price drop tracker"}
        </span>
      </div>

      <StatBar stats={stats} drops={drops} currency={currency} isRental={isRental} />

      <nav className="tab-nav">
        <div className="tab-nav-row1">
          {PRICE_TIERS.map(t => (
            <button
              key={t.id}
              className={`tab-btn ${activeTier === t.id && !showAreas ? "active" : ""}`}
              onClick={() => { setActiveTier(t.id); setShowAreas(false); }}
            >
              <span className="tab-label">{t.label}</span>
              {tierCounts[t.id] > 0 && <span className="tab-count">{tierCounts[t.id]}</span>}
            </button>
          ))}
          {/* Area Analytics visible inline on desktop */}
          <button
            className={`tab-btn area-tab desktop-area-tab ${showAreas ? "active" : ""}`}
            onClick={() => setShowAreas(true)}
          >
            <span className="tab-label">Area Analytics</span>
          </button>
        </div>
        {/* Area Analytics on its own centered row on mobile */}
        <div className="tab-nav-row2">
          <button
            className={`tab-btn area-tab ${showAreas ? "active" : ""}`}
            onClick={() => setShowAreas(true)}
          >
            <span className="tab-label">Area Analytics</span>
          </button>
        </div>
      </nav>

      {!showAreas && (
        <>
          <div className="filterbar">
            <div className="filterbar-left">
              {PROP_FILTERS.map(f => (
                <button
                  key={f.id}
                  className={`filter-chip ${propFilter === f.id ? "active" : ""}`}
                  onClick={() => setPropFilter(f.id)}
                >{f.label}</button>
              ))}
            </div>
            <div className="filterbar-right">
              <span className="result-count">{filteredDrops.length} drops</span>
              <select className="sort-select" value={sort} onChange={e => setSort(e.target.value)}>
                {SORTS.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
              </select>
            </div>
          </div>
          <DropFeed
            drops={filteredDrops}
            currency={currency}
            loading={loading}
            error={error}
            onCardClick={openHistory}
            isRental={isRental}
            totalRentalDropsEver={isRental ? (stats.total_drops ?? -1) : null}
          />
        </>
      )}

      {showAreas && <AreaAnalytics drops={drops} currency={currency} loading={loading} isRental={isRental} />}

      {selectedListing && (
        <HistoryModal
          listing={selectedListing}
          historyData={historyData}
          loading={historyLoading}
          currency={currency}
          isRental={isRental}
          onClose={() => { setSelectedListing(null); setHistoryData(null); }}
        />
      )}

      <FloatingAlertButton />
    </div>
  );
}
