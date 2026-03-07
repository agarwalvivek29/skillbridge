// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {EscrowFactory} from "../src/EscrowFactory.sol";

/// @title Deploy
/// @notice Base deployment script for EscrowFactory
/// @dev Usage:
///   Base Sepolia:  forge script script/DeployBase.s.sol --rpc-url $BASE_SEPOLIA_RPC_URL --broadcast --verify
///   Base Mainnet:  forge script script/DeployBase.s.sol --rpc-url $BASE_RPC_URL --broadcast --verify
///                  ⚠️  REQUIRES explicit human approval before running on mainnet
contract Deploy is Script {
    function run() external {
        // Read deployer private key from environment
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        // The platform fee recipient — set to deployer for testnet, multisig wallet for prod
        address feeRecipient = vm.envOr("FEE_RECIPIENT", deployer);

        console.log("=== SkillBridge EscrowFactory Deployment ===");
        console.log("Deployer:      ", deployer);
        console.log("Fee recipient: ", feeRecipient);
        console.log("Chain ID:      ", block.chainid);

        vm.startBroadcast(deployerKey);

        EscrowFactory factory = new EscrowFactory(feeRecipient);

        vm.stopBroadcast();

        console.log("EscrowFactory deployed at:", address(factory));
        console.log("");
        console.log("Next steps:");
        console.log("1. Add to api .env:  ESCROW_FACTORY_ADDRESS=", address(factory));
        console.log("2. Verify on Basescan if not auto-verified");
    }
}
