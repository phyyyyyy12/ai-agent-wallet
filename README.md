# AI Agent Wallet

为 AI Agent（如 Claude Code）设计的以太坊 Sepolia 测试网钱包。通过 MCP Server 暴露钱包工具，让 AI Agent 可以自主执行链上操作，同时提供 React 仪表盘供人类监控和管理。

## 架构

```
AI Agent (Claude Code)  ←  MCP Tools  →  Wallet Core  →  Sepolia
Human (Browser)         ←  REST API   →  Wallet Core  →  Sepolia
```

## 快速开始

### 后端

```bash
cd ai-agent-wallet
uv sync --dev

# 运行测试
.venv/bin/python -m pytest tests/ -v

# 启动 API Server（供前端使用）
.venv/bin/python src/api.py

# 启动 MCP Server（供 AI Agent 使用）
.venv/bin/python src/mcp_server.py
```

### 前端

```bash
cd web
npm install
npm run dev
# 访问 http://localhost:5173
```

### 配置为 Claude Code MCP Server

在 `~/.claude/settings.json` 中添加：

```json
{
  "mcpServers": {
    "ai-wallet": {
      "command": "/path/to/ai-agent-wallet/.venv/bin/python",
      "args": ["/path/to/ai-agent-wallet/src/mcp_server.py"]
    }
  }
}
```

## MCP 工具列表

| Tool | 说明 |
|------|------|
| `create_wallet` | 创建新钱包 |
| `import_wallet` | 导入私钥 |
| `get_balance` | 查询 ETH 余额 |
| `send_eth` | 转账（受限额约束） |
| `get_transaction` | 查询交易详情 |
| `sign_message` | 签名消息 |
| `get_wallet_info` | 钱包信息 |
| `set_spending_limit` | 设置支出限额 |
| `get_transaction_history` | 交易历史 |

## 安全策略

- 单笔限额（默认 0.1 ETH）
- 日累计限额（默认 1.0 ETH）
- 频率限制（默认 5 笔/分钟）
- 地址白名单
- 超限操作需人类审批
- 全量操作审计日志

## 文档

- [用户画像与使用场景](docs/01-user-persona.md)
- [重点问题分析](docs/02-key-problems.md)
- [架构设计](docs/03-architecture.md)
- [AI 协作过程](docs/04-ai-collaboration.md)

## 技术栈

Python 3.11+ / web3.py / FastMCP / FastAPI / React 18 / Vite / Sepolia Testnet
