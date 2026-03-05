const AED_TO_USD = 0.2723;

function fmt(val, currency, isRental) {
  if (!val) return "--";
  if (isRental) {
    // val is raw AED/yr
    const display = currency === "AED" ? val : val * AED_TO_USD;
    const symbol = currency === "AED" ? "AED " : "$";
    if (display >= 1_000_000) return `${symbol}${(display / 1_000_000).toFixed(2)}M/yr`;
    return `${symbol}${(display / 1000).toFixed(0)}K/yr`;
  }
  // val is millions AED
  return currency === "AED" ? `AED ${val.toFixed(2)}M` : `$${(val * AED_TO_USD).toFixed(2)}M`;
}

function parseArea(areaStr) {
  if (!areaStr) return { city: "Unknown", locality: "", sub: "" };
  const parts = areaStr.split(",").map(s => s.trim());
  return { city: parts[0] || "Unknown", locality: parts[1] || "", sub: parts.slice(2).join(", ") };
}

export default function AreaAnalytics({ drops, currency, loading, isRental }) {
  if (loading) return (
    <div className="area-analytics-wrap">
      {[...Array(4)].map((_, i) => (
        <div key={i} style={{ padding: "16px 0", borderBottom: "1px solid var(--border)" }}>
          <div className="skel skel-title" style={{ marginBottom: 8 }} />
          <div className="skel skel-sub" />
        </div>
      ))}
    </div>
  );

  if (!drops.length) return (
    <div className="feed-state">
      <div className="state-icon">◈</div>
      <div className="state-title">No data yet</div>
      <div className="state-sub">Area analytics will populate as listings are scraped.</div>
    </div>
  );

  const areaMap = {};
  drops.forEach(d => {
    const area = d.area || d.building || "Unknown";
    if (!areaMap[area]) areaMap[area] = { area, drops: [], totalDropValue: 0, totalDropPct: 0 };
    areaMap[area].drops.push(d);
    areaMap[area].totalDropValue += d.drop_abs_aed || 0;
    areaMap[area].totalDropPct += d.drop_pct || 0;
  });

  const areas = Object.values(areaMap)
    .map(a => ({
      ...a,
      count: a.drops.length,
      avgDropPct: a.totalDropPct / a.drops.length,
      avgNewPrice: a.drops.reduce((s, d) => s + (d.new_price_aed || 0), 0) / a.drops.length,
      parsed: parseArea(a.area),
    }))
    .sort((a, b) => b.totalDropValue - a.totalDropValue)
    .slice(0, 12);

  const maxDropValue = Math.max(...areas.map(a => a.totalDropValue));
  const mostActiveLocality = areas[0]?.parsed.locality || areas[0]?.parsed.city || "--";

  const typeMap = {};
  drops.forEach(d => { const t = d.type || "Other"; typeMap[t] = (typeMap[t] || 0) + 1; });
  const types = Object.entries(typeMap).sort((a, b) => b[1] - a[1]);

  const totalDropValue = drops.reduce((s, d) => s + (d.drop_abs_aed || 0), 0);

  return (
    <div className="area-analytics-wrap">

      <div className="analytics-summary">
        <div className="summary-item">
          <div className="summary-label">{isRental ? "Total Rent Dropped" : "Total Drop Value"}</div>
          <div className="summary-value gold">
            {fmt(totalDropValue, currency, isRental)}
          </div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Areas with Drops</div>
          <div className="summary-value">{areas.length}</div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Avg Drop</div>
          <div className="summary-value">
            -{(drops.reduce((s, d) => s + (d.drop_pct || 0), 0) / drops.length).toFixed(1)}%
          </div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Most Active Area</div>
          <div className="summary-value sm">{mostActiveLocality}</div>
        </div>
      </div>

      <div className="analytics-section">
        <div className="analytics-section-title">By Property Type</div>
        <div className="type-breakdown">
          {types.map(([type, count]) => (
            <div key={type} className="type-row">
              <div className="type-name">{type}</div>
              <div className="type-bar-wrap">
                <div className="type-bar" style={{ width: `${(count / drops.length) * 100}%` }} />
              </div>
              <div className="type-count">{count}</div>
              <div className="type-pct">{((count / drops.length) * 100).toFixed(0)}%</div>
            </div>
          ))}
        </div>
      </div>

      <div className="analytics-section">
        <div className="analytics-section-title">Top Areas by Drop Value</div>
        <div className="area-table">
          <div className="area-table-head">
            <span>Area</span>
            <span>Drops</span>
            <span>Avg Drop %</span>
            <span>{isRental ? "Total Rent Dropped" : "Total Value Dropped"}</span>
            <span>{isRental ? "Avg Current Rent" : "Avg New Price"}</span>
          </div>
          {areas.map((a, i) => {
            const { city, locality, sub } = a.parsed;
            const heading = locality || city;
            const subheading = locality ? `${city}${sub ? `, ${sub}` : ""}` : sub;
            return (
              <div key={a.area} className="area-table-row">
                <div className="area-table-name">
                  <span className="area-rank">#{i + 1}</span>
                  <div>
                    <div className="area-name-main">{heading}</div>
                    {subheading && <div className="area-name-sub">{subheading}</div>}
                  </div>
                </div>
                <div className="area-table-cell">{a.count}</div>
                <div className="area-table-cell accent">-{a.avgDropPct.toFixed(1)}%</div>
                <div className="area-table-cell gold" style={{ position: "relative" }}>
                  {fmt(a.totalDropValue, currency, isRental)}
                  <div className="value-bar" style={{ width: `${(a.totalDropValue / maxDropValue) * 100}%` }} />
                </div>
                <div className="area-table-cell dim">{fmt(a.avgNewPrice, currency, isRental)}</div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}
