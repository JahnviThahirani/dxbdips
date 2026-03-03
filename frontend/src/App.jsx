import { useState, useEffect, useCallback } from "react";
import Header from "./components/Header";
import StatBar from "./components/StatBar";
import FilterBar from "./components/FilterBar";
import DropFeed from "./components/DropFeed";
import HistoryModal from "./components/HistoryModal";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TIME_WINDOWS = [
  { label: "24H", hours: 24 },
  { label: "7D", hours: 168 },
  { label: "30D", hours: 720 },
];

export default function App() {
  const [drops, setDrops] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currency, setCurrency] = useState("USD");
  const [timeWindow, setTimeWindow] = useState(TIME_WINDOWS[0]);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("abs");
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

  const filteredDrops = drops.filter((d) => {
    if (filter === "all") return true;
    if (filter === "10plus") return d.drop_pct >= 10;
    if (filter === "5plus") return d.drop_pct >= 5;
    return d.type === filter;
  });

  return (
    <div className="app">
      <div className="bg-grid" />
      <div className="bg-glow" />

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

      <FilterBar
        filter={filter}
        setFilter={setFilter}
        sort={sort}
        setSort={setSort}
        count={filteredDrops.length}
      />

      <DropFeed
        drops={filteredDrops}
        currency={currency}
        loading={loading}
        error={error}
        onCardClick={openHistory}
      />

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
