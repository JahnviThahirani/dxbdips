import { useEffect } from "react";
import { formatPrice, formatDrop } from "../lib/utils";

function PriceChart({ history, drops, currency }) {
  if (!history || history.length < 2) {
    return (
      <div className="chart-empty">
        <span>📊 Not enough data points yet</span>
        <span className="chart-empty-sub">Price history builds up over multiple scrape runs</span>
      </div>
    );
  }

  const AED_TO_USD = 0.2723;
  const prices = history.map(h => currency === "AED" ? h.price_aed : h.price_aed * AED_TO_USD);
  const dates = history.map(h => new Date(h.scraped_at));

  const minP = Math.min(...prices) * 0.98;
  const maxP = Math.max(...prices) * 1.02;
  const range = maxP - minP;

  const W = 560, H = 180, PAD = { top: 16, right: 16, bottom: 32, left: 60 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const toX = (i) => PAD.left + (i / (prices.length - 1)) * chartW;
  const toY = (p) => PAD.top + chartH - ((p - minP) / range) * chartH;

  const pathD = prices.map((p, i) => `${i === 0 ? "M" : "L"} ${toX(i)} ${toY(p)}`).join(" ");
  const areaD = pathD + ` L ${toX(prices.length - 1)} ${H - PAD.bottom} L ${toX(0)} ${H - PAD.bottom} Z`;

  // Drop markers
  const dropMarkers = drops.map(d => {
    const dt = new Date(d.detected_at);
    const idx = dates.reduce((best, date, i) =>
      Math.abs(date - dt) < Math.abs(dates[best] - dt) ? i : best, 0);
    return { x: toX(idx), y: toY(prices[idx]), drop: d };
  });

  // Y axis labels
  const yLabels = [minP, (minP + maxP) / 2, maxP].map(p => ({
    y: toY(p),
    label: currency === "AED"
      ? `AED ${p.toFixed(1)}M`
      : `$${p.toFixed(1)}M`,
  }));

  // X axis labels (first, middle, last)
  const xIdxs = [0, Math.floor((prices.length - 1) / 2), prices.length - 1];
  const xLabels = xIdxs.map(i => ({
    x: toX(i),
    label: dates[i].toLocaleDateString("en-AE", { month: "short", day: "numeric" }),
  }));

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="price-chart">
        <defs>
          <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#a855f7" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#a855f7" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="strokeGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#c084fc" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {yLabels.map((l, i) => (
          <line key={i} x1={PAD.left} y1={l.y} x2={W - PAD.right} y2={l.y}
            stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="4 4" />
        ))}

        {/* Area fill */}
        <path d={areaD} fill="url(#lineGrad)" />

        {/* Price line */}
        <path d={pathD} fill="none" stroke="url(#strokeGrad)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

        {/* Data points */}
        {prices.map((_, i) => (
          <circle key={i} cx={toX(i)} cy={toY(prices[i])} r="2.5"
            fill="#a855f7" stroke="#0d0d1a" strokeWidth="1.5" />
        ))}

        {/* Drop markers */}
        {dropMarkers.map((m, i) => (
          <g key={i}>
            <circle cx={m.x} cy={m.y} r="6" fill="rgba(239,68,68,0.2)" stroke="#ef4444" strokeWidth="1.5" />
            <text x={m.x} y={m.y - 10} textAnchor="middle" fill="#ef4444" fontSize="9" fontFamily="monospace">
              ▼{m.drop.drop_pct}%
            </text>
          </g>
        ))}

        {/* Y labels */}
        {yLabels.map((l, i) => (
          <text key={i} x={PAD.left - 6} y={l.y + 4} textAnchor="end"
            fill="rgba(255,255,255,0.35)" fontSize="9" fontFamily="monospace">{l.label}</text>
        ))}

        {/* X labels */}
        {xLabels.map((l, i) => (
          <text key={i} x={l.x} y={H - 6} textAnchor="middle"
            fill="rgba(255,255,255,0.35)" fontSize="9" fontFamily="monospace">{l.label}</text>
        ))}
      </svg>
    </div>
  );
}

export default function HistoryModal({ listing, historyData, loading, currency, onClose }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const AED_TO_USD = 0.2723;

  return (
    <div className="modal-overlay" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal">
        <button className="modal-close" onClick={onClose}>✕</button>

        {/* Property header */}
        <div className="modal-header">
          {listing.image_url && (
            <img src={listing.image_url} alt={listing.title} className="modal-image" />
          )}
          <div className="modal-meta">
            <div className="modal-tags">
              {listing.type && <span className="tag tag-type">{listing.type}</span>}
              {listing.beds && <span className="tag tag-beds">{listing.beds} BR</span>}
            </div>
            <h2 className="modal-title">{listing.title || "Luxury Property"}</h2>
            <p className="modal-location">{[listing.building, listing.area].filter(Boolean).join(" · ")}</p>
            <div className="modal-prices">
              <div className="modal-drop-amount">
                -{formatDrop(listing.drop_abs_aed, listing.drop_abs_usd, currency)}
                <span className="modal-drop-pct"> (-{listing.drop_pct}%)</span>
              </div>
              <div className="modal-price-range">
                <span className="price-old">{formatPrice(listing.old_price_aed, listing.old_price_usd, currency)}</span>
                <span> → </span>
                <span className="price-new">{formatPrice(listing.new_price_aed, listing.new_price_usd, currency)}</span>
              </div>
            </div>
            <a href={listing.url} target="_blank" rel="noopener noreferrer" className="view-btn">
              View on Bayut ↗
            </a>
          </div>
        </div>

        <div className="modal-divider" />

        {/* Price history chart */}
        <div className="modal-section">
          <h3 className="modal-section-title">Price History</h3>
          {loading ? (
            <div className="chart-loading">
              <div className="skel skel-chart" />
            </div>
          ) : historyData ? (
            <>
              <PriceChart
                history={historyData.price_history}
                drops={historyData.drops}
                currency={currency}
              />
              {historyData.drops?.length > 0 && (
                <div className="drop-history-list">
                  <h4 className="drop-history-title">All Drops Detected</h4>
                  {historyData.drops.map((d, i) => (
                    <div key={i} className="drop-history-item">
                      <span className="drop-history-date">
                        {new Date(d.detected_at).toLocaleDateString("en-AE", {
                          day: "numeric", month: "short", year: "numeric"
                        })}
                      </span>
                      <span className="drop-history-amount">
                        -{formatDrop(d.drop_abs_aed, d.drop_abs_aed * AED_TO_USD * 1_000_000, currency)}
                      </span>
                      <span className="drop-history-pct">-{d.drop_pct}%</span>
                      <span className="drop-history-range">
                        {formatPrice(d.old_price_aed, d.old_price_aed * AED_TO_USD, currency)}
                        {" → "}
                        {formatPrice(d.new_price_aed, d.new_price_aed * AED_TO_USD, currency)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="chart-empty">Failed to load history</div>
          )}
        </div>
      </div>
    </div>
  );
}
