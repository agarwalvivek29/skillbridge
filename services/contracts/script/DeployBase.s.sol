// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/EscrowFactory.sol";

/// @title DeployBase
/// @notice Network-aware deployment script for Base Sepolia and Base Mainnet.
///         Reads network from foundry.toml [rpc_endpoints] via --rpc-url alias.
///
/// Usage:
///   # Base Sepolia
///   forge script script/DeployBase.s.sol \
///     --rpc-url base_sepolia \
///     --broadcast \
///     --verify \
///     --private-key $PRIVATE_KEY
///
///   # Base Mainnet — REQUIRES explicit human approval before running
///   forge script script/DeployBase.s.sol \
///     --rpc-url base_mainnet \
///     --broadcast \
///     --verify \
///     --private-key $PRIVATE_KEY
///
/// Chain IDs:
///   Base Mainnet  → 8453
///   Base Sepolia  → 84532
contract DeployBase is Script {
    // Base Mainnet chain ID — guard against accidental mainnet deploys
    uint256 constant BASE_MAINNET_CHAIN_ID = 8453;
    uint256 constant BASE_SEPOLIA_CHAIN_ID = 84532;

    function run() external {
        _validateNetwork();

        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        console.log("=== SkillBridge EscrowFactory Deployment ===");
        console.log("Network:         ", _networkName());
        console.log("Chain ID:        ", block.chainid);
        console.log("Deployer:        ", deployer);

        vm.startBroadcast(deployerKey);

        EscrowFactory factory = new EscrowFactory();

        vm.stopBroadcast();

        console.log("");
        console.log("=== Deployment Complete ===");
        console.log("EscrowFactory:   ", address(factory));
        console.log("Owner:           ", factory.owner());
        console.log("");
        console.log("Next step: add to api service .env:");
        console.log("  ESCROW_FACTORY_ADDRESS=", vm.toString(address(factory)));
    }

    function _validateNetwork() internal view {
        uint256 id = block.chainid;
        require(
            id == BASE_MAINNET_CHAIN_ID || id == BASE_SEPOLIA_CHAIN_ID,
            "DeployBase: unsupported network (use base_sepolia or base_mainnet)"
        );

        if (id == BASE_MAINNET_CHAIN_ID) {
            // Extra guard — the env var ALLOW_MAINNET must be explicitly set to "true"
            string memory allow = vm.envOr("ALLOW_MAINNET", string("false"));
            require(
                keccak256(bytes(allow)) == keccak256(bytes("true")),
                "DeployBase: set ALLOW_MAINNET=true to deploy to Base Mainnet"
            );
        }
    }

    function _networkName() internal view returns (string memory) {
        if (block.chainid == BASE_MAINNET_CHAIN_ID) return "Base Mainnet";
        if (block.chainid == BASE_SEPOLIA_CHAIN_ID) return "Base Sepolia";
        return "Unknown";
    }
}
