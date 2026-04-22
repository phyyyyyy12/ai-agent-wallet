"""安全策略引擎 — 限额、频率、白名单、审计、审批队列"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path

from wallet.config import config


class CheckResult(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


@dataclass
class SecurityCheck:
    result: CheckResult
    reason: str


@dataclass
class OperationLog:
    timestamp: str
    tool: str
    params: dict
    security_check: str
    result: str
    duration_ms: int | None = None
    tx_hash: str | None = None


@dataclass
class SecurityPolicy:
    max_per_tx_eth: float = config.max_per_tx_eth
    max_daily_eth: float = config.max_daily_eth
    max_tx_per_minute: int = config.max_tx_per_minute
    address_whitelist: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "max_per_tx_eth": self.max_per_tx_eth,
            "max_daily_eth": self.max_daily_eth,
            "max_tx_per_minute": self.max_tx_per_minute,
            "address_whitelist": self.address_whitelist,
        }


class SecurityManager:
    def __init__(self) -> None:
        config.ensure_dirs()
        self._policy = self._load_policy()
        self._recent_txs: list[dict] = []  # {timestamp, amount_eth}
        self._logs: list[OperationLog] = []
        self._load_logs()

    @property
    def policy(self) -> SecurityPolicy:
        return self._policy

    def update_policy(self, **kwargs) -> SecurityPolicy:
        for k, v in kwargs.items():
            if hasattr(self._policy, k):
                setattr(self._policy, k, v)
        self._save_policy()
        return self._policy

    def check_transaction(self, to: str, amount_eth: float) -> SecurityCheck:
        """检查交易是否符合安全策略（每次从文件重载策略确保最新）"""
        self._policy = self._load_policy()
        # 1. 单笔限额
        if amount_eth > self._policy.max_per_tx_eth:
            return SecurityCheck(
                result=CheckResult.NEEDS_APPROVAL,
                reason=f"Amount {amount_eth} ETH exceeds per-tx limit {self._policy.max_per_tx_eth} ETH",
            )

        # 2. 日累计限额
        daily_total = self._get_daily_total() + amount_eth
        if daily_total > self._policy.max_daily_eth:
            return SecurityCheck(
                result=CheckResult.NEEDS_APPROVAL,
                reason=f"Daily total {daily_total:.4f} ETH would exceed limit {self._policy.max_daily_eth} ETH",
            )

        # 3. 频率限制
        recent_count = self._get_recent_tx_count()
        if recent_count >= self._policy.max_tx_per_minute:
            return SecurityCheck(
                result=CheckResult.DENIED,
                reason=f"Rate limit: {recent_count} txs in last minute (max {self._policy.max_tx_per_minute})",
            )

        # 4. 白名单检查
        if self._policy.address_whitelist and to.lower() not in [
            a.lower() for a in self._policy.address_whitelist
        ]:
            return SecurityCheck(
                result=CheckResult.NEEDS_APPROVAL,
                reason=f"Address {to} is not in whitelist",
            )

        return SecurityCheck(result=CheckResult.APPROVED, reason="All checks passed")

    def record_transaction(self, amount_eth: float) -> None:
        """记录交易用于限额计算"""
        self._recent_txs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "amount_eth": amount_eth,
        })

    def log_operation(self, log: OperationLog) -> None:
        """记录操作日志"""
        self._logs.append(log)
        self._append_log_file(log)

    def get_logs(self, limit: int = 50) -> list[dict]:
        """获取最近的操作日志"""
        logs = self._logs[-limit:]
        return [
            {
                "timestamp": l.timestamp,
                "tool": l.tool,
                "params": l.params,
                "security_check": l.security_check,
                "result": l.result,
                "duration_ms": l.duration_ms,
                "tx_hash": l.tx_hash,
            }
            for l in reversed(logs)
        ]

    # ── 内部方法 ──

    def _get_daily_total(self) -> float:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        total = 0.0
        for tx in self._recent_txs:
            ts = datetime.fromisoformat(tx["timestamp"])
            if ts > cutoff:
                total += tx["amount_eth"]
        return total

    def _get_recent_tx_count(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
        count = 0
        for tx in self._recent_txs:
            ts = datetime.fromisoformat(tx["timestamp"])
            if ts > cutoff:
                count += 1
        return count

    def _save_policy(self) -> None:
        path = config.data_dir / "security_policy.json"
        path.write_text(json.dumps(self._policy.to_dict(), indent=2))

    def _load_policy(self) -> SecurityPolicy:
        path = config.data_dir / "security_policy.json"
        if path.exists():
            data = json.loads(path.read_text())
            return SecurityPolicy(**data)
        policy = SecurityPolicy()
        # 保存默认策略到文件
        path.write_text(json.dumps(policy.to_dict(), indent=2))
        return policy

    def _append_log_file(self, log: OperationLog) -> None:
        path = config.data_dir / "logs" / "operations.jsonl"
        entry = json.dumps({
            "timestamp": log.timestamp,
            "tool": log.tool,
            "params": log.params,
            "security_check": log.security_check,
            "result": log.result,
            "duration_ms": log.duration_ms,
            "tx_hash": log.tx_hash,
        })
        with open(path, "a") as f:
            f.write(entry + "\n")

    def _load_logs(self) -> None:
        path = config.data_dir / "logs" / "operations.jsonl"
        if path.exists():
            for line in path.read_text().strip().split("\n"):
                if line:
                    data = json.loads(line)
                    self._logs.append(OperationLog(**data))


@dataclass
class PendingApproval:
    approval_id: str
    from_address: str
    to_address: str
    amount_eth: float
    reason: str
    created_at: str
    status: str = "pending"  # pending | approved | rejected


class ApprovalManager:
    """超限交易的审批队列。Agent 触发后写入待审批；人类操作员通过 MCP 工具确认/拒绝。"""

    def __init__(self) -> None:
        config.ensure_dirs()
        self._path = config.data_dir / "pending_approvals.json"
        self._approvals: list[PendingApproval] = []
        self._load()

    def create(self, from_address: str, to_address: str, amount_eth: float, reason: str) -> PendingApproval:
        approval = PendingApproval(
            approval_id=uuid.uuid4().hex[:12],
            from_address=from_address,
            to_address=to_address,
            amount_eth=amount_eth,
            reason=reason,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._approvals.append(approval)
        self._save()
        return approval

    def list_pending(self) -> list[PendingApproval]:
        self._load()
        return [a for a in self._approvals if a.status == "pending"]

    def get(self, approval_id: str) -> PendingApproval | None:
        self._load()
        for a in self._approvals:
            if a.approval_id == approval_id:
                return a
        return None

    def mark_approved(self, approval_id: str) -> PendingApproval | None:
        a = self.get(approval_id)
        if a and a.status == "pending":
            a.status = "approved"
            self._save()
            return a
        return None

    def mark_rejected(self, approval_id: str) -> PendingApproval | None:
        a = self.get(approval_id)
        if a and a.status == "pending":
            a.status = "rejected"
            self._save()
            return a
        return None

    def _save(self) -> None:
        self._path.write_text(json.dumps([asdict(a) for a in self._approvals], indent=2))

    def _load(self) -> None:
        if self._path.exists():
            data = json.loads(self._path.read_text())
            self._approvals = [PendingApproval(**d) for d in data]
