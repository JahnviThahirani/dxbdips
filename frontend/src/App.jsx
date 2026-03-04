import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import StatBar from "./components/StatBar";
import DropFeed from "./components/DropFeed";
import AreaAnalytics from "./components/AreaAnalytics";
import HistoryModal from "./components/HistoryModal";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TIME_WINDOWS = [
  { label: "24H", hours: 24 },
  { label: "7D", hours: 168 },
  { label: "30D", hours: 720 },
];

const PRICE_TIERS = [
  { id: "all",     label: "All",       min: 0,  max: Infinity },
  { id: "5to10m",  label: "5M – 10M",  min: 5,  max: 10 },
  { id: "10to20m", label: "10M – 20M", min: 10, max: 20 },
  { id: "20mplus", label: "20M+",      min: 20, max: Infinity },
];

const PROP_FILTERS = [
  { id: "all",       label: "All" },
  { id: "apartment", label: "Apartments" },
  { id: "villa",     label: "Villas" },
  { id: "penthouse", label: "Penthouses" },
  { id: "townhouse", label: "Townhouses" },
  { id: "5plus",     label: "5%+ Drop" },
  { id: "10plus",    label: "10%+ Drop" },
];

const SORTS = [
  { id: "abs",    label: "Biggest Value Drop" },
  { id: "pct",    label: "Biggest % Drop" },
  { id: "recent", label: "Most Recent" },
  { id: "price",  label: "Lowest Price" },
];

export default function App() {
  const [drops, setDrops] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currency, setCurrency] = useState("AED");
  const [timeWindow, setTimeWindow] = useState(TIME_WINDOWS[0]);
  const [activeTier, setActiveTier] = useState("all");
  const [propFilter, setPropFilter] = useState("all");
  const [sort, setSort] = useState("abs");
  const [showAreas, setShowAreas] = useState(false);
  const [selectedListing, setSelectedListing] = useState(null);
  const [historyData, setHistoryData] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [dropsRes, statsRes] = await Promise.all([
        fetch(`${API}/api/drops?hours=${timeWindow.hours}&limit=200&sort=${sort}`),
        fetch(`${API}/api/stats?hours=${timeWindow.hours}`),
      ]);
      if (!dropsRes.ok || !statsRes.ok) throw new Error("API error");
      const dropsData = await dropsRes.json();
      const statsData = await statsRes.json();
      setDrops(dropsData.drops || []);
      setStats(statsData);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [timeWindow.hours, sort]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => {
    const id = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, [fetchData]);

  const openHistory = async (listing) => {
    setSelectedListing(listing);
    setHistoryLoading(true);
    try {
      const res = await fetch(`${API}/api/history/${listing.listing_id}`);
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
    const p = d.new_price_aed || 0;
    return p >= tier.min && p < tier.max;
  });

  const filteredDrops = tierFiltered.filter(d => {
    if (propFilter === "all") return true;
    if (propFilter === "10plus") return d.drop_pct >= 10;
    if (propFilter === "5plus") return d.drop_pct >= 5;
    return d.type?.toLowerCase() === propFilter;
  });

  const tierCounts = PRICE_TIERS.reduce((acc, t) => {
    acc[t.id] = drops.filter(d => {
      const p = d.new_price_aed || 0;
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
        onRefresh={fetchData}
        loading={loading}
      />
      <StatBar stats={stats} drops={drops} currency={currency} />

      <nav className="tab-nav">
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
        <button
          className={`tab-btn area-tab ${showAreas ? "active" : ""}`}
          onClick={() => setShowAreas(true)}
        >
          <span className="tab-label">Area Analytics</span>
        </button>
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
          <DropFeed drops={filteredDrops} currency={currency} loading={loading} error={error} onCardClick={openHistory} />
        </>
      )}

      {showAreas && <AreaAnalytics drops={drops} currency={currency} loading={loading} />}

      {selectedListing && (
        <HistoryModal
          listing={selectedListing}
          historyData={historyData}
          loading={historyLoading}
          currency={currency}
          onClose={() => { setSelectedListing(null); setHistoryData(null); }}
        />
      )}
    </div>
  );
}