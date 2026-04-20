"""AI Agent 钱包 MCP Server — 供 Claude Code 等 AI Agent 调用"""

import time
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from wallet.core import WalletCore
from wallet.security import SecurityManager, OperationLog, CheckResult

mcp = FastMCP(
    "AI Agent Wallet",
    instructions="以太坊 Sepolia 测试网钱包，支持创建钱包、查询余额、转账、签名等操作。所有交易受安全策略约束。",
)

wallet = WalletCore()
security = SecurityManager()

# 启动时尝试加载已有钱包
wallet.load_wallet()


def _log(tool: str, params: dict, result: str, check: str = "N/A", tx_hash: str | None = None, start: float | None = None):
    security.log_operation(OperationLog(
        timestamp=datetime.now(timezone.utc).isoformat(),
        tool=tool,
        params=params,
        security_check=check,
        result=result,
        duration_ms=int((time.time() - start) * 1000) if start else None,
        tx_hash=tx_hash,
    ))


@mcp.tool()
def create_wallet() -> str:
    """创建一个新的以太坊钱包。返回钱包地址。私钥已加密存储，不会暴露。"""
    start = time.time()
    address = wallet.create_wallet()
    _log("create_wallet", {}, f"Created wallet: {address}", start=start)
    return f"钱包已创建\n地址: {address}\n私钥已加密存储在本地 keystore 中。\n\n请通过 Sepolia 水龙头获取测试 ETH: https://sepoliafaucet.com"


@mcp.tool()
def import_wallet(private_key: str) -> str:
    """导入已有的以太坊私钥。参数 private_key: 以 0x 开头的私钥。"""
    start = time.time()
    address = wallet.import_wallet(private_key)
    _log("import_wallet", {"private_key": "***REDACTED***"}, f"Imported: {address}", start=start)
    return f"钱包已导入\n地址: {address}"


@mcp.tool()
def get_balance(address: str = "") -> str:
    """查询 ETH 余额。address 为空则查询当前钱包余额。"""
    start = time.time()
    addr = address if address else None
    info = wallet.get_balance(addr)
    _log("get_balance", {"address": info["address"]}, f"{info['balance_eth']} ETH", start=start)
    return f"地址: {info['address']}\n余额: {info['balance_eth']} ETH"


@mcp.tool()
def send_eth(to: str, amount_eth: float) -> str:
    """发送 ETH 到指定地址。受安全策略限额约束。

    Args:
        to: 目标地址 (0x...)
        amount_eth: 发送金额（单位 ETH）
    """
    start = time.time()
    params = {"to": to, "amount_eth": amount_eth}

    # 安全检查
    check = security.check_transaction(to, amount_eth)
    if check.result == CheckResult.DENIED:
        _log("send_eth", params, f"DENIED: {check.reason}", check="DENIED", start=start)
        return f"交易被拒绝: {check.reason}"

    if check.result == CheckResult.NEEDS_APPROVAL:
        _log("send_eth", params, f"NEEDS_APPROVAL: {check.reason}", check="NEEDS_APPROVAL", start=start)
        return f"交易需要人类审批: {check.reason}\n\n请人类用户在仪表盘中确认此操作。"

    # 执行交易
    try:
        record = wallet.send_transaction(to, amount_eth)
        security.record_transaction(amount_eth)
        _log("send_eth", params, "SUCCESS", check="APPROVED", tx_hash=record.tx_hash, start=start)
        explorer_url = f"https://sepolia.etherscan.io/tx/{record.tx_hash}"
        return f"交易已发送!\nTx Hash: {record.tx_hash}\n金额: {amount_eth} ETH\n目标: {to}\n\n查看交易: {explorer_url}"
    except Exception as e:
        _log("send_eth", params, f"ERROR: {e}", check="APPROVED", start=start)
        return f"交易失败: {e}"


@mcp.tool()
def get_transaction(tx_hash: str) -> str:
    """查询交易详情。"""
    start = time.time()
    try:
        info = wallet.get_transaction(tx_hash)
        _log("get_transaction", {"tx_hash": tx_hash}, info["status"], start=start)
        return (
            f"交易详情:\n"
            f"  Hash: {info['tx_hash']}\n"
            f"  From: {info['from']}\n"
            f"  To: {info['to']}\n"
            f"  Value: {info['value_eth']} ETH\n"
            f"  Status: {info['status']}\n"
            f"  Block: {info['block_number']}"
        )
    except Exception as e:
        _log("get_transaction", {"tx_hash": tx_hash}, f"ERROR: {e}", start=start)
        return f"查询失败: {e}"


@mcp.tool()
def sign_message(message: str) -> str:
    """使用当前钱包签名消息。"""
    start = time.time()
    result = wallet.sign_message(message)
    _log("sign_message", {"message": message[:50]}, "SUCCESS", start=start)
    return f"消息签名:\n  Message: {result['message']}\n  Signature: {result['signature']}\n  Signer: {result['signer']}"


@mcp.tool()
def get_wallet_info() -> str:
    """获取当前钱包信息，包括地址、余额和链信息。"""
    start = time.time()
    if not wallet.is_loaded:
        _log("get_wallet_info", {}, "No wallet loaded", start=start)
        return "当前没有加载钱包。请使用 create_wallet 创建或 import_wallet 导入。"

    balance = wallet.get_balance()
    chain = wallet.get_chain_info()
    _log("get_wallet_info", {}, f"{balance['balance_eth']} ETH", start=start)
    return (
        f"钱包信息:\n"
        f"  地址: {balance['address']}\n"
        f"  余额: {balance['balance_eth']} ETH\n"
        f"  网络: Sepolia (Chain ID: {chain['chain_id']})\n"
        f"  最新区块: {chain['block_number']}\n"
        f"  Gas Price: {chain['gas_price_gwei']} Gwei\n"
        f"  连接状态: {'已连接' if chain['connected'] else '未连接'}"
    )


@mcp.tool()
def set_spending_limit(per_tx_eth: float = -1, daily_eth: float = -1) -> str:
    """设置支出限额。-1 表示不修改。

    Args:
        per_tx_eth: 单笔交易限额（ETH），-1 不修改
        daily_eth: 日累计限额（ETH），-1 不修改
    """
    start = time.time()
    updates = {}
    if per_tx_eth >= 0:
        updates["max_per_tx_eth"] = per_tx_eth
    if daily_eth >= 0:
        updates["max_daily_eth"] = daily_eth

    if not updates:
        policy = security.policy
    else:
        policy = security.update_policy(**updates)

    _log("set_spending_limit", updates, "Updated", start=start)
    return (
        f"当前安全策略:\n"
        f"  单笔限额: {policy.max_per_tx_eth} ETH\n"
        f"  日累计限额: {policy.max_daily_eth} ETH\n"
        f"  每分钟最大交易数: {policy.max_tx_per_minute}"
    )


@mcp.tool()
def get_transaction_history() -> str:
    """获取交易历史记录。"""
    start = time.time()
    history = wallet.get_transaction_history()
    if not history:
        _log("get_transaction_history", {}, "No transactions", start=start)
        return "暂无交易记录。"

    lines = ["交易历史:"]
    for tx in history[:20]:
        lines.append(
            f"  [{tx['timestamp'][:19]}] {tx['value_eth']} ETH → {tx['to'][:10]}... ({tx['status']})"
        )
    _log("get_transaction_history", {}, f"{len(history)} records", start=start)
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
