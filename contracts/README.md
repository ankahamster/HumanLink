# HumanLink Contracts

This directory contains a Hardhat workspace for the HumanLink on-chain contracts,
aligned with the protocol notes in `README.md` and `demo.md`.

## Contract Overview

- `IssueRegistry.sol`
  - Implements the documented issuer registry role
  - Stores device public keys, DIDs, and attestation hashes
  - Supports device revocation and validity checks
- `UserDeviceRegistry.sol`
  - Stores the `userIdHash -> deviceDID` mapping
  - Useful for local or self-custodied user/device binding flows
- `AssertionStatusRegistry.sol`
  - Provides the documented `revokeAssertion()` and `isRevoked()` interface
  - Adds `recordAssertionAudit()` for optional audit-summary anchoring

## On-Chain Data Boundary

The following data must stay off-chain:

- biometric templates or raw biometric data
- secure element private keys
- the full `HumanPresenceAssertion` document
- real user identity data

The following data is suitable for mandatory or optional on-chain anchoring:

- device DID and public-key registration metadata
- hashed user/account to device DID bindings
- assertion revocation status
- high-risk operation audit summaries

## Recommended Audit Mapping

`AssertionStatusRegistry.recordAssertionAudit()` expects only hashes and minimal metadata:

- `assertionHash`
- `assertionIdHash`
- `deviceDidHash`
- `requiredIssuerDidHash`
- `actionHash`
- `nonceHash`
- `originHash`
- `verificationMethodHash`
- `signedHash`
- `sensorSerialHash`
- `matchScore`
- `createdAt`
- `protocolVersion`

Recommended derivations:

- `assertionHash = keccak256(canonicalAssertionBytes)`
- `assertionIdHash = keccak256(bytes(assertion.id))`
- `deviceDidHash = keccak256(bytes(assertion.device.id))`
- `requiredIssuerDidHash = keccak256(bytes(assertion.challenge.requiredIssuerDID))`
- `originHash = keccak256(bytes(assertion.challenge.origin))`
- `verificationMethodHash = keccak256(bytes(assertion.proof.verificationMethod))`
- `sensorSerialHash = keccak256(bytes(assertion.evidence.sensorSerial))`

## Hardhat Commands

```bash
npm install
npm run compile
npx hardhat node
npm run deploy:localhost
npm run anchor:localhost
npm run deploy:sepolia
npm run anchor:sepolia
```

The workspace is configured to use the bundled `solc-js` that already exists in
`node_modules`, so compilation does not depend on downloading a compiler at run
time.

## Sepolia Setup

1. Copy `.env.example` to `.env`
2. Set `SEPOLIA_RPC_URL`
3. Set `SEPOLIA_PRIVATE_KEY`
4. Optionally set `CONTRACT_ADMIN`
5. Run `npm run deploy:sepolia`
6. Copy `AssertionStatusRegistry` from `deployments/sepolia.json` into
   `ASSERTION_STATUS_REGISTRY_ADDRESS` when you want to anchor audit records

## CLI Audit Anchoring

When the SDK CLI asks whether the successful authorization record should stay
local or be anchored on-chain:

- choose `local` to keep the default local audit-only behavior
- choose `chain` to call `AssertionStatusRegistry.recordAssertionAudit(...)`
- make sure the `contracts/.env` file already points to your deployed Sepolia
  `AssertionStatusRegistry`

## Deployment Order

1. Deploy `IssueRegistry`
2. Deploy `UserDeviceRegistry`
3. Deploy `AssertionStatusRegistry`
4. Register trusted devices through `IssueRegistry.registerIssuer(...)`
5. During runtime, let the SDK or backend call:
   - `UserDeviceRegistry.bindDevice(...)`
   - `AssertionStatusRegistry.recordAssertionAudit(...)`
   - `AssertionStatusRegistry.revokeAssertion(...)`

## Sepolia

- Chain ID: `11155111`
- Explorer: <https://sepolia.etherscan.io/>
