"""AI Agent 钱包 MCP Server — 供 Claude Code 等 AI Agent 调用"""

import time
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from wallet.core import WalletCore
from wallet.security import SecurityManager, OperationLog, CheckResult, ApprovalManager

mcp = FastMCP(
    "AI Agent Wallet",
    instructions="以太坊 Sepolia 测试网钱包，支持创建钱包、查询余额、转账、签名等操作。所有交易受安全策略约束。",
)

wallet = WalletCore()
security = SecurityManager()
approvals = ApprovalManager()

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
        approval = approvals.create(
            from_address=wallet.address or "",
            to_address=to,
            amount_eth=amount_eth,
            reason=check.reason,
        )
        _log("send_eth", params, f"NEEDS_APPROVAL: {approval.approval_id}", check="NEEDS_APPROVAL", start=start)
        return (
            f"交易需要人类审批\n"
            f"  审批 ID: {approval.approval_id}\n"
            f"  原因: {check.reason}\n"
            f"  From: {approval.from_address}\n"
            f"  To: {to}\n"
            f"  金额: {amount_eth} ETH\n\n"
            f"人类操作员请调用 approve_pending_transaction(approval_id) 确认，"
            f"或 reject_pending_transaction(approval_id) 拒绝。"
        )

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
def get_security_policy() -> str:
    """查询当前安全策略（限额、频率限制等）。"""
    start = time.time()
    policy = security.policy
    daily_spent = security.get_daily_spent()
    daily_remaining = policy.max_daily_eth - daily_spent
    _log("get_security_policy", {}, "OK", start=start)
    whitelist_info = (
        "  白名单地址:\n" + "\n".join(f"    - {a}" for a in policy.address_whitelist)
        if policy.address_whitelist
        else "  白名单: 未启用（允许向任意地址转账）"
    )
    return (
        f"当前安全策略:\n"
        f"  单笔限额: {policy.max_per_tx_eth} ETH\n"
        f"  日累计限额: {policy.max_daily_eth} ETH（今日已用 {daily_spent:.4f} ETH，剩余 {daily_remaining:.4f} ETH）\n"
        f"  每分钟最大交易数: {policy.max_tx_per_minute}\n"
        f"{whitelist_info}"
    )


@mcp.tool()
def set_spending_limit(per_tx_eth: float = -1, daily_eth: float = -1, max_tx_per_minute: int = -1) -> str:
    """设置支出限额。-1 表示不修改。

    Args:
        per_tx_eth: 单笔交易限额（ETH），-1 不修改
        daily_eth: 日累计限额（ETH），-1 不修改
        max_tx_per_minute: 每分钟最大交易数，-1 不修改
    """
    start = time.time()
    updates = {}
    if per_tx_eth >= 0:
        updates["max_per_tx_eth"] = per_tx_eth
    if daily_eth >= 0:
        updates["max_daily_eth"] = daily_eth
    if max_tx_per_minute >= 0:
        updates["max_tx_per_minute"] = max_tx_per_minute

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
def get_transaction_history(all_wallets: bool = False, include_incoming: bool = True) -> str:
    """获取交易历史记录。

    Args:
        all_wallets: 默认 False 仅显示当前钱包；True 返回本地所有钱包的发出记录
        include_incoming: 默认 True 包含通过 Etherscan 查询到的收款记录（仅当前钱包）
    """
    start = time.time()
    outgoing = wallet.get_transaction_history(all_wallets=all_wallets)
    incoming = wallet.get_incoming_transactions() if include_incoming and not all_wallets else []

    merged = sorted(outgoing + incoming, key=lambda t: t["timestamp"], reverse=True)

    if not merged:
        _log("get_transaction_history", {"all_wallets": all_wallets}, "No transactions", start=start)
        return "暂无交易记录。"

    lines = [f"交易历史{'（全部钱包）' if all_wallets else ''}:"]
    for tx in merged[:30]:
        arrow = "←" if tx.get("direction") == "in" else "→"
        peer = tx["from"] if tx.get("direction") == "in" else tx["to"]
        tx_hash = tx.get("tx_hash", "")
        hash_display = f"  Hash: {tx_hash}" if tx_hash else ""
        lines.append(
            f"  [{tx['timestamp'][:19]}] {tx['value_eth']} ETH {arrow} {peer} ({tx['status']}){hash_display}"
        )
    _log("get_transaction_history", {"all_wallets": all_wallets}, f"{len(merged)} records", start=start)
    return "\n".join(lines)


@mcp.tool()
def list_wallets() -> str:
    """列出所有本地钱包及余额。"""
    start = time.time()
    wallets = wallet.list_wallets()
    if not wallets:
        _log("list_wallets", {}, "No wallets", start=start)
        return "未找到任何钱包。"
    lines = ["本地钱包列表:"]
    for w in wallets:
        active_mark = " ← 当前" if w["active"] else ""
        lines.append(f"  {w['address']}  {w['balance_eth']} ETH{active_mark}")
    _log("list_wallets", {}, f"{len(wallets)} wallets", start=start)
    return "\n".join(lines)


@mcp.tool()
def switch_wallet(address: str) -> str:
    """切换到指定地址的钱包。

    Args:
        address: 要切换到的钱包地址（0x...）
    """
    start = time.time()
    try:
        addr = wallet.switch_wallet(address)
        balance = wallet.get_balance()
        result = f"已切换到钱包: {addr}\n余额: {balance['balance_eth']} ETH"
        _log("switch_wallet", {"address": address}, result, start=start)
        return result
    except ValueError as e:
        err = str(e)
        _log("switch_wallet", {"address": address}, f"ERROR: {err}", start=start)
        return f"切换失败: {err}"


