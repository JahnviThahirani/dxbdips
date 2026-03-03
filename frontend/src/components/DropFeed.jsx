import { formatPrice, formatDrop, timeAgo, getDropTier } from "../lib/utils";

function DropCard({ drop, currency, rank, onClick }) {
  const tier = getDropTier(drop.drop_pct);
  const when = timeAgo(drop.detected_at);
  const isFresh = when?.cls === "recent" || when?.cls === "today";
  const pfUrl = drop.url;

  return (
    <div className={`drop-card tier-${tier}`} onClick={() => onClick(drop)}>
      <div className="drop-card-rank">
        <span className={`rank-num ${rank <= 3 ? `rank-${rank}` : ""}`}>#{rank}</span>
      </div>

      <div className="drop-card-image">
        {drop.image_url && (
          <img src={drop.image_url} alt={drop.title || "Property"} loading="lazy"
            onError={e => { e.target.style.display = "none"; e.target.nextSibling.style.display = "flex"; }}
          />
        )}
        <div className="image-placeholder" style={{ display: drop.image_url ? "none" : "flex" }}>
          <span>{drop.type === "villa" ? "🏡" : drop.type === "penthouse" ? "🏙️" : "🏢"}</span>
        </div>
        <div className={`drop-badge tier-${tier}`}>▼ {drop.drop_pct}%</div>
      </div>

      <div className="drop-card-info">
        <h3 className="drop-title">{drop.title || "Luxury Property"}</h3>
        <p className="drop-location">
          {[drop.building, drop.area].filter(Boolean).join(" · ")}
        </p>
        <div className="drop-tags">
          {drop.type && <span className="tag tag-type">{drop.type}</span>}
          {drop.beds && <span className="tag tag-beds">{drop.beds} BR</span>}
          {drop.size_sqft && <span className="tag tag-size">{Number(drop.size_sqft).toLocaleString()} sqft</span>}
          {isFresh && <span className="tag tag-time fresh">New drop</span>}
          <span className={`tag tag-time ${when.cls}`}>{when.text}</span>
        </div>
      </div>

      <div className="drop-card-prices">
        <div className="price-drop-amount">
          -{formatDrop(drop.drop_abs_aed, drop.drop_abs_usd, currency)}
        </div>
        <div className="price-range">
          <span className="price-old">{formatPrice(drop.old_price_aed, drop.old_price_usd, currency)}</span>
          <span className="price-arrow">→</span>
          <span className="price-new">{formatPrice(drop.new_price_aed, drop.new_price_usd, currency)}</span>
        </div>
            {pfUrl && (
          <a href={pfUrl} target="_blank" rel="noopener noreferrer"
            className="view-pf-link" onClick={e => e.stopPropagation()}>
            View on Property Finder ↗
          </a>
        )}
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="drop-card skeleton-card">
      <div className="drop-card-rank"><div className="skel skel-sm" /></div>
      <div className="drop-card-image"><div className="skel skel-img" /></div>
      <div className="drop-card-info">
        <div className="skel skel-title" />
        <div className="skel skel-sub" />
        <div className="skel skel-tags" />
      </div>
      <div className="drop-card-prices">
        <div className="skel skel-price" />
        <div className="skel skel-range" />
      </div>
    </div>
  );
}

export default function DropFeed({ drops, currency, loading, error, onCardClick }) {
  const handleCardClick = (drop) => {
    if (drop.url) {
      onCardClick(drop);
    }
  };

  if (error) {
    return (
      <div className="feed-state">
        <div className="state-icon">⚠️</div>
        <div className="state-title">Can't reach the server</div>
        <div className="state-sub">The API isn't responding - it may be restarting. Try refreshing in a minute.</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="drop-feed">
        {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (!drops.length) {
    return (
      <div className="feed-state">
        <div className="state-icon">🔍</div>
        <div className="state-title">No price drops detected yet</div>
        <div className="state-sub">DXB Dips compares prices between scrape runs. The baseline is complete - drops appear after the next scan.</div>
        <div className="state-next-scan"><span className="state-next-dot" />Scans run every 6 hours</div>
      </div>
    );
  }

  return (
    <div className="drop-feed">
      <div className="feed-header">
        <span className="feed-header-text">
          ▸ {drops.length} price drop{drops.length !== 1 ? "s" : ""} detected
        </span>
        <span className="feed-header-sub">Click any card to see full price history</span>
      </div>
      {drops.map((drop, i) => (
        <DropCard
          key={drop.id}
          drop={drop}
          currency={currency}
          rank={i + 1}
          onClick={handleCardClick}
        />
      ))}
    </div>
  );
}
