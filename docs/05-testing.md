# AI Agent 钱包 — 测试文档

## 1. 运行测试

```bash
cd /Users/admin/my-agent-project/ai-agent-wallet
PYTHONPATH=src .venv/bin/python -m pytest tests/test_wallet.py -v
```

预期输出：18 passed

---

## 2. 测试范围

测试覆盖两个核心模块，不测 API 端点和前端（API 层无独立业务逻辑，前端手动验证即可）。

---

## 3. 密钥派生测试（2个）

验证私钥加密的基础函数 `_derive_key` 行为正确。

| 测试 | 验证内容 |
|------|---------|
| `test_deterministic` | 相同密码 + 相同盐 → 每次派生结果一致（可重现） |
| `test_different_passwords` | 不同密码 → 派生结果不同（密码有效隔离） |

---

## 4. 钱包核心测试（6个）

| 测试 | 验证内容 |
|------|---------|
| `test_create_wallet` | 生成地址以 `0x` 开头、长度 42，钱包状态正确加载 |
| `test_import_wallet` | 导入私钥后，返回地址与原账户一致 |
| `test_load_wallet` | 创建钱包后，新实例能从 keystore 文件加载同一地址 |
| `test_sign_message` | 签名结果包含 `signature` 字段，`signer` 与当前地址一致 |
| `test_get_balance` | mock 掉 RPC 请求，验证余额返回结构正确 |
| `test_transaction_history_empty` | 新钱包交易历史为空列表 |

> **注**：`test_get_balance` 使用 mock 而非真实网络请求，避免测试依赖外部 RPC 节点的可用性。

---

## 5. 安全策略测试（8个）

覆盖 `check_transaction()` 的所有判断路径，以及策略管理功能。

| 测试 | 场景 | 预期结果 |
|------|------|---------|
| `test_check_within_limits` | 金额在单笔和日累计限额内 | `APPROVED` |
| `test_check_exceeds_per_tx` | 金额超过单笔限额 | `NEEDS_APPROVAL` |
| `test_check_exceeds_daily` | 当日累计超限 | `NEEDS_APPROVAL` |
| `test_check_rate_limit` | 1分钟内交易次数超限 | `DENIED` |
| `test_check_whitelist` | 白名单已配置，目标地址不在其中 | `NEEDS_APPROVAL` |
| `test_check_whitelist_pass` | 目标地址在白名单内（大小写不敏感） | `APPROVED` |
| `test_update_policy` | 修改限额后立即生效 | 新值可读取 |
| `test_log_operation` | 记录一条操作日志 | `get_logs()` 可查询到 |

### 三态结果说明

| 结果 | 含义 | 触发条件 |
|------|------|---------|
| `APPROVED` | 自动通过，Agent 可直接执行 | 所有检查均通过 |
| `NEEDS_APPROVAL` | 需要人类确认 | 超限额或地址不在白名单 |
| `DENIED` | 直接拒绝 | 触发频率限制（风控熔断） |

---

