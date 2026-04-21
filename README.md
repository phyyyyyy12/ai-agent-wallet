# AI Agent Wallet

为 AI Agent（如 Claude Code）设计的以太坊 Sepolia 测试网钱包。通过 MCP Server 暴露钱包工具，让 AI Agent 可以自主执行链上操作，同时提供 React 仪表盘供人类监控和管理。

## 架构

```
AI Agent (Claude Code)  ←  MCP Tools  →  Security Layer  →  Wallet Core  →  Sepolia
Human (Browser)         ←  REST API   →  Security Layer  →  Wallet Core  →  Sepolia
```

## 快速开始

### 环境要求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)（Python 包管理器）
- Node.js 18+

### 后端

```bash
cd ai-agent-wallet

# 安装依赖
uv sync --dev

# 运行测试
PYTHONPATH=src .venv/bin/python -m pytest tests/test_wallet.py -v

# 启动 API Server（供前端使用，端口 8088）
WALLET_ETHERSCAN_API_KEY=your_key .venv/bin/python -m uvicorn src.api:app --port 8088 --reload
```

### 前端

```bash
cd web
npm install
npm run dev
# 访问 http://localhost:5173
```

### 配置为 MCP Server

在项目根目录（或 `~/.claude/`）创建 `.mcp.json`：

```json
{
  "mcpServers": {
    "ai-wallet": {
      "command": "/path/to/ai-agent-wallet/.venv/bin/python",
      "args": ["/path/to/ai-agent-wallet/src/mcp_server.py"],
      "env": {
        "WALLET_ETHERSCAN_API_KEY": "your_key"
      }
    }
  }
}
```

重启 Claude Code / Cursor 后即可直接调用钱包工具。

## MCP 工具列表

| Tool | 说明 |
|------|------|
| `create_wallet` | 创建新钱包，私钥加密存储 |
| `import_wallet` | 导入已有私钥 |
| `get_wallet_info` | 查询地址、余额、链状态 |
| `get_balance` | 查询任意地址余额 |
| `send_eth` | 转账（受安全策略约束） |
| `get_transaction` | 查询交易详情 |
| `get_transaction_history` | 查询历史交易，合并收款记录，← / → 标注方向 |
| `sign_message` | 签名消息，证明地址所有权 |
| `set_spending_limit` | 设置支出限额 |
| `list_wallets` | 列出所有本地钱包及余额 |
| `switch_wallet` | 切换当前活跃钱包 |
| `list_pending_approvals` | 查看待人类审批的超限交易（只读） |

> approve / reject 不在 MCP 工具集中，仅人类可通过 React Dashboard 操作，从根本上防止 Agent 自审批。

## 安全策略

- 单笔限额（默认 0.1 ETH）/ 日累计限额（默认 1.0 ETH）/ 频率限制（默认 5 笔/分钟）/ 地址白名单
- 超限操作写入待审批队列，生成 approval ID；**仅人类可在 Dashboard 点击通过/拒绝**，Agent 无法自审批
- 私钥加密存储，主密码自动生成至 `~/.ai-agent-wallet/.master_key`（0600），不硬编码在源码中
- 全量操作审计日志（JSONL 格式），每次工具调用均留痕

## 环境变量 / 本地配置文件

| 变量 | 说明 | 默认行为 |
|------|------|--------|
| `WALLET_RPC_URL` | Sepolia RPC 节点 | 使用公共节点 |
| `WALLET_DATA_DIR` | 数据存储目录 | `~/.ai-agent-wallet` |
| `WALLET_KEYSTORE_PASSWORD` | keystore 加密密码 | 自动读取 `~/.ai-agent-wallet/.master_key`，首次启动自动生成 |
| `WALLET_ETHERSCAN_API_KEY` | Etherscan API Key（收款查询） | 自动读取 `~/.ai-agent-wallet/.etherscan_key` |
| `WALLET_API_PORT` | API 端口 | `8088` |

env 优先级高于本地文件。本地文件权限均为 0600，可直接编辑替换。

## 文档

- [项目完整介绍](docs/00-project-intro.md)
- [用户画像与使用场景](docs/01-user-persona.md)
- [重点问题分析](docs/02-key-problems.md)
- [架构设计](docs/03-architecture.md)
- [AI 协作过程](docs/04-ai-collaboration.md)
- [测试说明](docs/05-testing.md)

## 技术栈

- 后端：Python 3.11 / web3.py / FastMCP / FastAPI / cryptography
- 前端：React 18 / TypeScript / Vite
- 区块链：Ethereum Sepolia Testnet
- 包管理：uv