@mcp.tool()
def list_pending_approvals() -> str:
    """列出所有待人类审批的交易。"""
    start = time.time()
    pending = approvals.list_pending()
    if not pending:
        _log("list_pending_approvals", {}, "No pending", start=start)
        return "暂无待审批交易。"
    lines = ["待审批交易:"]
    for a in pending:
        lines.append(
            f"  [{a.approval_id}] {a.amount_eth} ETH  {a.from_address[:10]}... → {a.to_address[:10]}...\n"
            f"    原因: {a.reason}\n"
            f"    创建时间: {a.created_at[:19]}"
        )
    _log("list_pending_approvals", {}, f"{len(pending)} pending", start=start)
    return "\n".join(lines)


@mcp.tool()
def add_to_whitelist(address: str) -> str:
    """向白名单添加地址。白名单启用后，向不在白名单内的地址转账需要人类审批。

    Args:
        address: 要添加的以太坊地址（0x...）
    """
    start = time.time()
    policy = security.policy
    if address.lower() in [a.lower() for a in policy.address_whitelist]:
        _log("add_to_whitelist", {"address": address}, "Already exists", start=start)
        return f"地址 {address} 已在白名单中。"
    policy.address_whitelist.append(address)
    security.update_policy(address_whitelist=policy.address_whitelist)
    _log("add_to_whitelist", {"address": address}, "Added", start=start)
    return f"已添加到白名单: {address}\n当前白名单共 {len(policy.address_whitelist)} 个地址。"


@mcp.tool()
def remove_from_whitelist(address: str) -> str:
    """从白名单移除地址。

    Args:
        address: 要移除的以太坊地址（0x...）
    """
    start = time.time()
    policy = security.policy
    original = policy.address_whitelist
    updated = [a for a in original if a.lower() != address.lower()]
    if len(updated) == len(original):
        _log("remove_from_whitelist", {"address": address}, "Not found", start=start)
        return f"地址 {address} 不在白名单中。"
    security.update_policy(address_whitelist=updated)
    _log("remove_from_whitelist", {"address": address}, "Removed", start=start)
    return f"已从白名单移除: {address}\n当前白名单共 {len(updated)} 个地址。"


@mcp.tool()
def get_whitelist() -> str:
    """查询当前地址白名单。白名单启用时，只有列表内的地址可以直接转账；其余地址需要人类审批。"""
    start = time.time()
    policy = security.policy
    _log("get_whitelist", {}, "OK", start=start)
    if not policy.address_whitelist:
        return "白名单未启用。当前允许向任意地址转账（仍受限额约束）。"
    lines = [f"白名单地址（共 {len(policy.address_whitelist)} 个）:"]
    for addr in policy.address_whitelist:
        lines.append(f"  - {addr}")
    return "\n".join(lines)


@mcp.tool()
def cancel_pending_approval(approval_id: str) -> str:
    """取消一笔由 Agent 自己发起的待审批交易。仅可取消 pending 状态的交易。

    Args:
        approval_id: 审批 ID（由 send_eth 返回）
    """
    start = time.time()
    result = approvals.mark_cancelled(approval_id)
    if not result:
        _log("cancel_pending_approval", {"approval_id": approval_id}, "Not found or not pending", start=start)
        return f"取消失败：审批 ID {approval_id} 不存在或已不是 pending 状态。"
    _log("cancel_pending_approval", {"approval_id": approval_id}, "Cancelled", start=start)
    return f"已取消审批请求 {approval_id}（{result.amount_eth} ETH → {result.to_address}）"


@mcp.tool()
def estimate_gas(to: str, amount_eth: float) -> str:
    """转账前估算 Gas 费用，并检查余额是否足够支付转账金额 + Gas。

    Args:
        to: 目标地址 (0x...)
        amount_eth: 计划发送金额（单位 ETH）
    """
    start = time.time()
    try:
        info = wallet.get_gas_info(to, amount_eth)
        status = "✓ 余额充足" if info["sufficient"] else "✗ 余额不足"
        _log("estimate_gas", {"to": to, "amount_eth": amount_eth}, status, start=start)
        return (
            f"Gas 估算:\n"
            f"  Gas Limit: {info['gas_limit']} units\n"
            f"  Gas Price: {info['gas_price_gwei']:.2f} Gwei\n"
            f"  Gas 费用: {info['gas_cost_eth']:.8f} ETH\n"
            f"  转账金额: {info['amount_eth']} ETH\n"
            f"  合计需要: {info['total_needed_eth']:.8f} ETH\n"
            f"  当前余额: {info['balance_eth']} ETH\n"
            f"  {status}"
        )
    except Exception as e:
        _log("estimate_gas", {"to": to, "amount_eth": amount_eth}, f"ERROR: {e}", start=start)
        return f"Gas 估算失败: {e}"


# 注：approve/reject 工具不暴露给 Agent，仅人类操作员通过 React Dashboard
# 调用 FastAPI 的 /api/approvals/{id}/approve | /reject 端点完成审批闭环。
# 这是真实的权限隔离——MCP 没有这些工具，Agent 即使被 prompt injection
# 诱导也无法自行通过审批。


if __name__ == "__main__":
    mcp.run()
