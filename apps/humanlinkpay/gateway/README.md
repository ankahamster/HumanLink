# HumanlinkPay Gateway

这是 `HumanlinkPay` 的第一版网关骨架，目标是把支付意图、策略判断、HumanLink 授权和执行审计先串成一条最小可运行链路。

## 当前能力

- 提供 `POST /api/pay`
- 接收 `PaymentIntent`
- 执行三态策略：
  - `ALLOW`
  - `DENY`
  - `REQUIRE_HL`
- 对 `REQUIRE_HL` 场景调用本地 HumanLink SDK：
  - `POST /auth/challenge`
  - `POST /auth/execute/{session_id}`
  - `GET /auth/status/{session_id}`
  - `POST /audit/session`
- 写本地 gateway audit 日志
- 支持真实 Sepolia 执行：
  - `native_transfer`：两个测试钱包互转原生 ETH
  - `demo_merchant`：调用 DemoMerchant 合约并触发 `ServicePurchased`

## 目录

```text
gateway/
├── __init__.py
├── audit.py
├── config.py
├── main.py
├── models.py
├── payment_executor.py
├── policy.py
├── requirements.txt
└── sdk_client.py
```

相关补充：

- 本地审计说明见 [local_audit.md](../docs/local_audit.md)
- DemoMerchant 合约见 [DemoMerchant.sol](../contracts/DemoMerchant.sol)

## PaymentIntent

请求示例：

```json
{
  "userId": "demo-user",
  "to": "0xDemoMerchant",
  "amount": "0.005",
  "token": "ETH",
  "purpose": "Buy API access",
  "deadline": "2026-06-06T12:00:00Z",
  "nonce": "b093fd83-5f26-4a5d-b6a7-8e47f7334d29"
}
```

## 策略

首版策略固定为：

- `to` 不在 allowlist -> `DENY`
- `token != ETH` -> `DENY`
- `amount <= threshold` -> `ALLOW`
- `amount > threshold` -> `REQUIRE_HL`

默认阈值：

- `0.001 ETH`

## 运行

先启动 SDK：

```bash
cd ../../../sdk
./.venv311/bin/python run_server.py
```

再启动 gateway：

```bash
cd ..
../../sdk/.venv311/bin/pip install -r gateway/requirements.txt
cd gateway
../../sdk/.venv311/bin/uvicorn main:app --host 127.0.0.1 --port 8787
```

发送测试请求：

```bash
curl -X POST http://127.0.0.1:8787/api/pay \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "demo-user",
    "to": "0xDemoMerchant",
    "amount": "0.005",
    "token": "ETH",
    "purpose": "Buy API access"
  }'
```

## 执行模式

- `stub`：只返回伪造 `tx_hash`，不广播交易
- `native_transfer`：用本地私钥向 `PaymentIntent.to` 发起 Sepolia 原生 ETH 转账
- `demo_merchant`：调用 DemoMerchant 合约 `purchase()`，并触发 `ServicePurchased`

## 环境变量

- `HUMANLINKPAY_SDK_URL`：SDK 地址，默认 `http://127.0.0.1:8765`
- `HUMANLINKPAY_THRESHOLD_ETH`：授权阈值，默认 `0.001`
- `HUMANLINKPAY_ALLOWLIST`：收款地址白名单，逗号分隔
- `HUMANLINKPAY_EXECUTION_MODE`：`stub` / `native_transfer` / `demo_merchant`
- `HUMANLINKPAY_SEPOLIA_RPC_URL`：Sepolia RPC
- `HUMANLINKPAY_PRIVATE_KEY`：发起交易的钱包私钥
- `HUMANLINKPAY_CHAIN_ID`：默认 `11155111`
- `HUMANLINKPAY_DEMO_MERCHANT_ADDRESS`：DemoMerchant 合约地址，`demo_merchant` 模式必填
- `HUMANLINKPAY_WAIT_FOR_RECEIPT`：是否等待链上回执，默认 `true`
- `HUMANLINKPAY_AUDIT_LOG_PATH`：gateway 日志路径

说明：

- Gateway 会优先读取 `apps/humanlinkpay/gateway/.env`
- 如果没有设置，也会回退读取根目录 `contracts/.env`

## Mock Agent

已补一个最小请求脚本：

```bash
cd ../../..
python3 apps/humanlinkpay/agent/mock_agent.py \
  --to 0xRecipientOrDemoMerchant \
  --amount 0.005 \
  --purpose "Buy API access"
```

## 下一步

- 为 DemoMerchant 增加部署脚本或部署说明
- 增加前端页面和演示脚本
- 补更完整的 assertion 校验与错误展示
