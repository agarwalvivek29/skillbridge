// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IEscrowFactory
/// @notice Interface for the EscrowFactory that deploys GigEscrow contracts
interface IEscrowFactory {
    // ─── Events ──────────────────────────────────────────────────────────────────

    /// @notice Emitted when a new GigEscrow is deployed
    event EscrowCreated(
        address indexed escrowAddress,
        address indexed client,
        address indexed freelancer,
        address tokenAddress,
        uint256 totalAmount
    );

    /// @notice Emitted when the platform fee recipient is updated
    event FeeRecipientUpdated(address indexed oldRecipient, address indexed newRecipient);

    // ─── Functions ────────────────────────────────────────────────────────────────

    /// @notice Deploy a new GigEscrow contract for a gig
    /// @param client Address of the client (funds depositor)
    /// @param freelancer Address of the freelancer (payout recipient)
    /// @param tokenAddress ERC-20 token address, or address(0) for ETH
    /// @param milestoneAmounts Array of per-milestone amounts (wei or token units)
    /// @param platformFeeBasisPoints Fee in basis points (e.g. 500 = 5%)
    /// @return escrowAddress Address of the newly deployed GigEscrow
    function createEscrow(
        address client,
        address freelancer,
        address tokenAddress,
        uint256[] calldata milestoneAmounts,
        uint256 platformFeeBasisPoints
    ) external returns (address escrowAddress);

    /// @notice Update the platform fee recipient address
    /// @param newRecipient New fee recipient address
    function setFeeRecipient(address newRecipient) external;

    /// @notice Current platform fee recipient
    function feeRecipient() external view returns (address);

    /// @notice Owner of the factory (acts as arbitrator for all deployed escrows)
    function owner() external view returns (address);

    /// @notice Pending owner awaiting two-step ownership acceptance
    function pendingOwner() external view returns (address);

    /// @notice Number of escrows deployed by this factory
    function getEscrowCount() external view returns (uint256);

    /// @notice Get the escrow address at a specific index (for paginated access)
    function getEscrow(uint256 index) external view returns (address);

    /// @notice Get all escrow addresses deployed by this factory
    /// @dev WARNING: unbounded — will revert at scale. Use getEscrowCount + getEscrow for production pagination.
    function getAllEscrows() external view returns (address[] memory);
}
