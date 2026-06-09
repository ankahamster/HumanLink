# HumanLinkPay

> HumanLink Agent Payment Demo
> 基于 HumanLink 硬件授权能力，为 AI Agent 支付场景提供可控执行、硬件在场确认与可审计记录。

***

## HumanLink 背景：Agent 时代的人类授权基础设施

> HumanLinkPay 是构建在 **HumanLink** 通用协议之上的 Agent 支付场景 Demo。理解 HumanLinkPay 的「硬件在场授权」能力，需要先了解底层 HumanLink 协议的设计。

<br />

### HumanLink 项目概述

**一句话**：AI Agent 时代的人类在场授权基础设施。让任何人在任何 Agent 执行高风险操作前，留下密码学级别的不可伪造授权记录。

类比：MCP 定义了 Agent 如何调用工具，HumanLink 定义了 Agent 执行高风险操作前如何留下不可伪造的人类授权记录。

<br />

### 核心问题

2025—2026 年，Agent 已经在替用户转账、发邮件、删文件。出事后，三方都没有可独立核验的证据：

- 用户说「我没授权过」
- 平台说「我们有操作日志」
- 用户说「日志是你们自己写的，谁知道真不真」

现有的「授权」只是软件 token——都由平台单方生成，用户无法独立核实，法律上无法举证。HumanLink 解决的是：**执行的那一刻，有没有留下真人物理授权的密码学证明。**

<br />

### 定位：Agent 时代的人类授权基础设施

| 类比            | 解决什么                         | 核心产品         | 谁付费                            |
| :------------ | :--------------------------- | :----------- | :----------------------------- |
| MCP           | Agent 怎么调用工具                 | 协议 + SDK     | Agent 开发者                      |
| AI Gateway    | Agent 流量路由和管控                | 策略引擎 + API   | 平台运营商                          |
| **HumanLink** | **Agent 执行前如何留下不可伪造的人类授权记录** | **协议 + SDK** | **Agent 平台（云端集成）/ 个人用户（本地集成）** |

Agent 平台集成 HumanLink，用户每次授权高风险操作都会生成一份**密码学断言**：绑定了具体操作参数、由用户的物理生物特征触发、由防篡改安全芯片签名、可链上核验。

出事后，平台拿出这份断言，链上验证一行代码，证明链完整：**"这个操作，在这个时刻，有一个已注册的人类物理在场并主动确认了。"**

<br />

### 核心设计原则

**一次按压 = 一份断言 = 一次授权，不缓存，不复用。**

每一次物理按压转化为一份密码学断言（Assertion），直接绑定触发它的具体操作。断言即用即弃，无 TTL，无复用窗口。人在场（Present）本身就是授权的物理证据。

HumanLink 不重在构建封闭硬件安全系统，而是通过开放接口、模块化硬件和统一验证协议，实现可验证、可审计、可扩展的人类授权基础设施。三大原则：

- **协议优先，硬件作为可信执行载体** — 重在构建开放式授权协议，非单一硬件产品。协议层定义 `Challenge`、`actionHash`、`HumanPresenceAssertion`、验证流程和审计接口；硬件负责执行人类在场验证、保护不可导出私钥，并对操作绑定的授权上下文签名。
- **开放接入，基于 HAI 抽象接口** — 当前 ESP32 + JM-101 + ATECC608A 是参考实现，HAI 不绑定特定硬件，重在定义合规 Issuer 的能力要求和输出格式。四个开放维度：硬件可替换、接入方通过统一 SDK 调用、不同 verifier 可独立验签、不同审计系统可跨平台追溯。
- **安全原则参考封闭硬件系统，工程路线不依赖封闭生态** — 参考硬件根信任（外设、链路、固件、签名可信）、私钥不可导出、可信确认（用户确认内容与最终签名内容一致）、上下文绑定签名和防重放等关键机制，但不复刻封闭生态。

<br />

### 硬件架构

当前参考实现采用**分立式架构**：ESP32 作为安全飞地控制器，通过 USB Serial 连接主机，内部通过 UART 调度 JM-101 指纹传感器，通过 I2C 调度 ATECC608A 安全芯片。

