import { useEffect } from "react";
import { formatPrice, formatDrop } from "../lib/utils";

function PriceChart({ history, drops, currency }) {
  if (!history || history.length < 2) {
    return (
      <div style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        justifyContent: "center", gap: "8px", padding: "48px 0",
        color: "#999", fontSize: "13px"
      }}>
        <span style={{ fontSize: "28px" }}>📊</span>
        <span>Not enough data points yet</span>
        <span style={{ fontSize: "11px", color: "#bbb" }}>Price history builds up over multiple scrape runs</span>
      </div>
    );
  }

  const AED_TO_USD = 0.2723;
  const prices = history.map(h => currency === "AED" ? h.price_aed : h.price_aed * AED_TO_USD);
  const dates = history.map(h => new Date(h.scraped_at));

  const minP = Math.min(...prices) * 0.97;
  const maxP = Math.max(...prices) * 1.03;
  const range = maxP - minP || 1;

  const W = 580, H = 200;
  const PAD = { top: 20, right: 24, bottom: 36, left: 72 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const toX = (i) => PAD.left + (i / Math.max(prices.length - 1, 1)) * chartW;
  const toY = (p) => PAD.top + chartH - ((p - minP) / range) * chartH;

  const pathD = prices.map((p, i) => `${i === 0 ? "M" : "L"} ${toX(i).toFixed(1)} ${toY(p).toFixed(1)}`).join(" ");
  const areaD = pathD + ` L ${toX(prices.length - 1).toFixed(1)} ${(H - PAD.bottom).toFixed(1)} L ${toX(0).toFixed(1)} ${(H - PAD.bottom).toFixed(1)} Z`;

  const dropMarkers = drops.map(d => {
    const dt = new Date(d.detected_at);
    const idx = dates.reduce((best, date, i) =>
      Math.abs(date - dt) < Math.abs(dates[best] - dt) ? i : best, 0);
    return { x: toX(idx), y: toY(prices[idx]), drop: d };
  });

  const yLabels = [minP, (minP + maxP) / 2, maxP].map(p => ({
    y: toY(p),
    label: currency === "AED" ? `${p.toFixed(1)}M` : `$${p.toFixed(2)}M`,
  }));

  const xIdxs = prices.length <= 3
    ? prices.map((_, i) => i)
    : [0, Math.floor((prices.length - 1) / 2), prices.length - 1];

  const xLabels = xIdxs.map(i => ({
    x: toX(i),
    label: dates[i].toLocaleDateString("en-AE", { month: "short", day: "numeric" }),
  }));

  return (
    <div style={{ width: "100%", overflowX: "auto" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto", display: "block" }}>
        <defs>
          <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#c0392b" stopOpacity="0.12" />
            <stop offset="100%" stopColor="#c0392b" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {yLabels.map((l, i) => (
          <line key={i} x1={PAD.left} y1={l.y} x2={W - PAD.right} y2={l.y}
            stroke="#e8e4df" strokeWidth="1" strokeDasharray="3 4" />
        ))}

        {/* Area fill */}
        <path d={areaD} fill="url(#areaFill)" />

        {/* Price line */}
        <path d={pathD} fill="none" stroke="#c0392b" strokeWidth="2"
          strokeLinecap="round" strokeLinejoin="round" />

        {/* Data points */}
        {prices.map((p, i) => (
          <circle key={i} cx={toX(i)} cy={toY(p)} r="3"
            fill="#fff" stroke="#c0392b" strokeWidth="1.5" />
        ))}

        {/* Drop markers */}
        {dropMarkers.map((m, i) => (
          <g key={i}>
            <circle cx={m.x} cy={m.y} r="7"
              fill="rgba(192,57,43,0.1)" stroke="#c0392b" strokeWidth="1.5" />
            <circle cx={m.x} cy={m.y} r="3"
              fill="#c0392b" />
            <text x={m.x} y={m.y - 13} textAnchor="middle"
              fill="#c0392b" fontSize="9" fontWeight="600"
              fontFamily="'DM Mono', monospace">
              ▼{m.drop.drop_pct}%
            </text>
          </g>
        ))}

        {/* Y labels */}
        {yLabels.map((l, i) => (
          <text key={i} x={PAD.left - 8} y={l.y + 4} textAnchor="end"
            fill="#aaa" fontSize="9.5" fontFamily="'DM Mono', monospace">{l.label}</text>
        ))}

        {/* X labels */}
        {xLabels.map((l, i) => (
          <text key={i} x={l.x} y={H - 8} textAnchor="middle"
            fill="#aaa" fontSize="9.5" fontFamily="'DM Mono', monospace">{l.label}</text>
        ))}
      </svg>
    </div>
  );
}

export default function HistoryModal({ listing, historyData, loading, currency, onClose }) {
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  const AED_TO_USD = 0.2723;

  return (
    <div
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.35)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "20px",
      }}
    >
      <div style={{
        background: "#fff", borderRadius: "16px",
        width: "100%", maxWidth: "640px", maxHeight: "90vh",
        overflowY: "auto", boxShadow: "0 24px 80px rgba(0,0,0,0.18)",
        position: "relative",
      }}>

        {/* Close button */}
        <button
          onClick={onClose}
          style={{
            position: "absolute", top: "16px", right: "16px",
            width: "32px", height: "32px", borderRadius: "50%",
            border: "none", background: "#f0ece6", cursor: "pointer",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "14px", color: "#666", zIndex: 10,
          }}
        >✕</button>

        {/* Image */}
        {listing.image_url && (
          <div style={{ width: "100%", height: "220px", overflow: "hidden", borderRadius: "16px 16px 0 0" }}>
            <img
              src={listing.image_url}
              alt={listing.title}
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
              onError={e => { e.target.style.display = "none"; }}
            />
          </div>
        )}

        {/* Content */}
        <div style={{ padding: "24px" }}>

          {/* Tags */}
          <div style={{ display: "flex", gap: "8px", marginBottom: "10px", flexWrap: "wrap" }}>
            {listing.type && (
              <span style={{
                fontSize: "11px", fontWeight: "600", letterSpacing: "0.08em",
                textTransform: "uppercase", color: "#888",
                background: "#f5f2ee", borderRadius: "6px", padding: "3px 8px"
              }}>{listing.type}</span>
            )}
            {listing.beds && (
              <span style={{
                fontSize: "11px", fontWeight: "600", letterSpacing: "0.08em",
                textTransform: "uppercase", color: "#888",
                background: "#f5f2ee", borderRadius: "6px", padding: "3px 8px"
              }}>{listing.beds} BR</span>
            )}
            {listing.size_sqft && (
              <span style={{
                fontSize: "11px", fontWeight: "600", letterSpacing: "0.08em",
                textTransform: "uppercase", color: "#888",
                background: "#f5f2ee", borderRadius: "6px", padding: "3px 8px"
              }}>{listing.size_sqft?.toLocaleString()} sqft</span>
            )}
          </div>

          {/* Title */}
          <h2 style={{
            fontSize: "18px", fontWeight: "700", color: "#1a1a1a",
            lineHeight: "1.3", margin: "0 0 6px 0"
          }}>
            {listing.title || "Luxury Property"}
          </h2>

          {/* Location */}
          <p style={{ fontSize: "13px", color: "#888", margin: "0 0 20px 0" }}>
            {[listing.building, listing.area].filter(Boolean).join(" · ")}
          </p>

          {/* Price drop summary */}
          <div style={{
            background: "#fdf5f4", border: "1px solid #f5ddd9",
            borderRadius: "12px", padding: "16px 20px", marginBottom: "20px",
            display: "flex", justifyContent: "space-between", alignItems: "center",
            flexWrap: "wrap", gap: "12px"
          }}>
            <div>
              <div style={{ fontSize: "11px", color: "#c0392b", fontWeight: "600",
                letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "4px" }}>
                Price Drop
              </div>
              <div style={{ fontSize: "26px", fontWeight: "800", color: "#c0392b", lineHeight: 1 }}>
                -{formatDrop(listing.drop_abs_aed, listing.drop_abs_usd, currency)}
              </div>
              <div style={{ fontSize: "13px", color: "#c0392b", opacity: 0.8, marginTop: "2px" }}>
                -{listing.drop_pct}% reduction
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "11px", color: "#999", marginBottom: "4px" }}>Was</div>
              <div style={{ fontSize: "15px", color: "#999", textDecoration: "line-through" }}>
                {formatPrice(listing.old_price_aed, listing.old_price_usd, currency)}
              </div>
              <div style={{ fontSize: "11px", color: "#999", margin: "4px 0 4px" }}>Now</div>
              <div style={{ fontSize: "20px", fontWeight: "700", color: "#1a1a1a" }}>
                {formatPrice(listing.new_price_aed, listing.new_price_usd, currency)}
              </div>
            </div>
          </div>

          {/* View listing link */}
          {listing.url && (
            <a
              href={listing.url} target="_blank" rel="noopener noreferrer"
              style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                fontSize: "13px", fontWeight: "600", color: "#1a1a1a",
                textDecoration: "none", padding: "10px 18px",
                border: "1.5px solid #e0dbd4", borderRadius: "8px",
                marginBottom: "28px", transition: "all 0.15s",
              }}
              onMouseEnter={e => { e.currentTarget.style.background = "#f5f2ee"; }}
              onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
            >
              View Listing ↗
            </a>
          )}

          {/* Divider */}
          <div style={{ height: "1px", background: "#f0ece6", marginBottom: "24px" }} />

          {/* Price history chart */}
          <div>
            <h3 style={{
              fontSize: "12px", fontWeight: "700", letterSpacing: "0.1em",
              textTransform: "uppercase", color: "#aaa", margin: "0 0 16px 0"
            }}>Price History</h3>

            {loading ? (
              <div style={{
                height: "200px", background: "#f5f2ee",
                borderRadius: "8px", animation: "pulse 1.5s infinite"
              }} />
            ) : historyData ? (
              <>
                <PriceChart
                  history={historyData.price_history}
                  drops={historyData.drops}
                  currency={currency}
                />

                {/* Drop log */}
                {historyData.drops?.length > 0 && (
                  <div style={{ marginTop: "24px" }}>
                    <h4 style={{
                      fontSize: "11px", fontWeight: "700", letterSpacing: "0.1em",
                      textTransform: "uppercase", color: "#aaa", margin: "0 0 12px 0"
                    }}>All Drops Detected</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {historyData.drops.map((d, i) => (
                        <div key={i} style={{
                          display: "flex", justifyContent: "space-between",
                          alignItems: "center", padding: "10px 14px",
                          background: "#fdf9f8", borderRadius: "8px",
                          border: "1px solid #f0ece6", flexWrap: "wrap", gap: "8px"
                        }}>
                          <span style={{ fontSize: "12px", color: "#888" }}>
                            {new Date(d.detected_at).toLocaleDateString("en-AE", {
                              day: "numeric", month: "short", year: "numeric"
                            })}
                          </span>
                          <span style={{ fontSize: "13px", fontWeight: "700", color: "#c0392b" }}>
                            -{formatDrop(d.drop_abs_aed, d.drop_abs_aed * AED_TO_USD * 1_000_000, currency)}
                          </span>
                          <span style={{
                            fontSize: "11px", fontWeight: "600", color: "#c0392b",
                            background: "rgba(192,57,43,0.08)", borderRadius: "4px",
                            padding: "2px 6px"
                          }}>-{d.drop_pct}%</span>
                          <span style={{ fontSize: "12px", color: "#999" }}>
                            {formatPrice(d.old_price_aed, d.old_price_aed * AED_TO_USD, currency)}
                            {" → "}
                            {formatPrice(d.new_price_aed, d.new_price_aed * AED_TO_USD, currency)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: "center", padding: "40px", color: "#aaa", fontSize: "13px" }}>
                Failed to load history
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
