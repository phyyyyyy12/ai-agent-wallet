"""AI Agent 钱包配置"""

import secrets
from pathlib import Path

from pydantic_settings import BaseSettings


_LEGACY_DEFAULT_PASSWORD = "demo-password-change-in-production"


class WalletConfig(BaseSettings):
    # 以太坊 RPC
    rpc_url: str = "https://ethereum-sepolia-rpc.publicnode.com"

    # Etherscan V2 API（用于查询收款记录）。需要免费 API Key（etherscan.io 注册）
    etherscan_api_url: str = "https://api.etherscan.io/v2/api"
    etherscan_chain_id: int = 11155111  # Sepolia
    etherscan_api_key: str = ""

    # 数据目录
    data_dir: Path = Path.home() / ".ai-agent-wallet"

    # 安全策略默认值
    max_per_tx_eth: float = 0.1
    max_daily_eth: float = 1.0
    max_tx_per_minute: int = 5

    # Keystore 加密密码：优先级 env > master_key 文件 > 自动生成
    # 留空表示使用文件机制；显式设置 env WALLET_KEYSTORE_PASSWORD 会覆盖文件
    keystore_password: str = ""

    # API 端口
    api_port: int = 8088

    model_config = {"env_prefix": "WALLET_"}

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "keystores").mkdir(exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)

    def resolve_etherscan_api_key(self) -> str:
        """优先用 env，其次从 ~/.ai-agent-wallet/.etherscan_key 文件读取。"""
        if self.etherscan_api_key:
            return self.etherscan_api_key
        key_path = self.data_dir / ".etherscan_key"
        if key_path.exists():
            return key_path.read_text().strip()
        return ""

    def resolve_keystore_password(self) -> str:
        """解析 keystore 主密码：env > master_key 文件 > 兼容/生成"""
        if self.keystore_password:
            return self.keystore_password

        self.ensure_dirs()
        master_key_path = self.data_dir / ".master_key"

        if master_key_path.exists():
            return master_key_path.read_text().strip()

        # 文件不存在：检查是否有存量 keystore
        keystore_dir = self.data_dir / "keystores"
        existing_keystores = list(keystore_dir.glob("*.json"))

        if existing_keystores:
            # 存量数据：写入旧默认密码以保持兼容
            password = _LEGACY_DEFAULT_PASSWORD
        else:
            # 新装：生成随机 32 字节密码
            password = secrets.token_urlsafe(32)

        master_key_path.write_text(password)
        master_key_path.chmod(0o600)
        return password


config = WalletConfig()