```
┌─────────────────── 硬件证明层 / TEE (Secure Enclave) ───────────────────────┐
│                                                                             │
│  [JM-101 指纹] <── UART ──> [ESP32 微控制器] <── I2C ──> [ATECC608A 芯片]  │
│    (智能模组)               (局部大脑)                   (硬件私钥黑盒)      │
│  输出: 匹配ID与得分          拼接哈希 H_final            ECDSA P-256 签名   │
│  (生物特征不出模块)          (ID+得分+SN+H_doc)                             │
│                                                                             │
└──────────────────────────────↑──┼──────────────────────────────────────────┘
       输入：挑战值哈希 H_doc    │  │   输出: 芯片硬件签名 (sig)
                                │  ↓
┌──────────────────── 用户本机 (PC/Mac/Linux) ────────────────────────┐
│                                                                    │
│  [Agent / OpenClaw]   [云端 Challenge（WebSocket）]             │
│          │                          │                              │
│          └──────────────┬───────────┘                              │
│                         ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  HumanLink SDK 守护进程（Python）                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

| 组件         | 型号                  | 角色                                | 接口              |
| ---------- | ------------------- | --------------------------------- | --------------- |
| 微控制器       | ESP32-WROOM-32      | 安全飞地控制器：接收 H\_doc、调度传感器与安全芯片、返回签名 | USB Serial ↔ PC |
| 指纹传感器      | JM-101 (FPM383C)    | 光学指纹采集与本地模板匹配，生物数据不出模块            | UART ↔ ESP32    |
| 安全芯片       | Microchip ATECC608A | 设备私钥存储、ECDSA P-256 签名，私钥不可读出      | I2C ↔ ESP32     |
| USB-Serial | CH340 / CP2102      | 主机通信桥梁                            | USB ↔ PC        |

<br />

### 竞品空白

| 竞品方向                | 代表                    | 它解决的            | 它解决不了的                  |
| ------------------- | --------------------- | --------------- | ----------------------- |
| Agent 支付协议          | Visa TAP, Stripe ACP  | Agent 有没有**权限** | 执行时有没有**人类物理在场**        |
| 软件 HITL 工具          | Permit.io, Auth0 CIBA | 有没有**软件层确认**    | 确认的是不是**真人**，证据能不能举证    |
| 审计合规平台              | FireTail, Zenity      | Agent **做了什么**  | 有没有**人类同意**，同意记录是否可独立核验 |
| Proof of Personhood | Worldcoin             | **注册时**是人       | **此刻执行时**在不在场           |
| 设备生物认证              | Apple Touch ID        | 是不是**设备主人**     | 跨平台操作绑定、链上可审计           |

HumanLink 填补的空白：**此刻物理在场 + 操作绑定 + 密码学可举证 + 链上可审计 + 开放协议**。

<br />

### Cobo Agentic Wallet vs HumanLink

HumanLink 与 Cobo 解决不同层面的问题：Cobo 是 Agent 钱包执行基础设施，HumanLink 是人类在场授权证明协议层。

| 维度    | Cobo Agentic Wallet                            | HumanLink                                                      |
| ----- | ---------------------------------------------- | -------------------------------------------------------------- |
| 核心定位  | Agent 钱包执行基础设施                                 | 人类在场授权证明协议层                                                    |
| 授权模型  | Pact：owner 批准任务级边界（intent、plan、budget）         | Challenge + actionHash：单次操作级断言                                 |
| 人工确认  | Owner 在 Cobo app 中批准 Pact                      | 用户在 HumanLink 设备上物理确认 actionHash                               |
| 签名私钥  | MPC key shares（资产控制权）                          | SE 独立私钥（授权证明权）                                                 |
| 签名对象  | 链上交易 / 钱包操作；Pact 内容独立可验签签名未明确                  | actionHash / Challenge / 授权上下文                                 |
| 第三方验签 | 依赖 Cobo 钱包体系与平台审计语义；审批日志在 Cobo 平台内部，无法脱离平台独立核验 | 基于 assertion + 设备身份 + registry + revocation 独立验签；审计记录可脱离平台独立核验 |

<br />

### 技术路线对比

HumanLink 采用**分立式硬件架构**（生物模块 + MCU + Secure Element），与三大主流路线对比：

| 维度         | HumanLink 分立式                                          | Apple Secure Enclave         | Android TEE+StrongBox          | 工业 / IoT SE 路线          |
| ---------- | ------------------------------------------------------ | ---------------------------- | ------------------------------ | ----------------------- |
| 安全边界       | 分散，需补强                                                 | 最集中                          | OEM 差异大                        | 中等，SE 强但生物处理通常在外部       |
| 操作绑定       | **强**（actionHash）                                      | 中等                           | 弱到中等                           | 中等，取决于业务实现              |
| 第三方验证与举证   | **强**：可独立验签、查设备注册状态与撤销记录、生成跨平台审计证据                     | 弱，主要依赖本机或 Apple 生态，不输出开放授权断言 | 弱到中等，依赖系统 API 和 OEM 实现，外部证明能力弱 | 中等，可验证设备签名，但不一定验证人类授权   |
| 审计/状态层     | Verifier + Registry + Revocation + Audit log，形成完整授权证明链 | 主要为系统内部日志，不面向第三方审计           | 主要为系统内部安全日志                    | 可有设备日志或证书状态，通常不面向人类授权证明 |
| 开放性        | **高**，可替换模组                                            | 低                            | 中等                             | **高**，适合嵌入不同硬件平台        |
| Agent 场景适配 | **强**：拦截高风险行为                                          | 弱                            | 弱到中等                           | 中等，更适合设备认证              |

分立式路线的代价是安全边界分散，需在 Secure Boot、模块 attestation、链路保护上持续补强。当前 Demo 指纹授权基于 JM-101（指纹匹配，非强活体检测），详见 [TECHNICAL\_ROADMAP/](./TECHNICAL_ROADMAP/)。

<br />

### HumanLink 协议设计（四层架构）

HumanLink 不是封闭硬件产品，而是 **开放协议 + SDK + 参考硬件** 三层设计：

| 层                | 职责           | 关键内容                                                                        |
| ---------------- | ------------ | --------------------------------------------------------------------------- |
| **协议核心层**        | 授权证明规范       | `Challenge`、`actionHash`、`HumanPresenceAssertion`、签名格式、10 步验证流程             |
| **接入层 (SDK)**    | 统一验证接口       | 本地/云端同一套 SDK：生成 Challenge、调用设备签名、验证 Assertion、写入审计                          |
| **身份与链上层**       | 设备身份与审计      | Device DID 链上注册、用户↔设备绑定、Assertion 撤销、审计记录锚定                                 |
| **硬件抽象接口 (HAI)** | 合规 Issuer 标准 | 定义签发设备的能力要求与输出格式，不绑定特定硬件（`get_device_did`、`get_attestation`、`authenticate`） |

**当前参考实现**：ESP32 + JM-101 指纹模块 + ATECC608A Secure Element（分立式路线）。

***

<br />

## HumanLinkPay定位

**HumanLinkPay** 是 `HumanLink` 仓库中的 Agent 支付 Demo。

它把 HumanLink 的指纹 + 设备签名能力接入 Agent 支付链路，实现：

- 小额交易自动放行
- 高风险交易必须经过 HumanLink 指纹授权
- 授权结果绑定具体 `PaymentIntent`
- 支付执行后保留本地审计记录、SDK 审计页和链上交易回执

当前主要实现代码位于：

```text
apps/humanlinkpay/
```

***

## 核心问题

当 AI Agent 能代表用户发起链上支付时，系统需要回答三个问题：

1. 哪些支付可以自动执行？
2. 哪些支付必须要求真实用户在场授权？
3. 授权完成后，如何留下可验证、可追溯、可展示的审计记录？

HumanLinkPay 的答案是：

- Agent 负责理解自然语言并生成结构化支付意图
- Gateway 负责策略判断、Challenge 生成、Assertion 校验和链上执行
- HumanLink 设备负责提供高风险操作的人类在场授权证明

***

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

***

## HumanLink 与 HumanLinkPay 的关系

```
HumanLink (通用基础设施 — HumanLink 仓库)
  ├── 协议层: Challenge / Assertion / 10 步验证
  ├── SDK:     本地验证、设备通信、审计记录
  ├── 硬件:    指纹 + SE 签名的参考实现
  │
  └── 应用场景 Demo
        └── HumanLinkPay ← 本仓库子项目
              场景: Agent 支付安全网关
              能力: 小额自动 / 高风险指纹授权 / 三层审计
