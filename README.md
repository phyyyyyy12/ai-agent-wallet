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

# 运行测试（18 个，全部应通过）
PYTHONPATH=src .venv/bin/python -m pytest tests/test_wallet.py -v

# 启动 API Server（供前端使用，端口 8088）
PYTHONPATH=src .venv/bin/python src/api.py
```

### 前端

```bash
cd web
npm install
npm run dev
# 访问 http://localhost:5173
```

### 配置为 Claude Code MCP Server

```bash
# 在项目根目录执行
claude mcp add ai-wallet \
  /path/to/ai-agent-wallet/.venv/bin/python \
  -- /path/to/ai-agent-wallet/src/mcp_server.py

# 验证连接
claude mcp list
```

配置成功后重开 Claude Code 会话，即可直接调用钱包工具：

```
# 示例指令（在 Claude Code 中直接说）
帮我创建一个新钱包
查一下当前钱包余额
签名消息"I am the owner of this wallet"
```

## MCP 工具列表

| Tool | 说明 |
|------|------|
| `create_wallet` | 创建新钱包，私钥加密存储 |
| `import_wallet` | 导入已有私钥 |
| `get_wallet_info` | 查询地址、余额、链状态 |
| `get_balance` | 查询任意地址余额 |
| `send_eth` | 转账（受安全策略约束） |
| `get_transaction` | 查询交易详情 |
| `get_transaction_history` | 查询历史交易 |
| `sign_message` | 签名消息，证明地址所有权 |
| `set_spending_limit` | 设置支出限额 |

## 安全策略

- 单笔限额（默认 0.1 ETH）
- 日累计限额（默认 1.0 ETH）
- 频率限制（默认 5 笔/分钟）
- 地址白名单
- 超限操作返回 `NEEDS_APPROVAL`，需人类确认
- 全量操作审计日志（JSONL 格式）

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `WALLET_RPC_URL` | Sepolia RPC 节点 | `https://ethereum-sepolia-rpc.publicnode.com` |
| `WALLET_DATA_DIR` | 数据存储目录 | `~/.ai-agent-wallet` |
| `WALLET_KEYSTORE_PASSWORD` | keystore 加密密码 | `demo-password-change-in-production` |
| `WALLET_API_PORT` | API 端口 | `8088` |

> 生产环境请务必修改 `WALLET_KEYSTORE_PASSWORD`

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
