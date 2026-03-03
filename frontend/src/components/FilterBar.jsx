const FILTERS = [
  { id: "all", label: "All" },
  { id: "apartment", label: "Apartments" },
  { id: "villa", label: "Villas" },
  { id: "penthouse", label: "Penthouses" },
  { id: "townhouse", label: "Townhouses" },
  { id: "5plus", label: "5%+ Drop" },
  { id: "10plus", label: "10%+ Drop" },
];

const SORTS = [
  { id: "abs", label: "Biggest Value Drop" },
  { id: "pct", label: "Biggest % Drop" },
  { id: "recent", label: "Most Recent" },
  { id: "price", label: "Lowest Price" },
];

export default function FilterBar({ filter, setFilter, sort, setSort, count }) {
  return (
    <div className="filterbar">
      <div className="filterbar-left">
        {FILTERS.map(f => (
          <button
            key={f.id}
            className={`filter-chip ${filter === f.id ? "active" : ""}`}
            onClick={() => setFilter(f.id)}
          >{f.label}</button>
        ))}
      </div>
      <div className="filterbar-right">
        <span className="result-count">{count} drops</span>
        <select
          className="sort-select"
          value={sort}
          onChange={e => setSort(e.target.value)}
        >
          {SORTS.map(s => (
            <option key={s.id} value={s.id}>{s.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
