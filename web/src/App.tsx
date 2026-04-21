import { useState, useEffect, useCallback } from "react";
import Dashboard from "./components/Dashboard";
import TransactionList from "./components/TransactionList";
import SecurityConfig from "./components/SecurityConfig";
import AgentLog from "./components/AgentLog";
import WalletSelector from "./components/WalletSelector";
import PendingApprovals from "./components/PendingApprovals";
import type { PendingApproval } from "./components/PendingApprovals";
import type { WalletItem } from "./components/WalletSelector";

const API = "";

export interface WalletInfo {
  loaded: boolean;
  address: string | null;
  balance_eth: string;
  chain?: {
    chain_id: number;
    block_number: number;
    gas_price_gwei: string;
    connected: boolean;
  };
}

export interface Transaction {
  tx_hash: string;
  from: string;
  to: string;
  value_eth: string;
  status: string;
  timestamp: string;
  block_number: number | null;
  gas_used: number | null;
  direction?: "in" | "out";
}

export interface LogEntry {
  timestamp: string;
  tool: string;
  params: Record<string, unknown>;
  security_check: string;
  result: string;
  duration_ms: number | null;
  tx_hash: string | null;
}

export interface SecurityPolicy {
  max_per_tx_eth: number;
  max_daily_eth: number;
  max_tx_per_minute: number;
  address_whitelist: string[];
}

type Tab = "dashboard" | "transactions" | "approvals" | "security" | "logs";

const tabs: { key: Tab; label: string }[] = [
  { key: "dashboard", label: "Dashboard" },
  { key: "transactions", label: "Transactions" },
  { key: "approvals", label: "Approvals" },
  { key: "security", label: "Security" },
  { key: "logs", label: "Agent Logs" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [wallet, setWallet] = useState<WalletInfo | null>(null);
  const [wallets, setWallets] = useState<WalletItem[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [security, setSecurity] = useState<SecurityPolicy | null>(null);
  const [approvals, setApprovals] = useState<PendingApproval[]>([]);

  const fetchAll = useCallback(async () => {
    try {
      const [w, ws, t, l, s, a] = await Promise.all([
        fetch(`${API}/api/wallet`).then((r) => r.json()),
        fetch(`${API}/api/wallets`).then((r) => r.json()),
        fetch(`${API}/api/transactions`).then((r) => r.json()),
        fetch(`${API}/api/logs`).then((r) => r.json()),
        fetch(`${API}/api/security`).then((r) => r.json()),
        fetch(`${API}/api/approvals`).then((r) => r.json()),
      ]);
      setWallet(w);
      setWallets(ws);
      setTransactions(t);
      setLogs(l);
      setSecurity(s);
      setApprovals(a);
    } catch (e) {
      console.error("Failed to fetch data:", e);
    }
  }, []);

  const handleSwitchWallet = async (address: string) => {
    await fetch(`${API}/api/wallets/switch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address }),
    });
    await fetchAll();
  };

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>AI Agent Wallet</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <WalletSelector wallets={wallets} onSwitch={handleSwitchWallet} />
          <span style={styles.network}>Sepolia Testnet</span>
        </div>
      </header>

      <nav style={styles.nav}>
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              ...styles.tabBtn,
              ...(tab === t.key ? styles.tabActive : {}),
            }}
          >
            {t.label}
            {t.key === "approvals" && approvals.length > 0 && (
              <span style={styles.badge}>{approvals.length}</span>
            )}
          </button>
        ))}
      </nav>

      <main style={styles.main}>
        {tab === "dashboard" && <Dashboard wallet={wallet} transactions={transactions} logs={logs} />}
        {tab === "transactions" && <TransactionList transactions={transactions} />}
        {tab === "approvals" && <PendingApprovals approvals={approvals} onAction={fetchAll} />}
        {tab === "security" && <SecurityConfig security={security} onUpdate={fetchAll} />}
        {tab === "logs" && <AgentLog logs={logs} />}
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    fontFamily: "'Inter', -apple-system, sans-serif",
    background: "#0a0a0f",
    color: "#e0e0e0",
    minHeight: "100vh",
    margin: 0,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "20px 32px",
    borderBottom: "1px solid #1a1a2e",
  },
  title: {
    margin: 0,
    fontSize: "24px",
    fontWeight: 700,
    background: "linear-gradient(135deg, #667eea, #764ba2)",
    WebkitBackgroundClip: "text",
    WebkitTextFillColor: "transparent",
  },
  network: {
    padding: "4px 12px",
    borderRadius: "12px",
    background: "#1a2332",
    color: "#4ade80",
    fontSize: "13px",
    fontWeight: 500,
  },
  nav: {
    display: "flex",
    gap: "4px",
    padding: "12px 32px",
    borderBottom: "1px solid #1a1a2e",
  },
  tabBtn: {
    padding: "8px 20px",
    border: "none",
    borderRadius: "8px",
    background: "transparent",
    color: "#888",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: 500,
    transition: "all 0.2s",
  },
  tabActive: {
    background: "#1a1a2e",
    color: "#fff",
  },
  badge: {
    marginLeft: "8px",
    background: "#fbbf24",
    color: "#1a1a2e",
    borderRadius: "10px",
    padding: "1px 7px",
    fontSize: "11px",
    fontWeight: 700,
  },
  main: {
    padding: "24px 32px",
  },
};
