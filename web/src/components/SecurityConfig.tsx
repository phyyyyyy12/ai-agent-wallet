import { useState } from "react";
import type { SecurityPolicy } from "../App";

interface Props {
  security: SecurityPolicy | null;
  onUpdate: () => void;
}

export default function SecurityConfig({ security, onUpdate }: Props) {
  const [perTx, setPerTx] = useState("");
  const [daily, setDaily] = useState("");
  const [maxRate, setMaxRate] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  if (!security) return <p style={{ color: "#666" }}>Loading...</p>;

  const handleSave = async () => {
    setSaving(true);
    setMsg("");
    const body: Record<string, number> = {};
    if (perTx) body.max_per_tx_eth = parseFloat(perTx);
    if (daily) body.max_daily_eth = parseFloat(daily);
    if (maxRate) body.max_tx_per_minute = parseInt(maxRate);

    try {
      await fetch("/api/security", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setMsg("Saved!");
      setPerTx("");
      setDaily("");
      setMaxRate("");
      onUpdate();
    } catch {
      setMsg("Failed to save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Security Policy</h3>

      <div style={styles.grid}>
        <div style={styles.item}>
          <label style={styles.label}>Per-Transaction Limit (ETH)</label>
          <div style={styles.current}>Current: {security.max_per_tx_eth} ETH</div>
          <input
            style={styles.input}
            type="number"
            step="0.01"
            placeholder="New value..."
            value={perTx}
            onChange={(e) => setPerTx(e.target.value)}
          />
        </div>

        <div style={styles.item}>
          <label style={styles.label}>Daily Limit (ETH)</label>
          <div style={styles.current}>Current: {security.max_daily_eth} ETH</div>
          <input
            style={styles.input}
            type="number"
            step="0.1"
            placeholder="New value..."
            value={daily}
            onChange={(e) => setDaily(e.target.value)}
          />
        </div>

        <div style={styles.item}>
          <label style={styles.label}>Max Transactions / Minute</label>
          <div style={styles.current}>Current: {security.max_tx_per_minute}</div>
          <input
            style={styles.input}
            type="number"
            step="1"
            placeholder="New value..."
            value={maxRate}
            onChange={(e) => setMaxRate(e.target.value)}
          />
        </div>
      </div>

      <div style={{ marginTop: "20px", display: "flex", alignItems: "center", gap: "12px" }}>
        <button style={styles.btn} onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Update Policy"}
        </button>
        {msg && <span style={{ color: msg === "Saved!" ? "#4ade80" : "#f87171", fontSize: "14px" }}>{msg}</span>}
      </div>

      <div style={styles.info}>
        <h4 style={{ margin: "0 0 8px", color: "#888" }}>How it works</h4>
        <ul style={{ margin: 0, paddingLeft: "20px", color: "#666", fontSize: "14px", lineHeight: "1.8" }}>
          <li>Transactions within limits are automatically approved for the AI Agent</li>
          <li>Transactions exceeding limits require human approval</li>
          <li>Rate limiting prevents rapid-fire transactions</li>
          <li>All operations are logged for audit</li>
        </ul>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { background: "#12121a", borderRadius: "12px", padding: "20px" },
  title: { margin: "0 0 20px", fontSize: "16px", fontWeight: 600, color: "#ccc" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "20px" },
  item: {},
  label: { display: "block", fontSize: "13px", color: "#888", marginBottom: "4px", textTransform: "uppercase" as const },
  current: { fontSize: "18px", fontWeight: 600, color: "#fff", marginBottom: "8px" },
  input: {
    width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #2a2a3e",
    background: "#0a0a0f", color: "#fff", fontSize: "14px", boxSizing: "border-box" as const,
  },
  btn: {
    padding: "10px 24px", borderRadius: "8px", border: "none",
    background: "linear-gradient(135deg, #667eea, #764ba2)", color: "#fff",
    fontSize: "14px", fontWeight: 600, cursor: "pointer",
  },
  info: {
    marginTop: "24px", padding: "16px", borderRadius: "8px", background: "#0a0a0f",
    border: "1px solid #1a1a2e",
  },
};
