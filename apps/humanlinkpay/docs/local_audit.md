# HumanlinkPay 里的本地审计

## 本地审计是什么

在 `HumanlinkPay` 里，本地审计指的是**先把关键业务证据写在本机文件里**，哪怕链上锚定还没发生，也已经留下了一份可回溯记录。

当前 gateway 会把这些信息写到本地 audit log：

- `PaymentIntent` 规范化结果
- policy 决策：`ALLOW / DENY / REQUIRE_HL`
- `action_hash`
- HumanLink assertion 摘要
- 交易执行结果和 `tx_hash`

默认日志文件：

```text
apps/humanlinkpay/gateway/runtime/gateway_audit.jsonl
```

## 为什么需要本地审计

因为一次完整的 Agent 支付会同时跨过三层：

1. Agent / Gateway 的业务决策层
2. HumanLink SDK 的授权证明层
3. Sepolia 的交易执行层

链上交易只能证明“钱发出去了”或“合约事件触发了”，但不能完整表达：

- 这个请求原始 `PaymentIntent` 是什么
- 为什么这笔交易被判定为高风险
- 是否要求 HumanLink 授权
- SDK 返回的是哪一份 assertion
- 执行失败时到底卡在策略、授权，还是链上广播

本地审计就是用来补足这层上下文。

## 什么情况下会用到本地审计

### 1. 演示时

最直接的用法是 Demo 回放：

- 评委看链上 `tx_hash`
- 你再打开本地 audit log
- 展示这笔支付对应的 policy、assertion、交易结果

这样能把“支付确实发生了”和“支付前确实做了 HumanLink 授权”串起来。

### 2. 交易失败时

如果 Sepolia 广播失败或 RPC 超时：

- 链上可能没有任何结果
- 但本地审计仍能保留这次 intent、授权情况和报错

这对排查非常重要。

### 3. 用户事后追溯时

如果用户问：

- “这笔钱是谁发起的？”
- “为什么这笔超过阈值还被执行了？”
- “HumanLink 当时有没有真的触发？”

本地审计能快速回答这些问题。

### 4. 链上锚定前

并不是每次都要立刻把所有摘要上链。

在很多场景里，先本地记录，再选择是否进一步上链，是更便宜也更灵活的方式。

## 和 SDK 记录页是什么关系

你现在已经有的 SDK 记录页，处理的是：

- 这次 HumanLink 授权完成后
- 授权记录是只保留本地，还是继续做链上锚定

它关注的是**授权证明本身**。

而 `HumanlinkPay` gateway 的本地审计关注的是**业务执行上下文**：

- 支付意图
- policy 决策
- assertion 摘要
- 交易 hash
- 执行状态

所以这两层不是重复，而是互补：

- SDK 记录页：证明“人确实授权了”
- Gateway 本地审计：证明“系统因为什么决策执行了这笔支付”

## 在当前 Demo 里怎么理解

最简单的理解方式：

- SDK 负责“授权证据”
- Gateway 负责“支付证据”
- 链上负责“执行证据”

三者合起来，才是一条完整的审计链。
