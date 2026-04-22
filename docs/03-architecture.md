# AI Agent 钱包 — 架构设计

## 1. 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                      Human / Browser                          │
│                   React Dashboard (Vite)                       │
│   余额 │ 交易历史 │ 待审批(Approvals) │ 安全配置 │ Agent 日志  │
└──────────┬───────────────────────────────────────────────────┘
           │ HTTP (REST API)
           ▼
┌──────────────────────────────────────────────────────────────┐
│                     FastAPI Server                             │
│   /api/wallet  /api/wallets  /api/transactions  /api/logs     │
│   /api/security  /api/approvals  /api/approvals/{id}/approve  │
└──────────┬───────────────────────────────────────────────────┘
           │
           │  共享 Wallet Core
           │
┌──────────┴───────────────────────────────────────────────────┐
│                      MCP Server                               │
│    ┌─────────────────────────────────────────────────────┐   │
│    │  MCP Tools (AI Agent 调用)                           │   │
│    │  create_wallet │ get_balance │ send_eth │ sign_msg   │   │
│    └────────────────────┬────────────────────────────────┘   │
└─────────────────────────┼────────────────────────────────────┘
                          │
              ┌───────────▼───────────┐
              │    Security Layer      │
              │  ┌─────────────────┐  │
              │  │ 限额检查         │  │
              │  │ 频率限制         │  │
              │  │ 白名单校验       │  │
              │  │ 操作审计         │  │
              │  └─────────────────┘  │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │     Wallet Core        │
              │  ┌─────────────────┐  │
              │  │ 密钥管理         │  │
              │  │ 交易构建         │  │
              │  │ 签名引擎         │  │
              │  │ 链上查询         │  │
              │  └─────────────────┘  │
              └───────────┬───────────┘
                          │ JSON-RPC (HTTPS)
              ┌───────────▼───────────┐
              │   Ethereum Sepolia     │
              │   (Infura / Alchemy)   │
              └───────────────────────┘
```

## 2. 分层职责

### 2.1 MCP Interface Layer（MCP 接口层）

- **职责**：将钱包功能暴露为 MCP Tools，供 AI Agent 调用
- **协议**：Model Context Protocol (stdio 传输)
- **工具列表**：

| Tool | 参数 | 说明 |
|------|------|------|
| `create_wallet` | — | 创建新钱包，返回地址（不返回私钥） |
| `import_wallet` | `private_key` | 导入已有钱包 |
| `get_balance` | `address?` | 查询 ETH 余额 |
| `send_eth` | `to`, `amount_eth` | 发送 ETH（受安全策略约束） |
| `estimate_gas` | `to`, `amount_eth` | 转账前估算 Gas 费用，检查余额是否充足 |
| `get_transaction` | `tx_hash` | 查询交易详情：Hash、From、To、Value、Status、Block |
| `get_transaction_history` | `all_wallets?`, `include_incoming?` | 查询交易历史，含 tx hash；默认当前钱包，合并 Etherscan 收款 |
| `sign_message` | `message` | 签名消息 |
| `get_wallet_info` | — | 获取当前钱包地址和余额 |
| `list_wallets` | — | 列出所有本地钱包及余额，标注当前活跃钱包 |
| `switch_wallet` | `address` | 切换到指定地址的钱包 |
| `get_security_policy` | — | 查询安全策略：限额、今日已用/剩余额度、白名单 |
| `set_spending_limit` | `per_tx?`, `daily?`, `max_tx_per_minute?` | 修改支出限额（-1 表示不修改） |
| `get_whitelist` | — | 查询白名单地址列表 |
| `add_to_whitelist` | `address` | 添加地址到白名单 |
| `remove_from_whitelist` | `address` | 从白名单移除地址 |
| `list_pending_approvals` | — | 只读，列出所有待人类审批的超限交易 |
| `cancel_pending_approval` | `approval_id` | 取消 Agent 自己发起的待审批交易（仅限 pending 状态） |

> approve / reject 故意不放在 MCP 中，避免 Agent 自审批；详见下方 HTTP API。

### 2.2 HTTP API Layer（FastAPI 层）

- **职责**：为 React Dashboard 提供 REST API
- **端口**：8088
- **端点**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/wallet` | GET | 当前活跃钱包信息（地址、余额） |
| `/api/wallets` | GET | 所有本地钱包列表（地址、余额、是否活跃） |
| `/api/wallets/switch` | POST | 切换活跃钱包 `{address}` |
| `/api/transactions` | GET | 交易历史列表（合并发送 + Etherscan 收款） |
| `/api/logs` | GET | Agent 操作日志 |
| `/api/security` | GET/PUT | 安全策略查询和修改 |
| `/api/approvals` | GET | 列出待审批交易 |
| `/api/approvals/{id}/approve` | POST | 【人类专用】通过审批并执行 |
| `/api/approvals/{id}/reject` | POST | 【人类专用】拒绝审批 `{reason?}` |

