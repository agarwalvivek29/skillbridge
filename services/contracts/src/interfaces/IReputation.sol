// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IReputation
/// @notice Interface for the on-chain reputation contract on SkillBridge.
///         Stores aggregated per-address stats: gigs completed, total earned,
///         and average AI quality score. Updated by the platform oracle on
///         every milestone completion.
interface IReputation {
    // ─── Events ──────────────────────────────────────────────────────────────────

    /// @notice Emitted when a freelancer's reputation record is updated
    event ReputationUpdated(
        address indexed freelancer,
        uint256 gigsCompleted,
        uint256 totalEarned,
        uint256 averageAiScore
    );

    // ─── Core Functions ──────────────────────────────────────────────────────────

    /// @notice Record a milestone completion for a freelancer
    /// @param freelancer Address of the freelancer
    /// @param earned Amount earned from this milestone (wei / token units)
    /// @param aiScore AI quality score for this submission (0–100)
    function recordCompletion(
        address freelancer,
        uint256 earned,
        uint256 aiScore
    ) external;

    // ─── View Functions ──────────────────────────────────────────────────────────

    /// @notice Number of gigs completed by this address
    function gigsCompleted(address freelancer) external view returns (uint256);

    /// @notice Total amount earned by this address (cumulative, in wei / token units)
    function totalEarned(address freelancer) external view returns (uint256);

    /// @notice Average AI quality score (0–100) across all reviewed submissions
    function averageAiScore(address freelancer) external view returns (uint256);
}