```

> 完整 HumanLink 协议文档见 [HumanLink\_doc/README.md](./HumanLink_doc/README.md)。技术路线与安全增强方向见 [TECHNICAL\_ROADMAP/](./TECHNICAL_ROADMAP/)。

***

## 系统架构

```text
┌──────────────────────────────────────────────────────────────┐
│                        HumanLinkPay                          │
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

***

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

***

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

***

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

***

## 仓库落点

```text
HumanLink/
├── HumanLinkPay_README.md
├── sdk/
├── contracts/
├── firmware/
└── apps/
    └── humanlinkpay/
        ├── README.md
        ├── agent/
        ├── gateway/
        ├── frontend/
        ├── docs/
        ├── contracts/
        └── deployments/
```

子目录说明：

| 目录                               | 作用                          | 当前状态      |
| -------------------------------- | --------------------------- | --------- |
| `apps/humanlinkpay/agent/`       | Hermes 工具层、mock 请求和 adapter | 已有可用脚本    |
| `apps/humanlinkpay/gateway/`     | 核心支付网关、策略、SDK 调用、执行与审计      | 已跑通主链路    |
| `apps/humanlinkpay/frontend/`    | 可视化 Demo 页面、聊天窗口、流程面板       | 已跑通       |
| `apps/humanlinkpay/docs/`        | 补充文档                        | 已补本地审计说明  |
| `apps/humanlinkpay/contracts/`   | 合约实验区                       | 当前不是主展示路径 |
| `apps/humanlinkpay/deployments/` | 部署记录占位                      | 待补充       |

