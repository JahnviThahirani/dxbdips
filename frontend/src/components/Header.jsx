export default function Header({ stats, currency, setCurrency, timeWindow, setTimeWindow, timeWindows, onRefresh, loading, onLogoClick }) {
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-logo" onClick={onLogoClick} style={{ cursor: "pointer" }}>DXB<span>Dips</span></div>
        <div className="header-tagline">Dubai Property Price Drop Tracker</div>
        {/* Live badge lives here on mobile (hidden on desktop via CSS) */}
        <div className="live-badge">
          <span className="live-badge-icon">
            <span className="live-ring" />
            <span className="live-ring live-ring-2" />
            <span className="live-dot" />
          </span>
          <span className="live-text">Scanning Live</span>
        </div>
      </div>
      <div className="header-right">
        {/* Live badge also here for desktop layout (hidden on mobile via CSS) */}
        <div className="live-badge">
          <span className="live-badge-icon">
            <span className="live-ring" />
            <span className="live-ring live-ring-2" />
            <span className="live-dot" />
          </span>
          <span className="live-text">Scanning Live</span>
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
