const fs = require("fs");
const path = require("path");
const hre = require("hardhat");
require("dotenv").config();

async function deployContract(name, args) {
  const factory = await hre.ethers.getContractFactory(name);
  const contract = await factory.deploy(...args);
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  return { contract, address };
}

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  const contractAdmin =
    process.env.CONTRACT_ADMIN && process.env.CONTRACT_ADMIN !== hre.ethers.ZeroAddress
      ? process.env.CONTRACT_ADMIN
      : deployer.address;

  console.log(`Network: ${hre.network.name}`);
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Admin: ${contractAdmin}`);

  const issueRegistry = await deployContract("IssueRegistry", [contractAdmin]);
  const userDeviceRegistry = await deployContract("UserDeviceRegistry", [contractAdmin]);
  const assertionStatusRegistry = await deployContract("AssertionStatusRegistry", [contractAdmin]);

  const deployment = {
    network: hre.network.name,
    chainId: Number(hre.network.config.chainId || 0),
    deployer: deployer.address,
    admin: contractAdmin,
    deployedAt: new Date().toISOString(),
    contracts: {
      IssueRegistry: issueRegistry.address,
      UserDeviceRegistry: userDeviceRegistry.address,
      AssertionStatusRegistry: assertionStatusRegistry.address,
    },
  };

  const deploymentsDir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(deploymentsDir, { recursive: true });

  const outputPath = path.join(deploymentsDir, `${hre.network.name}.json`);
  fs.writeFileSync(outputPath, JSON.stringify(deployment, null, 2));

  console.log("Deployment complete:");
  console.log(JSON.stringify(deployment, null, 2));
  console.log(`Saved deployment metadata to ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
