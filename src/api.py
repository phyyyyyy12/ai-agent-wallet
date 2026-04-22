"""FastAPI HTTP API — 供 React Dashboard 调用"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dataclasses import asdict

from wallet.core import WalletCore
from wallet.security import SecurityManager, ApprovalManager
from wallet.config import config

app = FastAPI(title="AI Agent Wallet API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

wallet = WalletCore()
security = SecurityManager()
approvals = ApprovalManager()
wallet.load_wallet()


class SecurityUpdate(BaseModel):
    max_per_tx_eth: float | None = None
    max_daily_eth: float | None = None
    max_tx_per_minute: int | None = None
    address_whitelist: list[str] | None = None


@app.get("/api/wallet")
def get_wallet():
    if not wallet.is_loaded:
        return {"loaded": False, "address": None, "balance_eth": "0"}
    try:
        balance = wallet.get_balance()
    except Exception:
        balance = {"address": wallet.address, "balance_wei": "0", "balance_eth": "0"}
    try:
        chain = wallet.get_chain_info()
    except Exception:
        chain = {"chain_id": 0, "block_number": 0, "gas_price_gwei": "0", "connected": False}
    return {
        "loaded": True,
        "address": balance["address"],
        "balance_eth": balance["balance_eth"],
        "chain": chain,
    }


@app.get("/api/transactions")
def get_transactions(all_wallets: bool = False, include_incoming: bool = True):
    outgoing = wallet.get_transaction_history(all_wallets=all_wallets)
    incoming = wallet.get_incoming_transactions() if include_incoming and not all_wallets else []
    merged = outgoing + incoming
    merged.sort(key=lambda t: t["timestamp"], reverse=True)
    return merged


@app.get("/api/logs")
def get_logs(limit: int = 50):
    return security.get_logs(limit)


@app.get("/api/security")
def get_security():
    return security.policy.to_dict()


@app.put("/api/security")
def update_security(body: SecurityUpdate):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    policy = security.update_policy(**updates)
    return policy.to_dict()


@app.get("/api/wallets")
def list_wallets():
    return wallet.list_wallets()


class SwitchWalletRequest(BaseModel):
    address: str


@app.post("/api/wallets/switch")
def switch_wallet(body: SwitchWalletRequest):
    try:
        address = wallet.switch_wallet(body.address)
        balance = wallet.get_balance()
        return {"success": True, "address": address, "balance_eth": balance["balance_eth"]}
    except ValueError as e:
        return {"success": False, "error": str(e)}


# ── 审批闭环（仅 Dashboard / 人类操作员） ──


@app.get("/api/approvals")
def list_approvals():
    return [asdict(a) for a in approvals.list_pending()]


@app.post("/api/approvals/{approval_id}/approve")
def approve(approval_id: str):
    a = approvals.get(approval_id)
    if not a:
        return {"success": False, "error": f"未找到审批 {approval_id}"}
    if a.status != "pending":
        return {"success": False, "error": f"该审批已是 {a.status} 状态"}

    if not wallet.address or wallet.address.lower() != a.from_address.lower():
        try:
            wallet.switch_wallet(a.from_address)
        except ValueError as e:
            return {"success": False, "error": f"无法切换到发起钱包: {e}"}

    approvals.mark_approved(approval_id)
    try:
        record = wallet.send_transaction(a.to_address, a.amount_eth)
        security.record_transaction(a.amount_eth)
        return {
            "success": True,
            "approval_id": approval_id,
            "tx_hash": record.tx_hash,
            "explorer_url": f"https://sepolia.etherscan.io/tx/{record.tx_hash}",
        }
    except Exception as e:
        return {"success": False, "error": f"审批已通过但执行失败: {e}"}


class RejectRequest(BaseModel):
    reason: str = ""


@app.post("/api/approvals/{approval_id}/reject")
def reject(approval_id: str, body: RejectRequest = RejectRequest()):
    a = approvals.mark_rejected(approval_id)
    if not a:
        return {"success": False, "error": f"未找到该审批 ID 或其已被处理"}
    return {"success": True, "approval_id": approval_id, "reason": body.reason}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.api_port)
