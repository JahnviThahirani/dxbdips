export const AED_TO_USD = 0.2723;

export function formatPrice(aedM, usdM, currency) {
  const sym = currency === "AED" ? "AED " : "$";
  const val = currency === "AED" ? aedM : (usdM || aedM * AED_TO_USD);
  if (!val) return "--";
  if (val >= 1) return `${sym}${val.toFixed(1)}M`;
  return `${sym}${(val * 1000).toFixed(0)}K`;
}

export function formatDrop(dropAbsAed, dropAbsUsd, currency) {
  const sym = currency === "AED" ? "AED " : "$";
  const val = currency === "AED"
    ? dropAbsAed * 1_000_000
    : (dropAbsUsd || dropAbsAed * AED_TO_USD * 1_000_000);
  if (!val) return "--";
  if (val >= 1_000_000) return `${sym}${(val / 1_000_000).toFixed(1)}M`;
  return `${sym}${(val / 1000).toFixed(0)}K`;
}

export function timeAgo(isoStr) {
  const diff = Date.now() - new Date(isoStr).getTime();
  const hrs = Math.floor(diff / 3600000);
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return { text: `${mins}m ago`, cls: "recent" };
  if (hrs < 12) return { text: `${hrs}h ago`, cls: "recent" };
  if (hrs < 24) return { text: "Today", cls: "today" };
  const days = Math.floor(hrs / 24);
  if (days < 7) return { text: `${days}d ago`, cls: "older" };
  return { text: `${days}d ago`, cls: "oldest" };
}

export function getDropTier(pct) {
  if (pct >= 10) return "high";
  if (pct >= 5) return "medium";
  return "low";
}
