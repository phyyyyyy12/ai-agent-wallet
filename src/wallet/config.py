"""AI Agent 钱包配置"""

from pathlib import Path

from pydantic_settings import BaseSettings


class WalletConfig(BaseSettings):
    # 以太坊 RPC
    # 备用公共节点列表（按稳定性排序）
    rpc_url: str = "https://ethereum-sepolia-rpc.publicnode.com"

    # 数据目录
    data_dir: Path = Path.home() / ".ai-agent-wallet"

    # 安全策略默认值
    max_per_tx_eth: float = 0.1
    max_daily_eth: float = 1.0
    max_tx_per_minute: int = 5

    # Keystore 加密密码（生产环境应从环境变量或密钥管理服务获取）
    keystore_password: str = "demo-password-change-in-production"

    # API 端口
    api_port: int = 8088

    model_config = {"env_prefix": "WALLET_"}

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "keystores").mkdir(exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)


config = WalletConfig()
