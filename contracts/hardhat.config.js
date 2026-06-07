require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const { subtask } = require("hardhat/config");
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } = require("hardhat/builtin-tasks/task-names");

const sepoliaRpcUrl = process.env.SEPOLIA_RPC_URL || "https://rpc.sepolia.org";
const sepoliaPrivateKey = process.env.SEPOLIA_PRIVATE_KEY || "";
const etherscanApiKey = process.env.ETHERSCAN_API_KEY || "";
const localSolcVersion = "0.8.26";
const localSolcLongVersion = "0.8.26+commit.8a97fa7a.Emscripten.clang";
const localSolcPath = require.resolve("solc/soljson.js");

subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD).setAction(async ({ solcVersion }) => {
  if (solcVersion !== localSolcVersion) {
    throw new Error(
      `Unsupported compiler request: ${solcVersion}. This workspace is pinned to the bundled solc ${localSolcVersion}.`
    );
  }

  return {
    compilerPath: localSolcPath,
    isSolcJs: true,
    version: localSolcVersion,
    longVersion: localSolcLongVersion,
  };
});

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: localSolcVersion,
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  paths: {
    sources: "./src",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  networks: {
    hardhat: {},
    localhost: {
      url: "http://127.0.0.1:8545",
    },
    sepolia: {
      url: sepoliaRpcUrl,
      accounts: sepoliaPrivateKey ? [sepoliaPrivateKey] : [],
    },
  },
  etherscan: {
    apiKey: etherscanApiKey,
  },
};
