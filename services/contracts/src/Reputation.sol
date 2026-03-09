// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IReputation} from "./interfaces/IReputation.sol";

/// @title Reputation
/// @notice On-chain reputation aggregator for SkillBridge. Stores per-address
///         stats updated on every milestone completion: gigs completed,
///         cumulative earnings, and rolling average AI quality score.
/// @dev Deployed once on Base L2. The factory owner (platform oracle) calls
///      recordCompletion() after each GigEscrow.completeMilestone() event.
///      Two-step ownership transfer for safety.
contract Reputation is IReputation {
    // ─── Errors ───────────────────────────────────────────────────────────────────

    error OnlyOwner();
    error OnlyPendingOwner();
    error ZeroAddress();
    error InvalidAiScore();

    // ─── Events ───────────────────────────────────────────────────────────────────

    event OwnershipTransferProposed(address indexed currentOwner, address indexed pendingOwner);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    // ─── State ────────────────────────────────────────────────────────────────────

    address public owner;
    address public pendingOwner;

    struct Record {
        uint256 gigsCompleted;
        uint256 totalEarned;
        /// @dev Running sum of all AI scores — divide by gigsCompleted for average
        uint256 aiScoreSum;
    }

    mapping(address => Record) private _records;

    // ─── Constructor ─────────────────────────────────────────────────────────────

    constructor() {
        owner = msg.sender;
    }

    // ─── Modifiers ────────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    // ─── Core Functions ──────────────────────────────────────────────────────────

    /// @inheritdoc IReputation
    function recordCompletion(
        address freelancer,
        uint256 earned,
        uint256 aiScore
    ) external onlyOwner {
        if (freelancer == address(0)) revert ZeroAddress();
        if (aiScore > 100) revert InvalidAiScore();

        Record storage r = _records[freelancer];
        r.gigsCompleted += 1;
        r.totalEarned += earned;
        r.aiScoreSum += aiScore;

        emit ReputationUpdated(
            freelancer,
            r.gigsCompleted,
            r.totalEarned,
            r.aiScoreSum / r.gigsCompleted
        );
    }

    // ─── Ownership ───────────────────────────────────────────────────────────────

    /// @notice Propose a new owner. The proposed address must call acceptOwnership().
    function proposeOwner(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        pendingOwner = newOwner;
        emit OwnershipTransferProposed(owner, newOwner);
    }

    /// @notice Accept ownership transfer. Must be called by the pendingOwner.
    function acceptOwnership() external {
        if (msg.sender != pendingOwner) revert OnlyPendingOwner();
        address previous = owner;
        owner = pendingOwner;
        pendingOwner = address(0);
        emit OwnershipTransferred(previous, owner);
    }

    // ─── View Functions ──────────────────────────────────────────────────────────

    /// @inheritdoc IReputation
    function gigsCompleted(address freelancer) external view returns (uint256) {
        return _records[freelancer].gigsCompleted;
    }

    /// @inheritdoc IReputation
    function totalEarned(address freelancer) external view returns (uint256) {
        return _records[freelancer].totalEarned;
    }

    /// @inheritdoc IReputation
    function averageAiScore(address freelancer) external view returns (uint256) {
        Record storage r = _records[freelancer];
        if (r.gigsCompleted == 0) return 0;
        return r.aiScoreSum / r.gigsCompleted;
    }

    /// @notice Raw AI score sum for a freelancer (for off-chain verification)
    function aiScoreSum(address freelancer) external view returns (uint256) {
        return _records[freelancer].aiScoreSum;
    }
}
