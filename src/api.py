"""FastAPI HTTP API — 供 React Dashboard 调用"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from wallet.core import WalletCore
from wallet.security import SecurityManager
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
wallet.load_wallet()


class SecurityUpdate(BaseModel):
    max_per_tx_eth: float | None = None
    max_daily_eth: float | None = None
    max_tx_per_minute: int | None = None


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
def get_transactions():
    return wallet.get_transaction_history()


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=config.api_port)
