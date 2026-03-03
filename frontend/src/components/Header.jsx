export default function Header({ stats, currency, setCurrency, timeWindow, setTimeWindow, timeWindows, onRefresh, loading }) {
  const lastScrape = stats?.last_scrape;
  const getTimeAgo = (ts) => {
    if (!ts) return null;
    const diff = (Date.now() - new Date(ts).getTime()) / 1000 / 60;
    if (diff < 1) return "just now";
    if (diff < 60) return Math.floor(diff) + "m ago";
    if (diff < 1440) return Math.floor(diff/60) + "h ago";
    return Math.floor(diff/1440) + "d ago";
  };
  const getNextScan = (ts) => {
    if (!ts) return null;
    const next = new Date(new Date(ts).getTime() + 6*60*60*1000);
    const diff = (next - Date.now()) / 1000 / 60;
    if (diff <= 0) return "soon";
    if (diff < 60) return Math.floor(diff) + "m";
    return Math.floor(diff/60) + "h " + Math.floor(diff%60) + "m";
  };
  const finishedAt = lastScrape?.finished_at;
  const timeAgo = getTimeAgo(finishedAt);
  const nextScan = getNextScan(finishedAt);
  const isStale = finishedAt ? (Date.now()-new Date(finishedAt).getTime())/1000/60 > 30 : true;
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">DXB<span>Dips</span></div>
        <div className="header-tagline">Dubai Property Price Drop Tracker</div>
      </div>
      <div className="header-right">
        {timeAgo && (
          <div className="last-scan">
            <span className={`last-scan-dot${isStale ? ' stale' : ''}`} />
            Last scan {timeAgo}
            {nextScan && <span style={{ opacity: 0.55, marginLeft: 4 }}>· next in {nextScan}</span>}
          </div>
        )}
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