// FloatingAlertButton.jsx
// A floating bell icon (bottom-right) that opens the EmailSubscribe form in a modal.
// Drop both this file and EmailSubscribe.jsx into your project, then add:
//   <FloatingAlertButton /> anywhere in your root layout (e.g. App.jsx)

import { useState, useEffect, useRef } from "react";
import EmailSubscribe from "./EmailSubscribe";

export default function FloatingAlertButton() {
  const [open, setOpen] = useState(false);
  const modalRef = useRef(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Close on backdrop click
  const handleBackdrop = (e) => {
    if (modalRef.current && !modalRef.current.contains(e.target)) {
      setOpen(false);
    }
  };

  return (
    <>
      {/* Floating bell button */}
      <button
        onClick={() => setOpen(true)}
        title="Get price drop alerts"
        style={styles.fab}
      >
        <BellIcon />
        <span style={styles.fabLabel}>Alerts</span>
      </button>

      {/* Modal overlay */}
      {open && (
        <div style={styles.overlay} onMouseDown={handleBackdrop}>
          <div ref={modalRef} style={styles.modal}>
            {/* Close button */}
            <button onClick={() => setOpen(false)} style={styles.closeBtn}>
              ✕
            </button>
            <EmailSubscribe onSuccess={() => setTimeout(() => setOpen(false), 2200)} />
          </div>
        </div>
      )}
    </>
  );
}

function BellIcon() {
  return (
    <svg
      width="18" height="18" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2.2"
      strokeLinecap="round" strokeLinejoin="round"
    >
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

const styles = {
  // Floating action button — bottom right, matches site dark style
  fab: {
    position: "fixed",
    bottom: 28,
    right: 28,
    zIndex: 1000,
    display: "flex",
    alignItems: "center",
    gap: 7,
    background: "#1a1a1a",
    color: "#ffffff",
    border: "none",
    borderRadius: 50,
    padding: "11px 18px 11px 14px",
    fontSize: 13,
    fontWeight: 700,
    fontFamily: "system-ui, -apple-system, sans-serif",
    cursor: "pointer",
    boxShadow: "0 4px 20px rgba(0,0,0,0.22)",
    transition: "transform 0.15s ease, box-shadow 0.15s ease",
    letterSpacing: "0.1px",
  },
  fabLabel: {
    lineHeight: 1,
  },

  // Backdrop
  overlay: {
    position: "fixed",
    inset: 0,
    zIndex: 1100,
    background: "rgba(0,0,0,0.35)",
    backdropFilter: "blur(3px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
  },

  // Modal container
  modal: {
    position: "relative",
    width: "100%",
    maxWidth: 440,
    animation: "fadeUp 0.2s ease",
  },

  // X close button
  closeBtn: {
    position: "absolute",
    top: -14,
    right: -14,
    zIndex: 10,
    width: 32,
    height: 32,
    borderRadius: "50%",
    background: "#1a1a1a",
    color: "#fff",
    border: "none",
    fontSize: 13,
    fontWeight: 700,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
    fontFamily: "system-ui, sans-serif",
  },
};

// Inject the fade-up keyframe once
if (typeof document !== "undefined") {
  const styleId = "dxb-modal-anim";
  if (!document.getElementById(styleId)) {
    const el = document.createElement("style");
    el.id = styleId;
    el.textContent = `
      @keyframes fadeUp {
        from { opacity: 0; transform: translateY(16px); }
        to   { opacity: 1; transform: translateY(0); }
      }
    `;
    document.head.appendChild(el);
  }
}