### 2.3 Security Layer（安全层）

- **职责**：在交易执行前进行安全检查
- **策略配置**：持久化在 `security_policy.json`，`PUT /api/security` 修改后实时写入文件
- **实时生效**：`check_transaction()` 每次调用时重新从文件加载策略，MCP 进程无需重启即可感知 Dashboard 的策略变更（包括白名单）
- **检查流程**：

```
交易请求 → 限额检查 → 频率检查 → 白名单检查 → 通过/拒绝/需审批
```

- **返回状态**：
  - `APPROVED`：通过，可执行
  - `DENIED`：违反硬性规则，拒绝
  - `NEEDS_APPROVAL`：超出 Agent 自主范围，写入 `ApprovalManager` 队列（持久化到 `pending_approvals.json`），返回 approval ID 供人类审批

- **审批闭环**：人类操作员在 React Dashboard 的 Approvals 面板点击"通过/拒绝"，背后调用 `POST /api/approvals/{id}/approve|reject`。通过后钱包自动切换到发起地址并执行链上转账。全部决策写入审计日志。approve / reject **不暴露在 MCP 中**，Agent 物理上无法自审批。

### 2.4 Wallet Core（钱包核心层）

- **职责**：密钥管理、交易构建与签名、链上交互
- **密钥存储**：AES-256 (Fernet) 加密的 keystore 文件，权限 0600
- **主密码**：通过 `WalletConfig.resolve_keystore_password()` 解析，优先级 env > `~/.ai-agent-wallet/.master_key` 文件 > 自动生成（首次启动若有存量 keystore 则迁移旧默认密码以保持兼容）
- **Etherscan Key**：通过 `WalletConfig.resolve_etherscan_api_key()` 解析，优先级 env `WALLET_ETHERSCAN_API_KEY` > `~/.ai-agent-wallet/.etherscan_key` 文件；用于查询收款记录（Etherscan V2 API，chainid=11155111）
- **链上交互**：通过 web3.py 连接 Sepolia RPC；收款记录通过 Etherscan V2 API 拉取，与本地发送记录合并后按时间排序，以 ← / → 标注方向

### 2.5 Frontend Layer（前端展示层）

- **技术栈**：React 18 + TypeScript + Vite
- **职责**：可视化展示钱包状态，供人类监控和管理
- **页面**：
  - Dashboard 首页：余额、最近 Agent 操作
  - 交易历史：收款/转出合并，方向标识（↓ IN / ↑ OUT）
  - **Approvals 待审批**：超限交易卡片，含通过/拒绝按钮；有待审批时 tab 显示黄色角标
  - 安全配置：限额设置、白名单管理
  - Agent 日志：实时操作日志流

## 3. 数据流

### 3.1 Agent 发起转账

