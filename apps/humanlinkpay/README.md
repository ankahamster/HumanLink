# HumanlinkPay

> HumanLink Agent Payment Demo
> 基于 HumanLink 硬件授权能力，为 AI Agent 支付场景提供可控执行、硬件在场确认与可审计记录。

---

## 一句话定位

**HumanlinkPay** 把 HumanLink 的指纹 + 设备签名能力接入 Agent 支付链路，实现：

- 小额交易自动放行
- 高风险交易必须经过 HumanLink 指纹授权
- 授权结果绑定具体 `PaymentIntent`
- 支付执行后保留本地审计记录、SDK 审计页和链上交易回执

---

## 核心问题

当 AI Agent 能代表用户发起链上支付时，系统需要回答三个问题：

1. 哪些支付可以自动执行？
2. 哪些支付必须要求真实用户在场授权？
3. 授权完成后，如何留下可验证、可追溯、可展示的审计记录？

HumanlinkPay 的答案是：

- Agent 负责理解自然语言并生成结构化支付意图
- Gateway 负责策略判断、Challenge 生成、Assertion 校验和链上执行
- HumanLink 设备负责提供高风险操作的人类在场授权证明

---

## Demo 场景

当前主展示场景不是合约交互，而是：

**一个测试钱包向另一个测试钱包发起 Sepolia 原生 ETH 单向转账**

示例流程：

```text
用户对 Hermes 说：
  "帮我给 0x2E5F...6A6D 转 0.0012 ETH，用途是 coffee"

1. Hermes 从自然语言中提取：
   - to
   - amount
   - purpose

2. 前端把 PaymentIntent 发给 Gateway

3. Gateway 做 Policy Check：
   - 地址是否在 allowlist
   - token 是否为 ETH
   - 金额是否超过 0.001 ETH

4. 如果 amount <= 0.001 ETH：
   - decision = ALLOW
   - 直接执行 Sepolia 转账

5. 如果 amount > 0.001 ETH：
   - decision = REQUIRE_HL
   - Gateway 创建 challenge
   - HumanLink SDK 触发设备侧指纹授权
   - Gateway 校验 assertion
   - 校验通过后继续执行 Sepolia 转账

6. 返回：
   - decision / reason
   - action_hash
   - humanlink_record_url
   - tx_hash
```

---

## 系统架构

```text
┌──────────────────────────────────────────────────────────────┐
│                        HumanlinkPay                          │
│                                                              │
│  Hermes Chat UI                                              │
│      │  自然语言                                             │
│      ▼                                                      │
│  Frontend Demo Page                                          │
│      │  PaymentIntent                                         │
│      ▼                                                      │
│  Payment Gateway                                             │
│    1. validate intent                                        │
│    2. canonicalize intent                                    │
│    3. policy decision                                        │
│    4. create challenge                                       │
│    5. call HumanLink SDK                                     │
│    6. verify assertion                                       │
│    7. execute native transfer                                │
│    8. write gateway audit                                    │
│      │                                                      │
│      ├──────────────▶ HumanLink SDK                          │
│      │                  http://127.0.0.1:8765               │
│      │                  └─ 设备授权 / audit session          │
│      │                                                      │
│      └──────────────▶ Payment Executor                       │
│                         └─ Sepolia native ETH transfer       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 当前已跑通能力

截至当前版本，下面这些链路已经跑通：

- HumanLink SDK 本地服务联通
- Gateway `POST /api/pay` 三态策略：
  - `DENY`
  - `ALLOW`
  - `REQUIRE_HL`
- 风险阈值固定为 `0.001 ETH`
- 真实 Sepolia 原生 ETH 转账 `native_transfer`
- 高风险交易触发 HumanLink 指纹授权
- Assertion 与 `action_hash` 绑定校验
- Gateway 本地审计日志输出
- HumanLink SDK 审计页自动打开
- 前端支付流程可视化
- 真实 Hermes CLI bridge 接入
- Hermes 自然聊天 -> 结构化支付参数提取 -> 自动发起支付
- 高风险授权弹窗与 30 秒倒计时

---

## 策略模型

当前最小策略为：

- `to` 不在 allowlist -> `DENY`
- `token != ETH` -> `DENY`
- `amount <= 0.001 ETH` -> `ALLOW`
- `amount > 0.001 ETH` -> `REQUIRE_HL`

对应语义：

- `DENY`：策略拒绝，不执行交易
- `ALLOW`：低风险自动放行，直接转账
- `REQUIRE_HL`：高风险，需要 HumanLink 指纹授权后继续转账

---

## PaymentIntent

当前最小字段如下：

```json
{
  "userId": "demo-user",
  "to": "0x2E5F15E329b49D4B38fFdD100E0793780966eA6D",
  "amount": "0.0012",
  "token": "ETH",
  "purpose": "coffee",
  "deadline": "2026-06-06T12:00:00Z",
  "nonce": "uuid"
}
```

Gateway 内部会进一步生成 `CanonicalPaymentIntent`，并基于它计算 `action_hash`。

---

## 目录结构

```text
apps/humanlinkpay/
├── README.md
├── agent/
│   ├── README.md
│   ├── hermes_adapter.py
│   ├── hermes_tool_schema.json
│   └── mock_agent.py
├── contracts/
│   └── DemoMerchant.sol
├── deployments/
│   └── README.md
├── docs/
│   └── local_audit.md
├── frontend/
│   ├── README.md
│   └── index.html
└── gateway/
    ├── README.md
    ├── .env
    ├── .env.example
    ├── audit.py
    ├── config.py
    ├── hermes_bridge.py
    ├── main.py
    ├── models.py
    ├── payment_executor.py
    ├── policy.py
    ├── requirements.txt
    └── sdk_client.py
