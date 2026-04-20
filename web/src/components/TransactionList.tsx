import type { Transaction } from "../App";

interface Props {
  transactions: Transaction[];
}

export default function TransactionList({ transactions }: Props) {
  if (transactions.length === 0) {
    return (
      <div style={styles.empty}>
        <p>No transactions yet.</p>
        <p style={{ color: "#666", fontSize: "14px" }}>
          Transactions will appear here when the AI Agent sends ETH.
        </p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>Transaction History</h3>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Time</th>
            <th style={styles.th}>Tx Hash</th>
            <th style={styles.th}>From</th>
            <th style={styles.th}>To</th>
            <th style={styles.th}>Value</th>
            <th style={styles.th}>Status</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => (
            <tr key={tx.tx_hash} style={styles.tr}>
              <td style={styles.td}>{tx.timestamp.slice(0, 19).replace("T", " ")}</td>
              <td style={styles.td}>
                <a
                  href={`https://sepolia.etherscan.io/tx/${tx.tx_hash}`}
                  target="_blank"
                  rel="noreferrer"
                  style={styles.link}
                >
                  {tx.tx_hash.slice(0, 10)}...
                </a>
              </td>
              <td style={styles.td}>
                <code style={styles.addr}>{tx.from.slice(0, 8)}...</code>
              </td>
              <td style={styles.td}>
                <code style={styles.addr}>{tx.to.slice(0, 8)}...</code>
              </td>
              <td style={styles.td}>{tx.value_eth} ETH</td>
              <td style={styles.td}>
                <span
                  style={{
                    ...styles.badge,
                    background: tx.status === "success" ? "#064e3b" : tx.status === "pending" ? "#78350f" : "#7f1d1d",
                    color: tx.status === "success" ? "#4ade80" : tx.status === "pending" ? "#fbbf24" : "#f87171",
                  }}
                >
                  {tx.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { background: "#12121a", borderRadius: "12px", padding: "20px" },
  empty: { textAlign: "center" as const, padding: "60px 0", color: "#888" },
  title: { margin: "0 0 16px", fontSize: "16px", fontWeight: 600, color: "#ccc" },
  table: { width: "100%", borderCollapse: "collapse" as const },
  th: {
    textAlign: "left" as const, padding: "8px 12px", fontSize: "12px",
    color: "#666", textTransform: "uppercase" as const, borderBottom: "1px solid #1a1a2e",
  },
  tr: { borderBottom: "1px solid #1a1a2e" },
  td: { padding: "10px 12px", fontSize: "14px" },
  link: { color: "#667eea", textDecoration: "none" },
  addr: { fontSize: "13px", color: "#aaa" },
  badge: { padding: "2px 8px", borderRadius: "4px", fontSize: "12px", fontWeight: 500 },
};
