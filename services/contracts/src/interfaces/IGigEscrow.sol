// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IGigEscrow
/// @notice Interface for per-gig escrow contract managing milestone payments on SkillBridge.
interface IGigEscrow {
    // ─── Enums ───────────────────────────────────────────────────────────────

    enum MilestoneStatus {
        PENDING,
        COMPLETED,
        DISPUTED,
        REFUNDED
    }

    // ─── Events ──────────────────────────────────────────────────────────────

    event EscrowFunded(address indexed escrow, uint256 totalAmount);
    event MilestoneCompleted(uint256 indexed index, address indexed freelancer, uint256 amount);
    event DisputeRaised(uint256 indexed index, address indexed raisedBy);
    event DisputeResolved(uint256 indexed index, bool paidFreelancer, uint256 amount);
    event EmergencyWithdrawApproved(address indexed approver);
    event EmergencyWithdrawExecuted(uint256 clientRefund, uint256 freelancerAmount);

    // ─── Functions ───────────────────────────────────────────────────────────

    /// @notice Client deposits the total gig budget. Must equal the sum of all milestone amounts.
    function deposit() external payable;

    /// @notice Releases funds for a completed milestone to the freelancer.
    /// @dev Callable by client or arbitrator (API oracle).
    function completeMilestone(uint256 index) external;

    /// @notice Locks a milestone pending dispute resolution.
    /// @dev Callable by client or freelancer.
    function raiseDispute(uint256 index) external;

    /// @notice Resolves a disputed milestone.
    /// @dev Callable only by the arbitrator address.
    /// @param index Milestone index
    /// @param payFreelancer If true, release to freelancer; if false, refund to client.
    function resolveDispute(uint256 index, bool payFreelancer) external;

    /// @notice Records approval for emergency withdrawal. Both client and freelancer must approve.
    function approveEmergencyWithdraw() external;

    /// @notice Executes emergency withdrawal when both parties have approved.
    ///         Unreleased milestone funds are returned to client. Released funds stay with freelancer.
    function emergencyWithdraw() external;

    /// @notice Returns the ETH balance held by the contract.
    function getBalance() external view returns (uint256);

    /// @notice Returns the status and amount for a given milestone.
    function getMilestone(uint256 index) external view returns (MilestoneStatus status, uint256 amount);

    /// @notice Returns the total number of milestones.
    function milestoneCount() external view returns (uint256);
}
