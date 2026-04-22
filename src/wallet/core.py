"""AI Agent 钱包核心模块 — 密钥管理、交易构建、链上查询"""

import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from wallet.config import config


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


@dataclass
class TransactionRecord:
    tx_hash: str
    from_address: str
    to_address: str
    value_eth: str
    status: str  # "pending", "success", "failed"
    timestamp: str
    block_number: int | None = None
    gas_used: int | None = None


@dataclass
class WalletCore:
    """以太坊钱包核心"""

    _w3: Web3 = field(init=False)
    _account: Account | None = field(init=False, default=None)
    _address: str | None = field(init=False, default=None)
    _transactions: list[TransactionRecord] = field(init=False, default_factory=list)
    _nonce: int | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        config.ensure_dirs()
        self._w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        self._load_transactions()

    def _next_nonce(self) -> int:
        if self._nonce is None:
            self._nonce = self._w3.eth.get_transaction_count(self._address)
        n = self._nonce
        self._nonce += 1
        return n

    # ── 密钥管理 ──

    def create_wallet(self) -> str:
        """创建新钱包，返回地址"""
        account = Account.create(extra_entropy=secrets.token_hex(32))
        self._account = account
        self._address = account.address
        self._nonce = None
        self._save_keystore(account.key.hex())
        return account.address

    def import_wallet(self, private_key: str) -> str:
        """导入已有私钥，返回地址"""
        account = Account.from_key(private_key)
        self._account = account
        self._address = account.address
        self._nonce = None
        self._save_keystore(private_key)
        return account.address

    def load_wallet(self) -> str | None:
        """从 keystore 加载钱包"""
        keystore_dir = config.data_dir / "keystores"
        files = sorted(keystore_dir.glob("*.json"))
        if not files:
            return None
        pk = self._load_keystore(files[0])
        account = Account.from_key(pk)
        self._account = account
        self._address = account.address
        self._nonce = None
        return account.address

    def list_wallets(self) -> list[dict]:
        """列出所有本地钱包及余额"""
        keystore_dir = config.data_dir / "keystores"
        result = []
        for f in sorted(keystore_dir.glob("*.json")):
            address = f.stem
            try:
                balance_info = self.get_balance(address)
                balance_eth = balance_info["balance_eth"]
            except Exception:
                balance_eth = "0"
            result.append({
                "address": address,
                "balance_eth": balance_eth,
                "active": address == self._address,
            })
        return result

    def switch_wallet(self, address: str) -> str:
        """切换到指定地址的钱包"""
        keystore_path = config.data_dir / "keystores" / f"{address}.json"
        if not keystore_path.exists():
            raise ValueError(f"未找到钱包 {address}")
        pk = self._load_keystore(keystore_path)
        account = Account.from_key(pk)
        self._account = account
        self._address = account.address
        self._nonce = None
        return account.address

    @property
    def address(self) -> str | None:
        return self._address

    @property
    def is_loaded(self) -> bool:
        return self._account is not None

    # ── 链上查询 ──

    def get_balance(self, address: str | None = None) -> dict:
        """查询 ETH 余额"""
        addr = address or self._address
        if not addr:
            raise ValueError("No wallet loaded and no address provided")
        balance_wei = self._w3.eth.get_balance(Web3.to_checksum_address(addr))
        balance_eth = self._w3.from_wei(balance_wei, "ether")
        return {
            "address": addr,
            "balance_wei": str(balance_wei),
            "balance_eth": str(balance_eth),
        }

    def get_transaction(self, tx_hash: str) -> dict:
        """查询交易详情"""
        tx = self._w3.eth.get_transaction(tx_hash)
        receipt = None
        try:
            receipt = self._w3.eth.get_transaction_receipt(tx_hash)
        except Exception:
            pass

        return {
            "tx_hash": tx_hash,
            "from": tx["from"],
            "to": tx["to"],
            "value_eth": str(self._w3.from_wei(tx["value"], "ether")),
            "gas_price": str(tx["gasPrice"]),
            "block_number": tx.get("blockNumber"),
            "status": "success" if receipt and receipt["status"] == 1 else "pending" if not receipt else "failed",
        }

    def get_chain_info(self) -> dict:
        """获取链信息"""
        return {
            "chain_id": self._w3.eth.chain_id,
            "block_number": self._w3.eth.block_number,
            "gas_price_gwei": str(self._w3.from_wei(self._w3.eth.gas_price, "gwei")),
            "connected": self._w3.is_connected(),
        }

    # ── 交易 ──

    def send_transaction(self, to: str, amount_eth: float) -> TransactionRecord:
        """发送 ETH 转账"""
        if not self._account:
            raise ValueError("No wallet loaded")

        to_addr = Web3.to_checksum_address(to)
        value_wei = self._w3.to_wei(amount_eth, "ether")

        tx = {
            "from": self._address,
            "to": to_addr,
            "value": value_wei,
            "gas": 21000,
            "gasPrice": self._w3.eth.gas_price,
            "nonce": self._next_nonce(),
            "chainId": self._w3.eth.chain_id,
        }

        signed = self._account.sign_transaction(tx)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        record = TransactionRecord(
            tx_hash=tx_hash_hex,
            from_address=self._address,
            to_address=to,
            value_eth=str(amount_eth),
            status="pending",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._transactions.append(record)
        self._save_transactions()

        return record

    def get_gas_info(self, to: str, amount_eth: float) -> dict:
        """估算转账所需 Gas 费用，并检查余额是否充足"""
        gas_limit = 21000
        gas_price_wei = self._w3.eth.gas_price
        gas_cost_wei = gas_limit * gas_price_wei
        gas_cost_eth = float(self._w3.from_wei(gas_cost_wei, "ether"))
        gas_price_gwei = float(self._w3.from_wei(gas_price_wei, "gwei"))

        balance_info = self.get_balance()
        balance_eth = float(balance_info["balance_eth"])
        total_needed = amount_eth + gas_cost_eth

        return {
            "gas_limit": gas_limit,
            "gas_price_gwei": gas_price_gwei,
            "gas_cost_eth": gas_cost_eth,
            "amount_eth": amount_eth,
            "total_needed_eth": total_needed,
            "balance_eth": balance_eth,
            "sufficient": balance_eth >= total_needed,
        }

    def sign_message(self, message: str) -> dict:
        """签名消息"""
        if not self._account:
            raise ValueError("No wallet loaded")

        msg = encode_defunct(text=message)
        signed = self._account.sign_message(msg)
        return {
            "message": message,
            "signature": signed.signature.hex(),
            "signer": self._address,
        }

    # ── 交易历史 ──

    def get_transaction_history(self, all_wallets: bool = False) -> list[dict]:
        """获取本地记录的发送交易历史。默认仅返回当前钱包，all_wallets=True 返回全部。"""
        self._load_transactions()
        updated = False
        for t in self._transactions:
            if t.status == "pending":
                try:
                    receipt = self._w3.eth.get_transaction_receipt(t.tx_hash)
                    if receipt:
                        t.status = "success" if receipt["status"] == 1 else "failed"
                        t.block_number = receipt["blockNumber"]
                        t.gas_used = receipt["gasUsed"]
                        updated = True
                except Exception:
                    pass
        if updated:
            self._save_transactions()

        records = self._transactions
        if not all_wallets and self._address:
            current = self._address.lower()
            records = [t for t in records if t.from_address.lower() == current]

        return [
            {
                "tx_hash": t.tx_hash,
                "from": t.from_address,
                "to": t.to_address,
                "value_eth": t.value_eth,
                "status": t.status,
                "timestamp": t.timestamp,
                "block_number": t.block_number,
                "gas_used": t.gas_used,
                "direction": "out",
            }
            for t in reversed(records)
        ]

    def get_incoming_transactions(self, limit: int = 20) -> list[dict]:
        """通过 Etherscan V2 API 查询当前钱包的收款记录。需配置 WALLET_ETHERSCAN_API_KEY。"""
        if not self._address or not config.resolve_etherscan_api_key():
            return []
        params = {
            "chainid": config.etherscan_chain_id,
            "module": "account",
            "action": "txlist",
            "address": self._address,
            "sort": "desc",
            "page": 1,
            "offset": 100,
            "apikey": config.resolve_etherscan_api_key(),
        }
        try:
            resp = httpx.get(config.etherscan_api_url, params=params, timeout=10)
            data = resp.json()
        except Exception:
            return []
        if data.get("status") != "1":
            return []

        addr = self._address.lower()
        incoming = []
        for tx in data.get("result", []):
            if tx.get("to", "").lower() != addr:
                continue
            value_eth = str(self._w3.from_wei(int(tx["value"]), "ether"))
            ts = datetime.fromtimestamp(int(tx["timeStamp"]), tz=timezone.utc).isoformat()
            incoming.append({
                "tx_hash": tx["hash"],
                "from": tx["from"],
                "to": tx["to"],
                "value_eth": value_eth,
                "status": "success" if tx.get("isError") == "0" else "failed",
                "timestamp": ts,
                "block_number": int(tx["blockNumber"]),
                "direction": "in",
            })
            if len(incoming) >= limit:
                break
        return incoming

    # ── 内部方法 ──

    def _save_keystore(self, private_key: str) -> None:
        salt = secrets.token_bytes(16)
        key = _derive_key(config.resolve_keystore_password(), salt)
        f = Fernet(key)
        encrypted = f.encrypt(private_key.encode())

        keystore_path = config.data_dir / "keystores" / f"{self._address}.json"
        keystore_path.write_text(
            json.dumps({
                "address": self._address,
                "salt": salt.hex(),
                "encrypted_key": encrypted.decode(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        )
        keystore_path.chmod(0o600)

    def _load_keystore(self, path: Path) -> str:
        data = json.loads(path.read_text())
        salt = bytes.fromhex(data["salt"])
        key = _derive_key(config.resolve_keystore_password(), salt)
        f = Fernet(key)
        return f.decrypt(data["encrypted_key"].encode()).decode()

    def _save_transactions(self) -> None:
        path = config.data_dir / "transactions.json"
        records = [
            {
                "tx_hash": t.tx_hash,
                "from_address": t.from_address,
                "to_address": t.to_address,
                "value_eth": t.value_eth,
                "status": t.status,
                "timestamp": t.timestamp,
                "block_number": t.block_number,
                "gas_used": t.gas_used,
            }
            for t in self._transactions
        ]
        path.write_text(json.dumps(records, indent=2))

    def _load_transactions(self) -> None:
        path = config.data_dir / "transactions.json"
        if path.exists():
            records = json.loads(path.read_text())
            self._transactions = [
                TransactionRecord(**r) for r in records
            ]