```

目录说明：

| 目录 | 作用 | 当前状态 |
| --- | --- | --- |
| `agent/` | Hermes 工具层、mock 请求和 adapter | 已有可用脚本 |
| `gateway/` | 核心支付网关、策略、SDK 调用、执行与审计 | 已跑通主链路 |
| `frontend/` | 可视化 Demo 页面、聊天窗口、流程面板 | 已跑通 |
| `docs/` | 补充文档 | 已补本地审计说明 |
| `contracts/` | 合约实验区 | 当前不是主展示路径 |
| `deployments/` | 部署记录占位 | 待补充 |

---

## 快速启动

建议从仓库根目录 `HumanLink/` 打开 3 个终端，按下面顺序执行。

### 0. 前置条件

在正式启动前，请先确认：

- HumanLink 硬件和 SDK 侧链路已经可用
- 本机已安装 Hermes CLI，且 `hermes` 命令可执行
- `~/.hermes/.env` 中已配置可用的模型 API key
- Sepolia RPC 和测试钱包私钥已经准备好

### 1. 启动 HumanLink SDK

终端 A：

```bash
cd sdk
./.venv311/bin/python run_server.py
```

默认地址：

```text
http://127.0.0.1:8765
```

可选健康检查：

```bash
curl http://127.0.0.1:8765/health
```

### 2. 安装 gateway 依赖

终端 B：

```bash
cd apps/humanlinkpay/gateway
../../../sdk/.venv311/bin/pip install -r requirements.txt
```

### 3. 配置 gateway 环境变量

```bash
cd apps/humanlinkpay/gateway
cp .env.example .env
```

建议至少确认下面这些配置：

```env
HUMANLINKPAY_GATEWAY_HOST=127.0.0.1
HUMANLINKPAY_GATEWAY_PORT=8787
HUMANLINKPAY_AUTO_OPEN_DEMO_UI=true
HUMANLINKPAY_SDK_URL=http://127.0.0.1:8765
HUMANLINKPAY_THRESHOLD_ETH=0.001
HUMANLINKPAY_HERMES_COMMAND=hermes
HUMANLINKPAY_HERMES_PROVIDER=deepseek
HUMANLINKPAY_HERMES_MODEL=deepseek-chat
HUMANLINKPAY_EXECUTION_MODE=native_transfer
HUMANLINKPAY_ALLOWLIST=0x2E5F15E329b49D4B38fFdD100E0793780966eA6D
HUMANLINKPAY_WAIT_FOR_RECEIPT=true
HUMANLINKPAY_SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/YOUR_KEY
HUMANLINKPAY_PRIVATE_KEY=0xYOUR_PRIVATE_KEY
```

说明：

- `HUMANLINKPAY_ALLOWLIST` 请填写允许收款的钱包地址
- `HUMANLINKPAY_SEPOLIA_RPC_URL` 和 `HUMANLINKPAY_PRIVATE_KEY` 是真实测试网转账的必要配置
- 当前主模式建议使用 `HUMANLINKPAY_EXECUTION_MODE=native_transfer`

### 4. 启动 gateway

终端 B：

```bash
cd apps/humanlinkpay/gateway
HUMANLINKPAY_AUTO_OPEN_DEMO_UI=true \
  ../../../sdk/.venv311/bin/uvicorn \
  main:app --host 127.0.0.1 --port 8787
