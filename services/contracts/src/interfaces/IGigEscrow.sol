// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IGigEscrow
/// @notice Interface for the per-gig escrow contract on SkillBridge
interface IGigEscrow {
    // ─── Enums ───────────────────────────────────────────────────────────────────

    enum MilestoneStatus {
        PENDING,
        COMPLETED,
        DISPUTED,
        RESOLVED
    }

    enum DisputeResolution {
        PAY_FREELANCER,
        REFUND_CLIENT,
        SPLIT
    }

    // ─── Events ──────────────────────────────────────────────────────────────────

    /// @notice Emitted when the client successfully deposits the full budget
    event EscrowFunded(address indexed client, uint256 totalAmount, address tokenAddress);

    /// @notice Emitted when a milestone is completed and funds released
    /// @param milestoneIndex Index of the completed milestone
    /// @param freelancer Address receiving the net payout
    /// @param netAmount Amount sent to freelancer (after platform fee)
    /// @param platformFeeAmount Amount sent to platform fee recipient
    event FundsReleased(
        uint256 indexed milestoneIndex,
        address indexed freelancer,
        uint256 netAmount,
        uint256 platformFeeAmount
    );

    /// @notice Emitted when a dispute is raised on a milestone
    event DisputeRaised(uint256 indexed milestoneIndex, address indexed raisedBy);

    /// @notice Emitted when a dispute is resolved
    event DisputeResolved(
        uint256 indexed milestoneIndex,
        DisputeResolution resolution,
        uint256 freelancerAmount,
        uint256 clientAmount
    );

    /// @notice Emitted when one party signs the emergency withdrawal
    event EmergencyWithdrawalSigned(address indexed signer);

    /// @notice Emitted when emergency withdrawal executes
    event EmergencyWithdrawal(uint256 clientAmount);

    // ─── Core Functions ───────────────────────────────────────────────────────────

    /// @notice Client deposits the full gig budget to lock funds
    /// @dev ETH: send msg.value == totalAmount. ERC-20: approve first, then call.
    function deposit() external payable;

    /// @notice Client approves a milestone and releases funds to freelancer
    /// @param index Zero-based milestone index
    function completeMilestone(uint256 index) external;

    /// @notice Client or freelancer raises a dispute on a milestone
    /// @param index Zero-based milestone index
    function raiseDispute(uint256 index) external;

    /// @notice Arbitrator resolves a disputed milestone
    /// @param index Zero-based milestone index
    /// @param resolution PAY_FREELANCER, REFUND_CLIENT, or SPLIT
    /// @param freelancerSplitAmount Amount to freelancer (only used for SPLIT)
    function resolveDispute(uint256 index, DisputeResolution resolution, uint256 freelancerSplitAmount) external;

    /// @notice Client or freelancer signs the emergency withdrawal request
    /// @dev Both parties must sign before emergencyWithdraw() can execute
    function signEmergencyWithdrawal() external;

    /// @notice Execute emergency withdrawal once both parties have signed
    /// @dev Returns all remaining funds to the client
    function emergencyWithdraw() external;

    // ─── View Functions ───────────────────────────────────────────────────────────

    /// @notice Current contract balance (ETH or ERC-20 units)
    function getBalance() external view returns (uint256);

    /// @notice Status of a specific milestone
    function getMilestoneStatus(uint256 index) external view returns (MilestoneStatus);

    /// @notice Whether the escrow has been funded
    function funded() external view returns (bool);

    /// @notice Total amount expected from deposit
    function totalAmount() external view returns (uint256);
}
