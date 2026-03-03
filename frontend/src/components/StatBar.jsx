export default function StatBar({ stats, drops, currency }) {
  const AED_TO_USD = 0.2723;

  const totalDropValue = drops.reduce((s, d) => s + (d.drop_abs_aed || 0), 0);
  const displayValue = currency === "AED"
    ? `AED ${totalDropValue.toFixed(1)}M`
    : `$${(totalDropValue * AED_TO_USD).toFixed(1)}M`;

  const biggest = drops.length ? drops.reduce((a, b) => a.drop_pct > b.drop_pct ? a : b) : null;
  const biggestAbs = drops.length ? drops.reduce((a, b) => a.drop_abs_aed > b.drop_abs_aed ? a : b) : null;

  const cards = [
    {
      icon: "📉",
      label: "Biggest % Drop",
      value: biggest ? `-${biggest.drop_pct}%` : "--",
      sub: biggest ? `${biggest.area || biggest.building}` : "no data yet",
      color: "var(--purple-400)",
      glow: "rgba(168,85,247,0.3)",
    },
    {
      icon: "💸",
      label: "Biggest Value Drop",
      value: biggestAbs
        ? currency === "AED"
          ? `AED -${biggestAbs.drop_abs_aed?.toFixed(1)}M`
          : `$-${(biggestAbs.drop_abs_aed * AED_TO_USD).toFixed(1)}M`
        : "--",
      sub: biggestAbs ? `${biggestAbs.building || biggestAbs.area}` : "no data yet",
      color: "var(--violet-300)",
      glow: "rgba(139,92,246,0.3)",
    },
    {
      icon: "🔍",
      label: "Properties Tracked",
      value: stats.total_scanned ? stats.total_scanned.toLocaleString() : "--",
      sub: "Active listings on Bayut",
      color: "var(--purple-300)",
      glow: "rgba(192,132,252,0.2)",
    },
    {
      icon: "📊",
      label: "Total Value Dropped",
      value: drops.length ? displayValue : "--",
      sub: `Across ${drops.length} listings`,
      color: "var(--violet-400)",
      glow: "rgba(124,58,237,0.3)",
    },
  ];

  return (
    <div className="statbar">
      {cards.map((card, i) => (
        <div className="stat-card" key={i} style={{ "--card-glow": card.glow }}>
          <div className="stat-card-top">
            <span className="stat-card-icon">{card.icon}</span>
            <span className="stat-card-label">{card.label}</span>
          </div>
          <div className="stat-card-value" style={{ color: card.color }}>{card.value}</div>
          <div className="stat-card-sub">{card.sub}</div>
        </div>
      ))}
    </div>
  );
}