```

启动成功后，默认会自动在浏览器打开：

```text
http://127.0.0.1:8787/ui/payment-demo
```

也可以手动检查：

```bash
curl http://127.0.0.1:8787/health
```

### 5. 验证真实 Hermes 接入

终端 C：

```bash
curl -X POST http://127.0.0.1:8787/api/hermes/chat \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "demo-user",
    "messages": [
      { "role": "user", "content": "你好，请问你是？" }
    ]
  }'
```

预期：

- 返回真实 Hermes 中文回复
- 不再是前端本地假回复

### 6. 验证 `ALLOW` 低风险转账

```bash
curl -X POST http://127.0.0.1:8787/api/pay \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "demo-user",
    "to": "0x2E5F15E329b49D4B38fFdD100E0793780966eA6D",
    "amount": "0.0005",
    "token": "ETH",
    "purpose": "Low risk payment"
  }'
```

预期：

- `decision = ALLOW`
- 不触发 HumanLink
- 返回真实 `tx_hash`

### 7. 验证 `REQUIRE_HL` 高风险转账

```bash
curl -X POST http://127.0.0.1:8787/api/pay \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "demo-user",
    "to": "0x2E5F15E329b49D4B38fFdD100E0793780966eA6D",
    "amount": "0.0012",
    "token": "ETH",
    "purpose": "coffee"
  }'
```

预期：

- `decision = REQUIRE_HL`
- HumanLink SDK 触发设备侧指纹授权
- 授权成功后继续执行 Sepolia 转账
- 返回 `humanlink_record_url` 和 `tx_hash`

### 8. 验证前端完整链路

打开：

```text
http://127.0.0.1:8787/ui/payment-demo
```

在聊天框直接输入：

```text
帮我给 0x2E5F15E329b49D4B38fFdD100E0793780966eA6D 转 0.0012 ETH，用途是 coffee
```

预期：

1. Hermes 用自然语言回复
2. 自动提取地址、金额、用途
3. 自动发起支付
4. 高风险场景弹出 HumanLink 授权浮层和 30 秒倒计时
5. 授权成功后自动跳转到 HumanLink 审计页
6. 页面展示 Sepolia `tx_hash`

### 9. 一次性跑通检查清单

如果要确认“所有链路都跑通”，至少检查下面这些点：

- SDK `/health` 正常
- Gateway `/health` 正常
- `/api/hermes/chat` 返回真实 Hermes 回复
- `/api/pay` 的 `ALLOW` 路径成功
- `/api/pay` 的 `REQUIRE_HL` 路径成功
- 浏览器里高风险授权弹窗正常
- `humanlink_record_url` 能自动打开
- 返回的 `tx_hash` 能在 Sepolia 浏览器中查看

---

## 使用方式

### 方式 A：前端主展示

入口：

```text
http://127.0.0.1:8787/ui/payment-demo
```

当前前端能力：

- 大聊天窗口展示 Hermes 风格交互
- 聊天记录保存在浏览器本地
- 自然聊天到支付意图的过渡
- Hermes 自动提取地址、金额、用途
- 字段齐全后自动发起支付
- `DENY / ALLOW / REQUIRE_HL` 三种示例按钮
- 可视化流程状态面板
- 高风险授权弹窗与 30 秒倒计时
- 审计页等待页自动跳转到真实 `humanlink_record_url`
- Sepolia 交易链接跳转

### 方式 B：直接调 API

```bash
curl -X POST http://127.0.0.1:8787/api/pay \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "demo-user",
    "to": "0x2E5F15E329b49D4B38fFdD100E0793780966eA6D",
    "amount": "0.0012",
    "token": "ETH",
    "purpose": "coffee"
  }'
