// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/EscrowFactory.sol";

/// @title Deploy
/// @notice Deploys EscrowFactory to the active network.
///
/// Usage:
///   # Dry-run (no broadcast)
///   forge script script/Deploy.s.sol --rpc-url $BASE_SEPOLIA_RPC_URL
///
///   # Base Sepolia (testnet)
///   forge script script/Deploy.s.sol \
///     --rpc-url $BASE_SEPOLIA_RPC_URL \
///     --broadcast \
///     --verify \
///     --private-key $PRIVATE_KEY
///
///   # Base Mainnet — REQUIRES explicit human approval before running
///   forge script script/Deploy.s.sol \
///     --rpc-url $BASE_RPC_URL \
///     --broadcast \
///     --verify \
///     --private-key $PRIVATE_KEY
///
/// After deployment, copy the printed EscrowFactory address to the api service .env:
///   ESCROW_FACTORY_ADDRESS=<printed address>
contract Deploy is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);

        console.log("Deployer:        ", deployer);
        console.log("Chain ID:        ", block.chainid);
        console.log("Block:           ", block.number);

        vm.startBroadcast(deployerKey);

        EscrowFactory factory = new EscrowFactory();

        vm.stopBroadcast();

        console.log("EscrowFactory deployed at:", address(factory));
        console.log("Factory owner:            ", factory.owner());
    }
}
