# HumanlinkPay Deployments

这个目录用于保存 `apps/humanlinkpay/` 自己的部署结果，不改动根目录 `contracts/deployments/`。

建议后续把 `DemoMerchant` 部署结果保存成：

```json
{
  "network": "sepolia",
  "chainId": 11155111,
  "contract": "DemoMerchant",
  "address": "0xYourDemoMerchantAddress",
  "deployedAt": "2026-06-06T00:00:00Z"
}
```

部署完成后，把地址同步写入：

```text
HUMANLINKPAY_DEMO_MERCHANT_ADDRESS=0xYourDemoMerchantAddress
HUMANLINKPAY_ALLOWLIST=0xYourDemoMerchantAddress
HUMANLINKPAY_EXECUTION_MODE=demo_merchant
```
