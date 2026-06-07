# HumanlinkPay Frontend

这是 `HumanlinkPay` 的最小演示前端。

## 入口

推荐直接通过 gateway 访问：

```text
http://127.0.0.1:8787/ui/payment-demo
```

这样页面和 `POST /api/pay` 同源，不需要额外配置 CORS。

## 当前能力

- 模拟“和 Hermes 对话”的大聊天窗口
- 聊天记录持久化保存在浏览器本地
- 把自然语言解析成结构化支付请求并自动填充到表单
- 内置三种快捷示例：
  - `DENY`
  - `ALLOW`
  - `REQUIRE_HL`
- 解释三种示例分别代表什么
- 展示交易请求 JSON
- 展示 Hermes 工具参数 JSON
- 展示 gateway 返回结果 JSON
- 展示流程面板：
  - Hermes 理解用户意图
  - 组装 PaymentIntent
  - Gateway 接收请求
  - Policy 判断
  - HumanLink 授权
  - 链上执行
  - 结果展示
- 高风险交易发起后，延迟弹出 HumanLink SDK 授权提示层
- 当返回 `humanlink_record_url` 时，默认优先打开一个“等待 HumanLink 审计页”的友好页面，再自动跳转到真实审计页
- 当返回 `tx_hash` 时，提供 Sepolia Etherscan 跳转链接

## 说明

- 当前前端展示的是“请求发起后到最终结果返回”的可视化
- Hermes 对话窗口是演示型 UI，用于把自然语言请求和工具参数映射展示出来
- 还不是实时事件流，因此中间步骤是阶段性展示，不是逐帧状态推送
- 风险阈值展示固定为 `0.001 Sepolia ETH`

## 自动打开页面

- gateway 启动后，默认会自动在本地浏览器打开：

```text
http://127.0.0.1:8787/ui/payment-demo
```

- 如需关闭，可在 `apps/humanlinkpay/gateway/.env` 里设置：

```text
HUMANLINKPAY_AUTO_OPEN_DEMO_UI=false
```

## 三个快捷示例

- `DENY`：地址不在 allowlist，Gateway 直接拒绝
- `ALLOW`：金额 `<= 0.001 ETH`，不触发 HumanLink，直接转账
- `REQUIRE_HL`：金额 `> 0.001 ETH`，触发 HumanLink 指纹授权，成功后继续转账
