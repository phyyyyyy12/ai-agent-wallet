"""AI Agent 钱包单元测试"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 设置测试用临时目录
_tmp = tempfile.mkdtemp()
with patch.dict("os.environ", {"WALLET_DATA_DIR": _tmp}):
    from wallet.config import WalletConfig

    test_config = WalletConfig(data_dir=Path(_tmp))

# 用测试配置替换全局配置
import wallet.config

wallet.config.config = test_config
test_config.ensure_dirs()

from wallet.core import WalletCore, _derive_key
from wallet.security import SecurityManager, SecurityPolicy, CheckResult


class TestDeriveKey:
    def test_deterministic(self):
        salt = b"1234567890123456"
        k1 = _derive_key("password", salt)
        k2 = _derive_key("password", salt)
        assert k1 == k2

    def test_different_passwords(self):
        salt = b"1234567890123456"
        k1 = _derive_key("pass1", salt)
        k2 = _derive_key("pass2", salt)
        assert k1 != k2


class TestWalletCore:
    def test_create_wallet(self):
        w = WalletCore()
        address = w.create_wallet()
        assert address.startswith("0x")
        assert len(address) == 42
        assert w.is_loaded
        assert w.address == address

    def test_import_wallet(self):
        from eth_account import Account

        acct = Account.create()
        w = WalletCore()
        address = w.import_wallet(acct.key.hex())
        assert address == acct.address
        assert w.is_loaded

    def test_load_wallet(self):
        # create first
        w1 = WalletCore()
        addr = w1.create_wallet()

        # load in new instance
        w2 = WalletCore()
        loaded = w2.load_wallet()
        assert loaded is not None
        assert w2.is_loaded

    def test_sign_message(self):
        w = WalletCore()
        w.create_wallet()
        result = w.sign_message("hello world")
        assert "signature" in result
        assert result["signer"] == w.address

    @patch("wallet.core.Web3")
    def test_get_balance(self, mock_web3_cls):
        """测试余额查询（mock RPC）"""
        mock_w3 = MagicMock()
        mock_w3.eth.get_balance.return_value = 1000000000000000000  # 1 ETH
        mock_w3.from_wei.return_value = 1.0
        mock_web3_cls.return_value = mock_w3
        mock_web3_cls.to_checksum_address = lambda x: x
        mock_web3_cls.HTTPProvider = MagicMock()

        w = WalletCore()
        w._w3 = mock_w3
        w._address = "0x1234567890abcdef1234567890abcdef12345678"

        result = w.get_balance()
        assert result["balance_eth"] == str(1.0)

    def test_transaction_history_empty(self):
        w = WalletCore()
        assert w.get_transaction_history() == []


class TestSecurityPolicy:
    def test_default_policy(self):
        p = SecurityPolicy()
        assert p.max_per_tx_eth == test_config.max_per_tx_eth
        assert p.max_daily_eth == test_config.max_daily_eth

    def test_to_dict(self):
        p = SecurityPolicy(max_per_tx_eth=0.5, max_daily_eth=2.0)
        d = p.to_dict()
        assert d["max_per_tx_eth"] == 0.5
        assert d["max_daily_eth"] == 2.0


class TestSecurityManager:
    def test_check_within_limits(self):
        sm = SecurityManager()
        sm.update_policy(max_per_tx_eth=1.0, max_daily_eth=10.0, max_tx_per_minute=5, address_whitelist=[])
        check = sm.check_transaction("0x1234", 0.5)
        assert check.result == CheckResult.APPROVED

    def test_check_exceeds_per_tx(self):
        sm = SecurityManager()
        sm.update_policy(max_per_tx_eth=0.1, max_daily_eth=10.0, max_tx_per_minute=5, address_whitelist=[])
        check = sm.check_transaction("0x1234", 0.5)
        assert check.result == CheckResult.NEEDS_APPROVAL

    def test_check_exceeds_daily(self):
        sm = SecurityManager()
        sm.update_policy(max_per_tx_eth=1.0, max_daily_eth=0.5, max_tx_per_minute=5, address_whitelist=[])
        # 模拟已有交易
        sm.record_transaction(0.4)
        check = sm.check_transaction("0x1234", 0.2)
        assert check.result == CheckResult.NEEDS_APPROVAL

    def test_check_rate_limit(self):
        sm = SecurityManager()
        sm.update_policy(max_per_tx_eth=10.0, max_daily_eth=100.0, max_tx_per_minute=2, address_whitelist=[])
        sm.record_transaction(0.01)
        sm.record_transaction(0.01)
        check = sm.check_transaction("0x1234", 0.01)
        assert check.result == CheckResult.DENIED

    def test_check_whitelist(self):
        sm = SecurityManager()
        sm.update_policy(max_per_tx_eth=10.0, max_daily_eth=100.0, max_tx_per_minute=5, address_whitelist=["0xAAAA"])
        check = sm.check_transaction("0xBBBB", 0.01)
        assert check.result == CheckResult.NEEDS_APPROVAL

    def test_check_whitelist_pass(self):
        sm = SecurityManager()
        sm._policy = SecurityPolicy(
            max_per_tx_eth=10.0,
            max_daily_eth=100.0,
            address_whitelist=["0xAAAA"],
        )
        check = sm.check_transaction("0xaaaa", 0.01)  # 大小写不敏感
        assert check.result == CheckResult.APPROVED

    def test_update_policy(self):
        sm = SecurityManager()
        sm.update_policy(max_per_tx_eth=5.0)
        assert sm.policy.max_per_tx_eth == 5.0

    def test_log_operation(self):
        from wallet.security import OperationLog

        sm = SecurityManager()
        sm.log_operation(OperationLog(
            timestamp="2026-01-01T00:00:00Z",
            tool="test",
            params={"key": "val"},
            security_check="N/A",
            result="ok",
        ))
        logs = sm.get_logs()
        assert len(logs) >= 1
        assert logs[0]["tool"] == "test"
