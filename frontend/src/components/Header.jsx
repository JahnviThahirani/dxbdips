export default function Header({ currency, setCurrency, timeWindow, setTimeWindow, timeWindows, onRefresh, loading }) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo">DXB<span>Dips</span></div>
        <div className="header-tagline">Dubai Luxury Property Price Intelligence</div>
      </div>
      <div className="header-right">
        <div className="time-windows">
          {timeWindows.map(tw => (
            <button key={tw.label} className={`tw-btn ${timeWindow.label === tw.label ? "active" : ""}`} onClick={() => setTimeWindow(tw)}>{tw.label}</button>
          ))}
        </div>
        <div className="currency-toggle">
          {["AED", "USD"].map(c => (
            <button key={c} className={`curr-btn ${currency === c ? "active" : ""}`} onClick={() => setCurrency(c)}>{c}</button>
          ))}
        </div>
        <button className={`refresh-btn ${loading ? "spinning" : ""}`} onClick={onRefresh} disabled={loading}>{loading ? "..." : "↻"}</button>
      </div>
    </header>
  );
}