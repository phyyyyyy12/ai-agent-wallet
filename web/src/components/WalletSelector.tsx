import { useState } from "react";

export interface WalletItem {
  address: string;
  balance_eth: string;
  active: boolean;
}

interface Props {
  wallets: WalletItem[];
  onSwitch: (address: string) => void;
}

export default function WalletSelector({ wallets, onSwitch }: Props) {
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);

  const active = wallets.find((w) => w.active);

  const handleSwitch = async (address: string) => {
    if (switching) return;
    setSwitching(true);
    setOpen(false);
    await onSwitch(address);
    setSwitching(false);
  };

  return (
    <div style={styles.wrapper}>
      <button style={styles.trigger} onClick={() => setOpen((v) => !v)}>
        <span style={styles.dot} />
        {active
          ? `${active.address.slice(0, 6)}...${active.address.slice(-4)}`
          : "No Wallet"}
        <span style={styles.chevron}>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div style={styles.dropdown}>
          {wallets.map((w) => (
            <button
              key={w.address}
              style={{
                ...styles.item,
                ...(w.active ? styles.itemActive : {}),
              }}
              onClick={() => !w.active && handleSwitch(w.address)}
            >
              <div style={styles.itemLeft}>
                {w.active && <span style={styles.activeDot} />}
                <code style={styles.addr}>
                  {w.address.slice(0, 6)}...{w.address.slice(-4)}
                </code>
              </div>
              <span style={styles.balance}>{parseFloat(w.balance_eth).toFixed(4)} ETH</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: { position: "relative" },
  trigger: {
    display: "flex", alignItems: "center", gap: "8px",
    padding: "6px 14px", border: "1px solid #1a1a2e", borderRadius: "10px",
    background: "#12121a", color: "#e0e0e0", cursor: "pointer",
    fontSize: "13px", fontWeight: 500,
  },
  dot: {
    width: "8px", height: "8px", borderRadius: "50%", background: "#4ade80",
    display: "inline-block",
  },
  chevron: { fontSize: "10px", color: "#666", marginLeft: "2px" },
  dropdown: {
    position: "absolute", top: "calc(100% + 8px)", right: 0,
    background: "#12121a", border: "1px solid #1a1a2e", borderRadius: "10px",
    minWidth: "260px", overflow: "hidden", zIndex: 100,
    boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
  },
  item: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    width: "100%", padding: "10px 16px", border: "none",
    background: "transparent", color: "#ccc", cursor: "pointer",
    fontSize: "13px", textAlign: "left" as const,
    borderBottom: "1px solid #1a1a2e",
  },
  itemActive: { background: "#1a1a2e", cursor: "default", color: "#fff" },
  itemLeft: { display: "flex", alignItems: "center", gap: "8px" },
  activeDot: {
    width: "6px", height: "6px", borderRadius: "50%", background: "#4ade80",
  },
  addr: { fontSize: "13px", color: "inherit" },
  balance: { color: "#4ade80", fontWeight: 500, fontSize: "13px" },
};
