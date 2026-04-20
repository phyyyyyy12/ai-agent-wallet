import type { WalletInfo, Transaction, LogEntry } from "../App";

interface Props {
  wallet: WalletInfo | null;
  transactions: Transaction[];
  logs: LogEntry[];
}

export default function Dashboard({ wallet, transactions, logs }: Props) {
  if (!wallet) return <p style={{ color: "#666" }}>Loading...</p>;

  const successTx = transactions.filter((t) => t.status === "success").length;
  const pendingTx = transactions.filter((t) => t.status === "pending").length;
  const recentLogs = logs.slice(0, 5);

  return (
    <div>
      {/* 状态卡片 */}
      <div style={styles.cards}>
        <div style={{ ...styles.card, borderColor: "#667eea" }}>
          <div style={styles.cardLabel}>Wallet Address</div>
          <div style={styles.cardValue}>
            {wallet.loaded ? (
              <span style={{ fontSize: "14px", fontFamily: "monospace" }}>
                {wallet.address?.slice(0, 6)}...{wallet.address?.slice(-4)}
              </span>
            ) : (
              <span style={{ color: "#f87171" }}>Not Loaded</span>
            )}
          </div>
        </div>

        <div style={{ ...styles.card, borderColor: "#4ade80" }}>
          <div style={styles.cardLabel}>Balance</div>
          <div style={styles.cardValue}>
            {parseFloat(wallet.balance_eth).toFixed(6)} ETH
          </div>
        </div>

        <div style={{ ...styles.card, borderColor: "#fbbf24" }}>
          <div style={styles.cardLabel}>Transactions</div>
          <div style={styles.cardValue}>
            {transactions.length}
            <span style={{ fontSize: "13px", color: "#888", marginLeft: "8px" }}>
              ({successTx} ok / {pendingTx} pending)
            </span>
          </div>
        </div>

        <div style={{ ...styles.card, borderColor: "#f472b6" }}>
          <div style={styles.cardLabel}>Network</div>
          <div style={styles.cardValue}>
            {wallet.chain?.connected ? (
              <>
                <span style={{ color: "#4ade80" }}>Connected</span>
                <span style={{ fontSize: "13px", color: "#888", marginLeft: "8px" }}>
                  Block #{wallet.chain.block_number}
                </span>
              </>
            ) : (
              <span style={{ color: "#f87171" }}>Disconnected</span>
            )}
          </div>
        </div>
      </div>

      {/* 最近操作 */}
      <div style={styles.section}>
        <h3 style={styles.sectionTitle}>Recent Agent Operations</h3>
        {recentLogs.length === 0 ? (
          <p style={{ color: "#666" }}>No operations yet.</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Time</th>
                <th style={styles.th}>Tool</th>
                <th style={styles.th}>Security</th>
                <th style={styles.th}>Result</th>
                <th style={styles.th}>Duration</th>
              </tr>
            </thead>
            <tbody>
              {recentLogs.map((log, i) => (
                <tr key={i} style={styles.tr}>
                  <td style={styles.td}>{log.timestamp.slice(11, 19)}</td>
                  <td style={styles.td}>
                    <code style={styles.code}>{log.tool}</code>
                  </td>
                  <td style={styles.td}>
                    <span
                      style={{
                        ...styles.badge,
                        background:
                          log.security_check === "APPROVED"
                            ? "#064e3b"
                            : log.security_check === "DENIED"
                            ? "#7f1d1d"
                            : log.security_check === "NEEDS_APPROVAL"
                            ? "#78350f"
                            : "#1e1e2e",
                        color:
                          log.security_check === "APPROVED"
                            ? "#4ade80"
                            : log.security_check === "DENIED"
                            ? "#f87171"
                            : log.security_check === "NEEDS_APPROVAL"
                            ? "#fbbf24"
                            : "#888",
                      }}
                    >
                      {log.security_check}
                    </span>
                  </td>
                  <td style={styles.td}>
                    <span style={{ fontSize: "13px" }}>
                      {log.result.length > 40
                        ? log.result.slice(0, 40) + "..."
                        : log.result}
                    </span>
                  </td>
                  <td style={styles.td}>
                    {log.duration_ms ? `${log.duration_ms}ms` : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  cards: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
    gap: "16px",
    marginBottom: "32px",
  },
  card: {
    background: "#12121a",
    borderRadius: "12px",
    padding: "20px",
    borderLeft: "3px solid",
  },
  cardLabel: {
    fontSize: "13px",
    color: "#888",
    marginBottom: "8px",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
  },
  cardValue: {
    fontSize: "20px",
    fontWeight: 600,
    color: "#fff",
  },
  section: {
    background: "#12121a",
    borderRadius: "12px",
    padding: "20px",
  },
  sectionTitle: {
    margin: "0 0 16px",
    fontSize: "16px",
    fontWeight: 600,
    color: "#ccc",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse" as const,
  },
  th: {
    textAlign: "left" as const,
    padding: "8px 12px",
    fontSize: "12px",
    color: "#666",
    textTransform: "uppercase" as const,
    borderBottom: "1px solid #1a1a2e",
  },
  tr: {
    borderBottom: "1px solid #1a1a2e",
  },
  td: {
    padding: "10px 12px",
    fontSize: "14px",
  },
  code: {
    background: "#1a1a2e",
    padding: "2px 8px",
    borderRadius: "4px",
    fontSize: "13px",
    color: "#667eea",
  },
  badge: {
    padding: "2px 8px",
    borderRadius: "4px",
    fontSize: "12px",
    fontWeight: 500,
  },
};
