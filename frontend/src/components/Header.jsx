import { useEffect, useState } from "react";

export default function Header({ stats, currency, setCurrency, timeWindow, setTimeWindow, timeWindows, onRefresh, loading }) {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="header">
      <div className="header-left">
        <div className="logo">
          <div className="logo-icon">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <path d="M4 8L14 20L24 8" stroke="url(#g1)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M4 14L14 26L24 14" stroke="url(#g2)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.5"/>
              <defs>
                <linearGradient id="g1" x1="4" y1="8" x2="24" y2="20" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#a855f7"/>
                  <stop offset="1" stopColor="#7c3aed"/>
                </linearGradient>
                <linearGradient id="g2" x1="4" y1="14" x2="24" y2="26" gradientUnits="userSpaceOnUse">
                  <stop stopColor="#c084fc"/>
                  <stop offset="1" stopColor="#a855f7"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <div className="logo-text">
            <span className="logo-name">Dubai<span className="logo-accent">Dips</span></span>
            <span className="logo-sub">dxbdips.com</span>
          </div>
        </div>

        <div className="live-indicator">
          <span className="live-dot" />
          <span>Live</span>
        </div>
      </div>

      <div className="header-center">
        <div className="stat-pill">
          <span className="stat-pill-value">{stats.total_drops ?? "--"}</span>
          <span className="stat-pill-label">drops</span>
        </div>
        <div className="stat-pill">
          <span className="stat-pill-value accent">{stats.avg_drop_pct ? stats.avg_drop_pct + "%" : "--"}</span>
          <span className="stat-pill-label">avg drop</span>
        </div>
        <div className="stat-pill">
          <span className="stat-pill-value bright">{stats.biggest_drop_pct ? stats.biggest_drop_pct + "%" : "--"}</span>
          <span className="stat-pill-label">biggest</span>
        </div>
        <div className="stat-pill">
          <span className="stat-pill-value dim">{stats.total_scanned ? stats.total_scanned.toLocaleString() : "--"}</span>
          <span className="stat-pill-label">tracked</span>
        </div>
      </div>

      <div className="header-right">
        <div className="time-toggle">
          {timeWindows.map(tw => (
            <button
              key={tw.label}
              className={`time-btn ${timeWindow.label === tw.label ? "active" : ""}`}
              onClick={() => setTimeWindow(tw)}
            >{tw.label}</button>
          ))}
        </div>

        <div className="currency-toggle">
          <button className={`curr-btn ${currency === "USD" ? "active" : ""}`} onClick={() => setCurrency("USD")}>USD</button>
          <button className={`curr-btn ${currency === "AED" ? "active" : ""}`} onClick={() => setCurrency("AED")}>AED</button>
        </div>

        <button className={`refresh-btn ${loading ? "spinning" : ""}`} onClick={onRefresh} title="Refresh">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M12.5 7A5.5 5.5 0 1 1 7 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M7 1.5L9.5 4M7 1.5L9.5 -1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </header>
  );
}
