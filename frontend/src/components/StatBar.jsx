export default function StatBar({ stats, drops, currency, isRental }) {
  const AED_TO_USD = 0.2723;

  const formatRentalPrice = (aed) => {
    if (!aed) return "--";
    const val = currency === "AED" ? aed : Math.round(aed * AED_TO_USD);
    const symbol = currency === "AED" ? "AED " : "$";
    if (val >= 1_000_000) return `${symbol}${(val / 1_000_000).toFixed(1)}M/yr`;
    return `${symbol}${(val / 1000).toFixed(0)}K/yr`;
  };

  const formatSaleDropValue = (totalAedMillions) => {
    if (currency === "AED") return `AED ${totalAedMillions.toFixed(1)}M`;
    return `$${(totalAedMillions * AED_TO_USD).toFixed(1)}M`;
  };

  const formatRentalDropValue = (totalAed) => {
    if (currency === "AED") {
      if (totalAed >= 1_000_000) return `AED ${(totalAed / 1_000_000).toFixed(1)}M/yr`;
      return `AED ${(totalAed / 1000).toFixed(0)}K/yr`;
    }
    const usd = totalAed * AED_TO_USD;
    if (usd >= 1_000_000) return `$${(usd / 1_000_000).toFixed(1)}M/yr`;
    return `$${(usd / 1000).toFixed(0)}K/yr`;
  };

  const biggest = drops.length ? drops.reduce((a, b) => a.drop_pct > b.drop_pct ? a : b) : null;
  const biggestAbs = drops.length ? drops.reduce((a, b) => a.drop_abs_aed > b.drop_abs_aed ? a : b) : null;

  let biggestAbsLabel = "--";
  let totalDropLabel = "--";

  if (isRental) {
    biggestAbsLabel = biggestAbs ? formatRentalPrice(biggestAbs.drop_abs_aed) : "--";
    const totalDropRaw = drops.reduce((s, d) => s + (d.drop_abs_aed || 0), 0);
    totalDropLabel = drops.length ? formatRentalDropValue(totalDropRaw) : "--";
  } else {
    // Sale prices are in millions
    biggestAbsLabel = biggestAbs
      ? (currency === "AED"
        ? `AED -${biggestAbs.drop_abs_aed?.toFixed(1)}M`
        : `$-${(biggestAbs.drop_abs_aed * AED_TO_USD).toFixed(1)}M`)
      : "--";
    const totalDropValue = drops.reduce((s, d) => s + (d.drop_abs_aed || 0), 0);
    totalDropLabel = drops.length ? formatSaleDropValue(totalDropValue) : "--";
  }

  const cards = [
    {
      icon: "📉",
      label: "Biggest % Drop",
      value: biggest ? `-${biggest.drop_pct}%` : "--",
      sub: biggest ? `${biggest.area || biggest.building}` : "no data yet",
    },
    {
      icon: "💸",
      label: "Biggest Value Drop",
      value: biggestAbsLabel,
      sub: biggestAbs ? `${biggestAbs.building || biggestAbs.area}` : "no data yet",
    },
    {
      icon: "🔍",
      label: "Listings Monitored",
      value: stats.unique_listings
        ? stats.unique_listings.toLocaleString()
        : (stats.total_scanned ? stats.total_scanned.toLocaleString() : "--"),
      sub: isRental ? "Unique rentals tracked" : "Unique properties tracked",
    },
    {
      icon: "📊",
      label: isRental ? "Total Rent Dropped" : "Total Value Dropped",
      value: totalDropLabel,
      sub: `Across ${drops.length} listings`,
    },
  ];

  return (
    <div className="statbar">
      {cards.map((card, i) => (
        <div className="stat-card" key={i}>
          <div className="stat-card-top">
            <span className="stat-card-icon">{card.icon}</span>
            <span className="stat-card-label">{card.label}</span>
          </div>
          <div className="stat-card-value" style={{ color: "var(--drop-red)" }}>{card.value}</div>
          <div className="stat-card-sub">{card.sub}</div>
        </div>
      ))}
    </div>
  );
}
