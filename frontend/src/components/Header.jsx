export default function Header({ stats, currency, setCurrency, timeWindow, setTimeWindow, timeWindows, onRefresh, loading, onLogoClick }) {
  const lastScrape = stats?.last_scrape;

  const getTimeAgo = (ts) => {
    if (!ts) return null;
    const diff = (Date.now() - new Date(ts).getTime()) / 1000 / 60;
    if (diff < 1) return "just now";
    if (diff < 60) return Math.floor(diff) + "m ago";
    if (diff < 1440) return Math.floor(diff / 60) + "h ago";
    return Math.floor(diff / 1440) + "d ago";
  };

  const getNextScan = () => {
    const now = new Date();
    const nowUTC = now.getTime();
    // Find next 00, 06, 12, 18 UTC boundary
    const hours = [0, 6, 12, 18];
    const todayBoundaries = hours.map(h => {
      const d = new Date(now);
      d.setUTCHours(h, 0, 0, 0);
      return d.getTime();
    });
    const tomorrowBoundaries = hours.map(h => {
      const d = new Date(now);
      d.setUTCDate(d.getUTCDate() + 1);
      d.setUTCHours(h, 0, 0, 0);
      return d.getTime();
    });
    const allBoundaries = [...todayBoundaries, ...tomorrowBoundaries];
    const next = allBoundaries.find(t => t > nowUTC + 60000); // at least 1 min away
    if (!next) return "soon";
    const diff = (next - nowUTC) / 1000 / 60;
    if (diff < 60) return Math.floor(diff) + "m";
    return Math.floor(diff / 60) + "h " + Math.floor(diff % 60) + "m";
  };

  const finishedAt = lastScrape?.finished_at;
  const timeAgo = getTimeAgo(finishedAt);
  const nextScan = getNextScan();
  const isStale = finishedAt ? (Date.now() - new Date(finishedAt).getTime()) / 1000 / 60 > 30 : true;

  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo" onClick={onLogoClick} style={{ cursor: "pointer" }}>DXB<span>Dips</span></div>
        <div className="header-tagline">Dubai Property Price Drop Tracker</div>
      </div>
      <div className="header-right">
        <div className="live-badge">
          <span className="live-badge-icon">
            <span className="live-ring" />
            <span className="live-ring live-ring-2" />
            <span className="live-dot" />
          </span>
          <span className="live-text">LIVE</span>
        </div>
        <div className="time-windows">
          {timeWindows.map(tw => (
            <button key={tw.label}
              className={`tw-btn${timeWindow.label === tw.label ? ' active' : ''}`}
              onClick={() => setTimeWindow(tw)}>{tw.label}</button>
          ))}
        </div>
        <div className="currency-toggle">
          {["AED", "USD"].map(c => (
            <button key={c}
              className={`curr-btn${currency === c ? ' active' : ''}`}
              onClick={() => setCurrency(c)}>{c}</button>
          ))}
        </div>
        <button className={`refresh-btn${loading ? ' spinning' : ''}`} onClick={onRefresh} title="Refresh">↻</button>
      </div>
    </header>
  );
}
