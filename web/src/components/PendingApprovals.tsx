import { useState } from "react";

export interface PendingApproval {
  approval_id: string;
  from_address: string;
  to_address: string;
  amount_eth: number;
  reason: string;
  created_at: string;
  status: string;
}

interface Props {
  approvals: PendingApproval[];
  onAction: () => void;
}

export default function PendingApprovals({ approvals, onAction }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const act = async (id: string, action: "approve" | "reject") => {
    setBusy(id);
    setMessage(null);
    try {
      const resp = await fetch(`/api/approvals/${id}/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: action === "reject" ? JSON.stringify({ reason: "" }) : undefined,
      });
      const data = await resp.json();
      if (data.success) {
        setMessage(
          action === "approve"
            ? `已通过审批，tx: ${data.tx_hash?.slice(0, 12)}...`
            : `已拒绝审批 ${id}`
        );
      } else {
        setMessage(`失败: ${data.error}`);
      }
    } catch (e) {
      setMessage(`请求失败: ${e}`);
    } finally {
      setBusy(null);
      onAction();
    }
  };

  if (approvals.length === 0) {
    return (
      <div style={styles.empty}>
        <p>暂无待审批交易。</p>
        <p style={{ color: "#666", fontSize: "14px" }}>
          Agent 触发超限交易时会出现在这里，需要人类操作员手动通过或拒绝。
        </p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>待审批交易（仅人类操作员）</h3>
      {message && <div style={styles.message}>{message}</div>}
      <div style={styles.list}>
        {approvals.map((a) => (
          <div key={a.approval_id} style={styles.card}>
            <div style={styles.row}>
              <span style={styles.label}>审批 ID</span>
              <code style={styles.code}>{a.approval_id}</code>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>金额</span>
              <span style={styles.amount}>{a.amount_eth} ETH</span>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>From</span>
              <code style={styles.addr}>{a.from_address}</code>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>To</span>
              <code style={styles.addr}>{a.to_address}</code>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>触发原因</span>
              <span style={styles.reason}>{a.reason}</span>
            </div>
            <div style={styles.row}>
              <span style={styles.label}>创建时间</span>
              <span>{new Date(a.created_at).toLocaleString()}</span>
            </div>
            <div style={styles.actions}>
              <button
                onClick={() => act(a.approval_id, "approve")}
                disabled={busy === a.approval_id}
                style={{ ...styles.btn, ...styles.approveBtn }}
              >
                {busy === a.approval_id ? "处理中..." : "✓ 通过并执行"}
              </button>
              <button
                onClick={() => act(a.approval_id, "reject")}
                disabled={busy === a.approval_id}
                style={{ ...styles.btn, ...styles.rejectBtn }}
              >
                ✗ 拒绝
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { background: "#12121a", borderRadius: "12px", padding: "20px" },
  empty: { textAlign: "center", padding: "60px 0", color: "#888", background: "#12121a", borderRadius: "12px" },
  title: { margin: "0 0 16px", fontSize: "16px", fontWeight: 600, color: "#fbbf24" },
  message: {
    background: "#1e3a8a",
    color: "#bfdbfe",
    padding: "10px 14px",
    borderRadius: "8px",
    fontSize: "14px",
    marginBottom: "16px",
  },
  list: { display: "flex", flexDirection: "column", gap: "12px" },
  card: {
    background: "#1a1a2e",
    borderRadius: "8px",
    padding: "16px",
    borderLeft: "3px solid #fbbf24",
  },
  row: { display: "flex", padding: "4px 0", fontSize: "14px", alignItems: "center" },
  label: { width: "100px", color: "#888", fontSize: "12px", textTransform: "uppercase", letterSpacing: "0.5px" },
  code: { background: "#0a0a0f", padding: "2px 8px", borderRadius: "4px", fontSize: "13px", color: "#fbbf24" },
  addr: { background: "#0a0a0f", padding: "2px 8px", borderRadius: "4px", fontSize: "12px", color: "#aaa" },
  amount: { fontWeight: 600, color: "#fff" },
  reason: { color: "#f87171", fontSize: "13px" },
  actions: { display: "flex", gap: "8px", marginTop: "12px" },
  btn: {
    padding: "8px 16px",
    border: "none",
    borderRadius: "6px",
    fontSize: "13px",
    fontWeight: 500,
    cursor: "pointer",
    transition: "all 0.2s",
  },
  approveBtn: { background: "#064e3b", color: "#4ade80" },
  rejectBtn: { background: "#7f1d1d", color: "#f87171" },
};
