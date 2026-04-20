import type { LogEntry } from "../App";

interface Props {
  logs: LogEntry[];
}

export default function AgentLog({ logs }: Props) {
  if (logs.length === 0) {
    return (
      <div style={styles.empty}>
        <p>No agent operations recorded yet.</p>
        <p style={{ color: "#666", fontSize: "14px" }}>
          Logs will appear here when the AI Agent interacts with the wallet via MCP.
        </p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Agent Operation Log</h3>
      <div style={styles.list}>
        {logs.map((log, i) => (
          <div key={i} style={styles.entry}>
            <div style={styles.entryHeader}>
              <code style={styles.tool}>{log.tool}</code>
              <span
                style={{
                  ...styles.badge,
                  background:
                    log.security_check === "APPROVED" ? "#064e3b"
                    : log.security_check === "DENIED" ? "#7f1d1d"
                    : log.security_check === "NEEDS_APPROVAL" ? "#78350f"
                    : "#1e1e2e",
                  color:
                    log.security_check === "APPROVED" ? "#4ade80"
                    : log.security_check === "DENIED" ? "#f87171"
                    : log.security_check === "NEEDS_APPROVAL" ? "#fbbf24"
                    : "#888",
                }}
              >
                {log.security_check}
              </span>
              <span style={styles.time}>
                {log.timestamp.slice(0, 19).replace("T", " ")}
              </span>
              {log.duration_ms && (
                <span style={styles.duration}>{log.duration_ms}ms</span>
              )}
            </div>

            <div style={styles.details}>
              <div>
                <span style={styles.detailLabel}>Params: </span>
                <code style={styles.detailCode}>
                  {JSON.stringify(log.params)}
                </code>
              </div>
              <div>
                <span style={styles.detailLabel}>Result: </span>
                <span>{log.result}</span>
              </div>
              {log.tx_hash && (
                <div>
                  <span style={styles.detailLabel}>Tx: </span>
                  <a
                    href={`https://sepolia.etherscan.io/tx/${log.tx_hash}`}
                    target="_blank"
                    rel="noreferrer"
                    style={styles.link}
                  >
                    {log.tx_hash.slice(0, 16)}...
                  </a>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { background: "#12121a", borderRadius: "12px", padding: "20px" },
  empty: { textAlign: "center" as const, padding: "60px 0", color: "#888" },
  title: { margin: "0 0 16px", fontSize: "16px", fontWeight: 600, color: "#ccc" },
  list: { display: "flex", flexDirection: "column" as const, gap: "8px" },
  entry: {
    padding: "12px 16px", borderRadius: "8px", background: "#0a0a0f",
    border: "1px solid #1a1a2e",
  },
  entryHeader: {
    display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px",
    flexWrap: "wrap" as const,
  },
  tool: {
    background: "#1a1a2e", padding: "2px 8px", borderRadius: "4px",
    fontSize: "13px", color: "#667eea", fontWeight: 600,
  },
  badge: { padding: "2px 8px", borderRadius: "4px", fontSize: "12px", fontWeight: 500 },
  time: { fontSize: "12px", color: "#555", marginLeft: "auto" },
  duration: { fontSize: "12px", color: "#555" },
  details: { fontSize: "13px", color: "#999", display: "flex", flexDirection: "column" as const, gap: "4px" },
  detailLabel: { color: "#666", fontWeight: 500 },
  detailCode: { fontSize: "12px", color: "#888" },
  link: { color: "#667eea", textDecoration: "none" },
};