```
Agent (Claude Code)
  │
  ├─ MCP call: send_eth(to="0x1234...", amount_eth="0.05")
  │
  ▼
MCP Server
  │
  ├─ SecurityLayer.check_transaction(to, amount)
  │   ├─ 从文件重载最新策略（实时感知 Dashboard 修改）
  │   ├─ 检查单笔限额 / 日累计 / 频率 / 白名单
  │   │
  │   ├─ → APPROVED
  │   │     └─ WalletCore.send_transaction()
  │   │           解密私钥 → 构建交易 → 签名 → 广播 → 返回 tx_hash
  │   │
  │   ├─ → NEEDS_APPROVAL
  │   │     └─ ApprovalManager.create() 写入 pending_approvals.json
  │   │           返回 approval_id 给 Agent（等待人类在 Dashboard 操作）
  │   │
  │   └─ → DENIED（频率熔断）
  │         返回拒绝原因，不执行任何操作
  │
  ├─ 记录操作日志（含安全检查结果）
  │
  └─ 返回结果给 Agent
```

### 3.2 人类查看仪表盘

```
Browser → GET /api/wallet       → FastAPI → WalletCore.get_balance() → Sepolia RPC
Browser → GET /api/transactions → FastAPI → 本地发送记录 + Etherscan 收款，合并排序
Browser → GET /api/logs         → FastAPI → 读取 operations.jsonl
Browser → GET /api/approvals    → FastAPI → ApprovalManager.list_pending()（实时读文件）
Browser → PUT /api/security     → FastAPI → 更新 security_policy.json（MCP 实时感知）
Browser → POST /api/approvals/{id}/approve → FastAPI → 切换钱包 → 执行链上转账
Browser → POST /api/approvals/{id}/reject  → FastAPI → 标记拒绝，写入审计日志
```

## 4. 安全模型

```
┌─────────────────────────────────────────────┐
│              安全边界                         │
│                                              │
│  ┌──────────┐     ┌───────────────────────┐ │
│  │ Keystore │     │    Wallet Process      │ │
│  │ (加密)    │◄───│  私钥仅在签名时解密    │ │
│  └──────────┘     │  签名后立即清除内存    │ │
│                    └───────────┬───────────┘ │
│                                │              │
│    ┌───────────────────────────▼──────┐      │
│    │         MCP Interface            │      │
│    │  只暴露操作结果，不暴露私钥      │      │
│    └─────────────────────────────────┘      │
│                                              │
└─────────────────────────────────────────────┘
         ▲ 
         │ MCP stdio (工具调用/结果)
         │
    AI Agent (无法直接接触私钥)
```

## 5. 文件结构

```
ai-agent-wallet/
├── docs/                    # 文档
├── src/
│   ├── wallet/
│   │   ├── __init__.py
│   │   ├── config.py        # 配置（RPC URL、keystore路径、安全策略默认值）
│   │   ├── core.py          # 钱包核心（密钥管理、交易、查询）
│   │   └── security.py      # 安全策略引擎
│   ├── api.py               # FastAPI HTTP API
│   └── mcp_server.py        # MCP Server 入口
├── web/                     # React 前端
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/      # Dashboard, TransactionList, PendingApprovals, SecurityConfig, AgentLog, WalletSelector
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── tests/
│   └── test_wallet.py
├── pyproject.toml
└── README.md
```

## 6. 技术选型理由

| 选择 | 理由 |
|------|------|
| **web3.py** | Python 生态中最成熟的以太坊库，社区活跃 |
| **MCP Server** | 与 Claude Code 等 Agent 原生集成，无需额外 HTTP 层 |
| **FastAPI** | 高性能异步 API 框架，自动生成 OpenAPI 文档 |
| **Fernet 加密** | cryptography 库内置，安全性足够 Demo 场景 |
| **React + Vite** | 开发体验好，构建快，生态丰富 |
| **Sepolia 测试网** | 以太坊官方推荐的测试网，水龙头获取测试币方便 |