```

---

## 演示建议

### 1. `DENY`

- 收款地址不在 allowlist
- 结果：策略直接拒绝，不触发 HumanLink，不发链上交易

### 2. `ALLOW`

- 收款地址在 allowlist
- 金额 `<= 0.001 ETH`
- 结果：自动放行，直接执行 Sepolia 转账

### 3. `REQUIRE_HL`

- 收款地址在 allowlist
- 金额 `> 0.001 ETH`
- 结果：触发 HumanLink 指纹授权，成功后继续执行 Sepolia 转账

推荐直接在聊天框测试这句：

```text
帮我给 0x2E5F15E329b49D4B38fFdD100E0793780966eA6D 转 0.0012 ETH，用途是 coffee
```

预期效果：

1. Hermes 回复并展示解析结果
2. 交易请求自动填充
3. 自动调用 gateway
4. 高风险情况下弹出授权提示
5. 授权成功后跳转审计页
6. 返回 Sepolia `tx_hash`

---

## 审计与结果

当前有三层结果输出：

1. **Gateway 本地审计日志**
   - 路径：`apps/humanlinkpay/gateway/runtime/gateway_audit.jsonl`
2. **HumanLink SDK 审计页**
   - 返回字段：`humanlink_record_url`
3. **链上交易结果**
   - 返回字段：`tx_hash`
   - 可跳转 Sepolia Etherscan

本地审计补充说明见 [local_audit.md](./docs/local_audit.md)。

### 链上 / 测试网证据（如适用）

这一部分建议在最终对外演示、提交黑客松材料或写总结时补齐。可以放入：

- 合约地址
- 交易哈希
- 测试账号
- 截图
- Agent Wallet 地址
- 操作记录

建议用下面这个模板补：

```text
- 合约地址：
- 交易哈希：
- 测试账号：
- Agent Wallet 地址：
- 操作记录：
- 截图：
```

---

## 关键文件

- Gateway 入口：[main.py](./gateway/main.py)
- Hermes Bridge：[hermes_bridge.py](./gateway/hermes_bridge.py)
- 支付执行器：[payment_executor.py](./gateway/payment_executor.py)
- 策略引擎：[policy.py](./gateway/policy.py)
- Gateway 说明：[gateway/README.md](./gateway/README.md)
- Frontend 页面：[index.html](./frontend/index.html)
- Frontend 说明：[frontend/README.md](./frontend/README.md)
- Mock Agent：[mock_agent.py](./agent/mock_agent.py)
- Hermes Adapter：[hermes_adapter.py](./agent/hermes_adapter.py)
- Hermes Tool Schema：[hermes_tool_schema.json](./agent/hermes_tool_schema.json)
- DemoMerchant 合约：[DemoMerchant.sol](./contracts/DemoMerchant.sol)

---

## 当前边界

当前主路径已经明确为：

- Sepolia 测试网
- 原生 ETH 单向转账
- `native_transfer` 执行模式
- 0.001 ETH 风险阈值
- allowlist + 金额阈值 的最小策略
- HumanLink 指纹授权 + 审计页 + 本地审计日志

当前**不是**主展示路径的能力：

- `DemoMerchant.sol` 合约交互
- Escrow / Quote / Settlement 状态机
- 更复杂的预算模型
- 强活体检测、模块级 attestation、secure boot

---

## 设计原则

- **Agent 负责理解，不负责放权**
  - Hermes 可以生成支付意图，但不能绕过 Gateway 策略
- **Gateway 负责决策，不信任自然语言**
  - 只信任结构化 `PaymentIntent`
- **HumanLink 负责高风险授权**
  - 高风险动作绑定具体 `action_hash`
- **执行必须可审计**
  - 本地日志、SDK 记录页、链上结果三层可回溯

---

## 后续可扩展方向

- 从 `native_transfer` 扩展到 `DemoMerchant` 或更真实的商业支付场景
- 增加更复杂的策略引擎，例如预算、时间窗、商户级别、用途规则
- 引入更强的设备 attestation 和硬件证明链
- 为多轮 Hermes 对话增加更稳定的流式事件展示
- 增加一键启动脚本和更完整的演示手册
