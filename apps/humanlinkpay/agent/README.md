# HumanlinkPay Agent Adapter

这个目录存放 `Hermes Agent -> HumanlinkPay gateway` 的最小适配层。

## 文件

- `mock_agent.py`：直接构造 `PaymentIntent` 发送到 gateway，适合本地联调
- `hermes_adapter.py`：接受 Hermes 侧的结构化参数，再转发到 gateway
- `hermes_tool_schema.json`：给 Hermes 配置工具调用时参考的输入 schema

## 接入原则

最小接入方案里，Hermes 只负责两件事：

1. 把自然语言支付意图解析成结构化参数
2. 调用 `hermes_adapter.py` 或等价适配器，把参数发给 gateway

HumanLink challenge、指纹授权、assertion 校验、交易广播都继续留在 `gateway/`。

## Hermes 期望输入

推荐传给 adapter 的结构化 JSON：

```json
{
  "to": "0x2E5F15E329b49D4B38fFdD100E0793780966eA6D",
  "amount": "0.005",
  "purpose": "Buy API access",
  "userId": "demo-user",
  "token": "ETH"
}
```

## 运行示例

命令行参数方式：

```bash
cd ../../..
python3 apps/humanlinkpay/agent/hermes_adapter.py \
  --to 0x2E5F15E329b49D4B38fFdD100E0793780966eA6D \
  --amount 0.005 \
  --purpose "Buy API access"
```

JSON 字符串方式：

```bash
cd ../../..
python3 apps/humanlinkpay/agent/hermes_adapter.py \
  --json-input '{"to":"0x2E5F15E329b49D4B38fFdD100E0793780966eA6D","amount":"0.005","purpose":"Buy API access"}'
```

stdin JSON 方式：

```bash
cd ../../..
echo '{"to":"0x2E5F15E329b49D4B38fFdD100E0793780966eA6D","amount":"0.005","purpose":"Buy API access"}' \
  | python3 apps/humanlinkpay/agent/hermes_adapter.py --stdin-json
```

## 输出

adapter 会输出 Hermes 更容易消费的结果：

```json
{
  "ok": true,
  "summary": "decision=REQUIRE_HL | Amount exceeds threshold 0.001 ETH | tx=0x...",
  "decision": "REQUIRE_HL",
  "requires_humanlink": true,
  "payment_intent": {
    "user_id": "demo-user",
    "to": "0x2e5f15e329b49d4b38ffdd100e0793780966ea6d",
    "amount": "0.005",
    "token": "ETH",
    "purpose": "Buy API access",
    "deadline": "2026-06-06T12:00:00Z",
    "nonce": "uuid"
  },
  "humanlink_record_url": "http://127.0.0.1:8765/ui/humanlink_record?audit_session_id=...",
  "tx_hash": "0x...",
  "execution_mode": "native_transfer",
  "raw": {}
}
```

## 推荐的 Hermes 调用方式

Hermes 侧如果支持“工具调用 + 结构化参数”，建议：

1. 先按自然语言解析出 `to`、`amount`、`purpose`
2. 按 `hermes_tool_schema.json` 组织参数
3. 调用 `hermes_adapter.py`
4. 把返回的 `summary`、`humanlink_record_url`、`tx_hash` 展示给用户
