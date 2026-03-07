// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./interfaces/IEscrowFactory.sol";
import "./GigEscrow.sol";

/// @title EscrowFactory
/// @notice Deployed once per network. Creates a new GigEscrow contract for each gig.
///         The `api` service calls createEscrow() after a gig is funded, passing the
///         client and freelancer wallet addresses plus per-milestone amounts.
contract EscrowFactory is IEscrowFactory {
    // ─── State ────────────────────────────────────────────────────────────────

    address public immutable owner;

    // ─── Constructor ─────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ─── Factory ──────────────────────────────────────────────────────────────

    /// @inheritdoc IEscrowFactory
    /// @param client      Client wallet address
    /// @param freelancer  Freelancer wallet address
    /// @param arbitrator  Arbitration oracle address (usually the API service wallet)
    /// @param amounts     Per-milestone amounts in wei; length = milestone count
    function createEscrow(
        address client,
        address freelancer,
        address arbitrator,
        uint256[] calldata amounts
    ) external returns (address escrowAddress) {
        require(client != address(0), "EscrowFactory: zero client address");
        require(freelancer != address(0), "EscrowFactory: zero freelancer address");
        require(arbitrator != address(0), "EscrowFactory: zero arbitrator address");
        require(amounts.length > 0, "EscrowFactory: no milestones");

        uint256 total;
        for (uint256 i; i < amounts.length; ++i) {
            require(amounts[i] > 0, "EscrowFactory: milestone amount must be > 0");
            total += amounts[i];
        }

        GigEscrow escrow = new GigEscrow(client, freelancer, arbitrator, amounts);
        escrowAddress = address(escrow);

        emit EscrowCreated(escrowAddress, client, freelancer, total);
    }
}
