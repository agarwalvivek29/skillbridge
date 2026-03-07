// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Deploy} from "./Deploy.s.sol";

/// @title DeployBase
/// @notice Thin wrapper that inherits Deploy and sets Base L2 context.
///
/// Deploy to Base Sepolia (testnet):
///   forge script script/DeployBase.s.sol \
///     --rpc-url $BASE_SEPOLIA_RPC_URL \
///     --broadcast \
///     --verify \
///     --etherscan-api-key $BASESCAN_API_KEY
///
/// Deploy to Base Mainnet (REQUIRES human approval):
///   forge script script/DeployBase.s.sol \
///     --rpc-url $BASE_RPC_URL \
///     --broadcast \
///     --verify \
///     --etherscan-api-key $BASESCAN_API_KEY
///
/// ⚠️  Never run the mainnet command without explicit human sign-off.
///     Store the deployed address in services/api/.env as ESCROW_FACTORY_ADDRESS.
contract DeployBase is Deploy {}