***

## 快速启动

### 1. 启动 HumanLink SDK

```bash
cd sdk
./.venv311/bin/python run_server.py
```

默认地址：

```text
http://127.0.0.1:8765
```

### 2. 安装 gateway 依赖

推荐直接复用仓库里已经存在的 `sdk/.venv311`：

```bash
cd apps/humanlinkpay/gateway
../../../sdk/.venv311/bin/pip install -r requirements.txt
```

### 3. 配置 gateway 环境变量

```bash
cd apps/humanlinkpay/gateway
cp .env.example .env
```

关键项：

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
```

还需要保证：

- 需要在本地配置 `HUMANLINKPAY_SEPOLIA_RPC_URL`
- 需要在本地配置 `HUMANLINKPAY_PRIVATE_KEY`
- 本机 Hermes CLI 可用，并且 `~/.hermes/.env` 中 API key 正确

### 4. 启动 gateway

```bash
cd apps/humanlinkpay/gateway
HUMANLINKPAY_AUTO_OPEN_DEMO_UI=true \
  ../../../sdk/.venv311/bin/uvicorn \
  main:app --host 127.0.0.1 --port 8787
```

启动后会自动在本地浏览器打开：

```text
http://127.0.0.1:8787/ui/payment-demo
```

***

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

***

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

***

## 审计与结果

当前有三层结果输出：

1. **Gateway 本地审计日志**
   - 路径：`apps/humanlinkpay/gateway/runtime/gateway_audit.jsonl`
2. **HumanLink SDK 审计页**
   - 返回字段：`humanlink_record_url`
3. **链上交易结果**
   - 返回字段：`tx_hash`
   - 可跳转 Sepolia Etherscan

补充说明见 [apps/humanlinkpay/docs/local\_audit.md](./apps/humanlinkpay/docs/local_audit.md)。

***

## 关键文件

- 子项目主说明：[apps/humanlinkpay/README.md](./apps/humanlinkpay/README.md)
- Gateway 入口：[main.py](./apps/humanlinkpay/gateway/main.py)
- Hermes Bridge：[hermes\_bridge.py](./apps/humanlinkpay/gateway/hermes_bridge.py)
- 支付执行器：[payment\_executor.py](./apps/humanlinkpay/gateway/payment_executor.py)
- 策略引擎：[policy.py](./apps/humanlinkpay/gateway/policy.py)
- Gateway 说明：[gateway/README.md](./apps/humanlinkpay/gateway/README.md)
- Frontend 页面：[index.html](./apps/humanlinkpay/frontend/index.html)
- Frontend 说明：[frontend/README.md](./apps/humanlinkpay/frontend/README.md)
- Mock Agent：[mock\_agent.py](./apps/humanlinkpay/agent/mock_agent.py)
- Hermes Adapter：[hermes\_adapter.py](./apps/humanlinkpay/agent/hermes_adapter.py)
- Hermes Tool Schema：[hermes\_tool\_schema.json](./apps/humanlinkpay/agent/hermes_tool_schema.json)
- DemoMerchant 合约：[DemoMerchant.sol](./apps/humanlinkpay/contracts/DemoMerchant.sol)

***

## 当前边界

当前主路径已经明确为：

- Sepolia 测试网
- 原生 ETH 单向转账
- `native_transfer` 执行模式
- `0.001 ETH` 风险阈值
- allowlist + 金额阈值 的最小策略
- HumanLink 指纹授权 + 审计页 + 本地审计日志

当前**不是**主展示路径的能力：

- `DemoMerchant.sol` 合约交互
- Escrow / Quote / Settlement 状态机
- 更复杂的预算模型
- 强活体检测、模块级 attestation、secure boot

***

## 设计原则

- **Agent 负责理解，不负责放权**
  - Hermes 可以生成支付意图，但不能绕过 Gateway 策略
- **Gateway 负责决策，不信任自然语言**
  - 只信任结构化 `PaymentIntent`
- **HumanLink 负责高风险授权**
  - 高风险动作绑定具体 `action_hash`
- **执行必须可审计**
  - 本地日志、SDK 记录页、链上结果三层可回溯

***

## 与 AI × Web3 School Handbook 的关联

HumanlinkPay 的 Demo 场景属于 Handbook **模块 B（Payment/Commerce）**，核心功能开发落在 **模块 D/E/F**。一句话：模块 B 是叙事线（用户看到的场景），模块 D/E/F 是工程线（代码实际在做什么）。

| Handbook 章节                                                                    | 核心概念                                           | HumanlinkPay 对应                                                              |
| ------------------------------------------------------------------------------ | ---------------------------------------------- | ---------------------------------------------------------------------------- |
| [Agentic Commerce](https://aiweb3.school/zh/handbook/tracks/agentic-commerce/) | Payment Intent、Budget Control、On-chain Receipt | PaymentIntent 字段设计、金额阈值控制、链上 tx 收据                                           |
| [Agent Wallet](https://aiweb3.school/zh/handbook/bridge/agent-wallet/)         | Policy、Guard、Human Check、Session Key           | Gateway Policy Engine = Policy+Guard；ALLOW/REQUIRE\_HL/DENY = 分层 Human Check |
| [Agent Identity](https://aiweb3.school/zh/handbook/bridge/agent-identity/)     | Ownership、Capability、硬件根信任                     | SE 签名作为 Agent action 的 owner 在场证明                                            |
| [AI Security](https://aiweb3.school/zh/handbook/bridge/ai-security/)           | Prompt Injection 防御、Tool Abuse、Audit Log       | Gateway 不信 Agent 自然语言；Agent 不直接调合约；三层审计                                      |
| [Verifiable AI](https://aiweb3.school/zh/handbook/bridge/verifiable-ai/)       | Audit Trail、按风险分层验证                            | 三层审计（SDK+Gateway+链上）；低风险自动 / 高风险 hardware attestation                        |

未来可扩展方向：[Agent Trust & Reputation](https://aiweb3.school/zh/handbook/bridge/agent-trust-and-reputation/)（三维信誉数据）、[Settlement & Escrow](https://aiweb3.school/zh/handbook/bridge/settlement-and-escrow/)（高风险支付争议窗口）。

***

## 后续可扩展方向

- 从 `native_transfer` 扩展到 `DemoMerchant` 或更真实的商业支付场景
- 增加更复杂的策略引擎，例如预算、时间窗、商户级别、用途规则
- 引入更强的设备 attestation 和硬件证明链
- 为多轮 Hermes 对话增加更稳定的流式事件展示
- 增加一键启动脚本和更完整的演示手册

