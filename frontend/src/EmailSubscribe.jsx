// EmailSubscribe.jsx
// Matches DXB Dips site aesthetic: cream bg, dark type, red accent, clean cards
// Usage: <EmailSubscribe /> anywhere in your React tree

import { useState } from "react";

const API_BASE = "https://dxbdips-api-production.up.railway.app";

function TogglePill({ options, value, onChange }) {
  return (
    <div style={styles.pillGroup}>
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          style={{
            ...styles.pill,
            ...(value === opt.value ? styles.pillActive : styles.pillInactive),
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function FilterChip({ label, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        ...styles.chip,
        ...(selected ? styles.chipSelected : styles.chipUnselected),
      }}
    >
      {label}
    </button>
  );
}

export default function EmailSubscribe({ onSuccess } = {}) {
  const [email, setEmail]             = useState("");
  const [listingType, setListingType] = useState("both");
  const [minDropPct, setMinDropPct]   = useState("0");
  const [propType, setPropType]       = useState("");
  const [status, setStatus]           = useState("idle");
  const [message, setMessage]         = useState("");

  const propTypes = [
    { value: "",            label: "All types" },
    { value: "apartment",   label: "Apartments" },
    { value: "villa",       label: "Villas" },
    { value: "penthouse",   label: "Penthouses" },
    { value: "townhouse",   label: "Townhouses" },
  ];

  const dropThresholds = [
    { value: "0",  label: "Any drop" },
    { value: "2",  label: "2%+" },
    { value: "5",  label: "5%+" },
    { value: "10", label: "10%+" },
  ];

  const handleSubmit = async () => {
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setStatus("error");
      setMessage("Please enter a valid email address.");
      return;
    }

    setStatus("loading");
    try {
      const res = await fetch(`${API_BASE}/api/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          listing_type:  listingType,
          min_drop_pct:  parseFloat(minDropPct) || 0,
          property_type: propType || null,
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setStatus("success");
        if (onSuccess) onSuccess();
      } else {
        throw new Error(data.detail || "Subscription failed.");
      }
    } catch (err) {
      setStatus("error");
      setMessage(err.message || "Something went wrong. Please try again.");
    }
  };

  if (status === "success") {
    return (
      <div style={styles.card}>
        <div style={{ textAlign: "center", padding: "12px 0 8px" }}>
          <div style={{
            width: 44, height: 44, borderRadius: "50%",
            background: "#f0ede6", display: "flex",
            alignItems: "center", justifyContent: "center",
            margin: "0 auto 14px", fontSize: 20,
          }}>✓</div>
          <div style={styles.successTitle}>You're subscribed</div>
          <div style={styles.successText}>
            We'll email you when new price drops match your filters.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.card}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.livedot} />
          <span style={styles.headerTitle}>Price Drop Alerts</span>
        </div>
        <span style={styles.freeBadge}>Free</span>
      </div>

      <p style={styles.description}>
        Get notified when new drops are detected. Filters are optional — leave anything blank to receive all updates.
      </p>

      <div style={styles.divider} />

      {/* Listing type — Buy / Rent / Both */}
      <div style={styles.field}>
        <label style={styles.label}>Alert me for</label>
        <TogglePill
          options={[
            { value: "both",   label: "🏠 Buy + 🔑 Rent" },
            { value: "sale",   label: "🏠 Buy only" },
            { value: "rental", label: "🔑 Rent only" },
          ]}
          value={listingType}
          onChange={setListingType}
        />
      </div>

      {/* Property type chips */}
      <div style={styles.field}>
        <label style={styles.label}>
          Property type
          <span style={styles.optional}> — optional, all selected by default</span>
        </label>
        <div style={styles.chipRow}>
          {propTypes.map((pt) => (
            <FilterChip
              key={pt.value}
              label={pt.label}
              selected={propType === pt.value}
              onClick={() => setPropType(pt.value)}
            />
          ))}
        </div>
      </div>

      {/* Min drop size chips */}
      <div style={styles.field}>
        <label style={styles.label}>
          Minimum drop size
          <span style={styles.optional}> — optional, any drop by default</span>
        </label>
        <div style={styles.chipRow}>
          {dropThresholds.map((dt) => (
            <FilterChip
              key={dt.value}
              label={dt.label}
              selected={minDropPct === dt.value}
              onClick={() => setMinDropPct(dt.value)}
            />
          ))}
        </div>
      </div>

      <div style={styles.divider} />

      {/* Email input */}
      <div style={styles.field}>
        <label style={styles.label}>Your email</label>
        <input
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (status === "error") setStatus("idle");
          }}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          style={{
            ...styles.input,
            ...(status === "error" ? { borderColor: "#e74c3c", background: "#fff8f7" } : {}),
          }}
          disabled={status === "loading"}
        />
        {status === "error" && (
          <div style={styles.errorText}>{message}</div>
        )}
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={status === "loading"}
        style={{
          ...styles.submitBtn,
          opacity: status === "loading" ? 0.6 : 1,
          cursor:  status === "loading" ? "not-allowed" : "pointer",
        }}
      >
        {status === "loading" ? "Subscribing…" : "Notify Me →"}
      </button>

      <p style={styles.disclaimer}>No spam · Unsubscribe anytime</p>
    </div>
  );
}

const styles = {
  card: {
    background: "#ffffff",
    border: "1px solid #e0ddd6",
    borderRadius: 16,
    padding: "22px 22px 18px",
    maxWidth: 420,
    width: "100%",
    boxSizing: "border-box",
  },

  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  livedot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#e74c3c",
    display: "inline-block",
    boxShadow: "0 0 0 3px rgba(231,76,60,0.15)",
  },
  headerTitle: {
    fontWeight: 700,
    fontSize: 15,
    color: "#1a1a1a",
    letterSpacing: "-0.2px",
    fontFamily: "system-ui, -apple-system, sans-serif",
  },
  freeBadge: {
    fontSize: 11,
    fontWeight: 600,
    color: "#777",
    border: "1px solid #d0cdc6",
    borderRadius: 20,
    padding: "2px 9px",
    fontFamily: "system-ui, sans-serif",
  },

  description: {
    fontSize: 13,
    color: "#777",
    margin: "0 0 14px",
    lineHeight: 1.55,
    fontFamily: "system-ui, sans-serif",
  },

  divider: {
    height: 1,
    background: "#ede9e2",
    margin: "14px 0",
  },

  field: {
    marginBottom: 14,
  },
  label: {
    display: "block",
    fontSize: 11,
    fontWeight: 700,
    color: "#333",
    marginBottom: 8,
    textTransform: "uppercase",
    letterSpacing: "0.6px",
    fontFamily: "system-ui, sans-serif",
  },
  optional: {
    fontWeight: 400,
    textTransform: "none",
    letterSpacing: 0,
    color: "#aaa",
    fontSize: 11,
  },

  // Toggle pills — mirrors Buy/Rent tabs on the site
  pillGroup: {
    display: "flex",
    background: "#f0ede6",
    borderRadius: 10,
    padding: 3,
    gap: 2,
  },
  pill: {
    flex: 1,
    padding: "8px 8px",
    border: "none",
    borderRadius: 8,
    fontSize: 12,
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.15s ease",
    fontFamily: "system-ui, sans-serif",
    whiteSpace: "nowrap",
    lineHeight: 1.3,
  },
  pillActive: {
    background: "#1a1a1a",
    color: "#ffffff",
    boxShadow: "0 1px 4px rgba(0,0,0,0.18)",
  },
  pillInactive: {
    background: "transparent",
    color: "#666",
  },

  // Filter chips — mirrors All/Apartments/Villas chips on the site
  chipRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 6,
  },
  chip: {
    padding: "5px 13px",
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 500,
    cursor: "pointer",
    border: "1px solid",
    transition: "all 0.12s ease",
    fontFamily: "system-ui, sans-serif",
    lineHeight: 1.5,
    background: "none",
  },
  chipSelected: {
    background: "#1a1a1a",
    color: "#ffffff",
    borderColor: "#1a1a1a",
  },
  chipUnselected: {
    background: "#ffffff",
    color: "#555",
    borderColor: "#d0cdc6",
  },

  // Email input
  input: {
    width: "100%",
    padding: "10px 13px",
    border: "1px solid #d0cdc6",
    borderRadius: 8,
    fontSize: 14,
    color: "#1a1a1a",
    background: "#faf9f7",
    outline: "none",
    boxSizing: "border-box",
    fontFamily: "system-ui, sans-serif",
  },
  errorText: {
    fontSize: 12,
    color: "#e74c3c",
    marginTop: 5,
    fontFamily: "system-ui, sans-serif",
  },

  // Submit — matches the dark filled Buy tab
  submitBtn: {
    width: "100%",
    padding: "11px 0",
    background: "#1a1a1a",
    color: "#ffffff",
    border: "none",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 700,
    transition: "opacity 0.15s",
    fontFamily: "system-ui, sans-serif",
    marginTop: 4,
    letterSpacing: "0.1px",
  },

  disclaimer: {
    textAlign: "center",
    fontSize: 11,
    color: "#bbb",
    margin: "10px 0 0",
    fontFamily: "system-ui, sans-serif",
  },

  successTitle: {
    fontWeight: 700,
    fontSize: 17,
    color: "#1a1a1a",
    marginBottom: 8,
    fontFamily: "system-ui, sans-serif",
  },
  successText: {
    fontSize: 13,
    color: "#777",
    lineHeight: 1.55,
    fontFamily: "system-ui, sans-serif",
  },
};
