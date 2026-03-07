// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IEscrowFactory
/// @notice Interface for the factory that deploys per-gig GigEscrow contracts.
interface IEscrowFactory {
    // ─── Events ──────────────────────────────────────────────────────────────

    event EscrowCreated(
        address indexed escrowAddress,
        address indexed client,
        address indexed freelancer,
        uint256 totalAmount
    );

    // ─── Functions ───────────────────────────────────────────────────────────

    /// @notice Deploys a new GigEscrow for a gig.
    /// @param client Address of the client (fund depositor)
    /// @param freelancer Address of the freelancer (fund recipient)
    /// @param arbitrator Address of the arbitrator (API oracle or multisig)
    /// @param amounts Array of per-milestone amounts in wei. Length = milestone count.
    /// @return escrowAddress Address of the newly deployed GigEscrow contract.
    function createEscrow(
        address client,
        address freelancer,
        address arbitrator,
        uint256[] calldata amounts
    ) external returns (address escrowAddress);

    /// @notice Returns the address of the owner (deployer).
    function owner() external view returns (address);
}
