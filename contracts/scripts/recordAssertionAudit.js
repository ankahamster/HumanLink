const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
require("dotenv").config();

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }

  if (value && typeof value === "object") {
    const keys = Object.keys(value).sort();
    return `{${keys
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(",")}}`;
  }

  return JSON.stringify(value);
}

function readAssertionPayload() {
  if (process.env.ASSERTION_JSON_B64) {
    return JSON.parse(Buffer.from(process.env.ASSERTION_JSON_B64, "base64").toString("utf8"));
  }

  if (process.env.ASSERTION_JSON_FILE) {
    return JSON.parse(fs.readFileSync(process.env.ASSERTION_JSON_FILE, "utf8"));
  }

  throw new Error("Provide ASSERTION_JSON_B64 or ASSERTION_JSON_FILE");
}

function readRegistryAddress() {
  if (
    process.env.ASSERTION_STATUS_REGISTRY_ADDRESS &&
    process.env.ASSERTION_STATUS_REGISTRY_ADDRESS !== hre.ethers.ZeroAddress
  ) {
    return process.env.ASSERTION_STATUS_REGISTRY_ADDRESS;
  }

  const deploymentPath = path.join(__dirname, "..", "deployments", `${hre.network.name}.json`);
  if (!fs.existsSync(deploymentPath)) {
    throw new Error(
      `Missing deployment file and ASSERTION_STATUS_REGISTRY_ADDRESS not set: ${deploymentPath}`
    );
  }

  const deployment = JSON.parse(fs.readFileSync(deploymentPath, "utf8"));
  return deployment.contracts?.AssertionStatusRegistry;
}

function pick(source, ...keys) {
  for (const key of keys) {
    if (source && source[key] !== undefined && source[key] !== null) {
      return source[key];
    }
  }
  return undefined;
}

function hashUtf8(value) {
  return hre.ethers.keccak256(hre.ethers.toUtf8Bytes(String(value || "")));
}

function toBytes32Hex(value, fieldName) {
  if (!value) {
    return hre.ethers.ZeroHash;
  }

  const normalized = String(value).startsWith("0x") ? String(value) : `0x${value}`;
  if (!hre.ethers.isHexString(normalized) || hre.ethers.dataLength(normalized) !== 32) {
    throw new Error(`${fieldName} must be a 32-byte hex string`);
  }
  return normalized;
}

function toUnixSeconds(isoString) {
  const timestamp = Date.parse(isoString);
  if (Number.isNaN(timestamp)) {
    throw new Error(`Invalid ISO timestamp: ${isoString}`);
  }
  return Math.floor(timestamp / 1000);
}

function buildAuditInput(assertion) {
  const challenge = assertion.challenge || {};
  const proof = assertion.proof || {};
  const evidence = assertion.evidence || {};
  const canonicalAssertion = stableStringify(assertion);

  return {
    assertionHash: hashUtf8(canonicalAssertion),
    assertionIdHash: hashUtf8(assertion.id || ""),
    deviceDidHash: hashUtf8(pick(assertion.device || {}, "id") || ""),
    requiredIssuerDidHash: hashUtf8(
      pick(challenge, "required_issuer_did", "requiredIssuerDID") || ""
    ),
    actionHash: toBytes32Hex(pick(challenge, "action_hash", "actionHash"), "actionHash"),
    nonceHash: hashUtf8(pick(challenge, "nonce") || ""),
    originHash: hashUtf8(pick(challenge, "origin") || ""),
    verificationMethodHash: hashUtf8(
      pick(proof, "verification_method", "verificationMethod") || ""
    ),
    signedHash: toBytes32Hex(pick(proof, "signed_hash", "signedHash"), "signedHash"),
    sensorSerialHash: hashUtf8(pick(evidence, "sensor_serial", "sensorSerial") || ""),
    matchScore: Number(pick(evidence, "match_score", "matchScore") || 0),
    createdAt: toUnixSeconds(assertion.created),
    protocolVersion: assertion.version || "0.3",
  };
}

async function main() {
  const assertion = readAssertionPayload();
  const registryAddress = readRegistryAddress();
  const registry = await hre.ethers.getContractAt(
    "AssertionStatusRegistry",
    registryAddress
  );

  const input = buildAuditInput(assertion);
  console.log(`Anchoring audit summary to ${registryAddress}`);
  console.log(`Assertion hash: ${input.assertionHash}`);

  const tx = await registry.recordAssertionAudit(input);
  const receipt = await tx.wait();

  console.log(`Transaction hash: ${receipt.hash}`);
  console.log(`Gas used: ${receipt.gasUsed.toString()}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
