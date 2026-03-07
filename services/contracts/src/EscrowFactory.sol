// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IEscrowFactory} from "./interfaces/IEscrowFactory.sol";
import {GigEscrow} from "./GigEscrow.sol";

/// @title EscrowFactory
/// @notice Deploys one GigEscrow contract per gig. The factory owner acts as the
///         platform oracle / arbitrator for all deployed escrows.
/// @dev Single deployed instance on Base L2. The api service calls createEscrow
///      after a gig is funded on-chain.
contract EscrowFactory is IEscrowFactory {
    // ─── Errors ───────────────────────────────────────────────────────────────────

    error OnlyOwner();
    error OnlyPendingOwner();
    error InvalidFeeRecipient();
    error InvalidClient();
    error InvalidFreelancer();
    /// @notice Reverts when milestoneAmounts array is empty
    error InvalidMilestones();
    /// @notice Reverts when a required address argument is the zero address
    error ZeroAddress();
    /// @notice Reverts when client and freelancer are the same address
    error ClientEqualsFreelancer();
    /// @notice Reverts when a milestone amount of zero is provided
    error ZeroMilestoneAmount();
    /// @notice Reverts when platformFeeBasisPoints exceeds 1000 (10%)
    error FeeTooHigh();

    // ─── Events ───────────────────────────────────────────────────────────────────

    /// @notice Emitted when ownership transfer is completed
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    /// @notice Emitted when a new ownership transfer is proposed
    event OwnershipTransferProposed(address indexed currentOwner, address indexed pendingOwner);

    // ─── State ────────────────────────────────────────────────────────────────────

    address public owner;
    /// @notice Pending owner for two-step ownership transfer; address(0) when no transfer is in progress
    address public pendingOwner;
    address public feeRecipient;

    address[] private _allEscrows;

    // ─── Constructor ─────────────────────────────────────────────────────────────

    /// @param _feeRecipient Initial address to receive platform fees
    constructor(address _feeRecipient) {
        require(_feeRecipient != address(0), "EscrowFactory: invalid fee recipient");
        owner = msg.sender;
        feeRecipient = _feeRecipient;
    }

    // ─── Modifiers ────────────────────────────────────────────────────────────────

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    // ─── Factory Function ────────────────────────────────────────────────────────

    /// @inheritdoc IEscrowFactory
    /// @notice Deploy a new GigEscrow for a gig. Callable only by the factory owner.
    /// @dev Access is restricted to the owner to prevent spam/grief attacks and
    ///      fake client registrations. The api service calls this on behalf of clients
    ///      after verifying the gig on-chain.
    function createEscrow(
        address client,
        address freelancer,
        address tokenAddress,
        uint256[] calldata milestoneAmounts,
        uint256 platformFeeBasisPoints
    ) external onlyOwner returns (address escrowAddress) {
        if (client == address(0)) revert ZeroAddress();
        if (freelancer == address(0)) revert ZeroAddress();
        if (client == freelancer) revert ClientEqualsFreelancer();
        if (milestoneAmounts.length == 0) revert InvalidMilestones();
        for (uint256 i = 0; i < milestoneAmounts.length; i++) {
            if (milestoneAmounts[i] == 0) revert ZeroMilestoneAmount();
        }
        if (platformFeeBasisPoints > 1000) revert FeeTooHigh();

        GigEscrow escrow = new GigEscrow(
            client,
            freelancer,
            tokenAddress,
            milestoneAmounts,
            platformFeeBasisPoints,
            feeRecipient,
            owner // factory owner is the arbitrator
        );

        escrowAddress = address(escrow);
        _allEscrows.push(escrowAddress);

        emit EscrowCreated(escrowAddress, client, freelancer, tokenAddress, escrow.totalAmount());
    }

    // ─── Admin Functions ──────────────────────────────────────────────────────────

    /// @inheritdoc IEscrowFactory
    /// @notice Update the platform fee recipient.
    /// @dev The new feeRecipient is captured at deploy time for each GigEscrow, so
    ///      this change affects only escrows created after this call. Existing deployed
    ///      escrows retain the feeRecipient value set when they were deployed.
    function setFeeRecipient(address newRecipient) external onlyOwner {
        if (newRecipient == address(0)) revert InvalidFeeRecipient();
        emit FeeRecipientUpdated(feeRecipient, newRecipient);
        feeRecipient = newRecipient;
    }

    /// @notice Propose a new owner. The proposed address must call acceptOwnership() to complete the transfer.
    /// @dev Two-step transfer prevents loss of ownership due to typos or compromised keys.
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

    // ─── View Functions ───────────────────────────────────────────────────────────

    /// @notice Number of escrows deployed by this factory
    function getEscrowCount() external view returns (uint256) {
        return _allEscrows.length;
    }

    /// @notice Get the escrow address at a specific index (for paginated access)
    function getEscrow(uint256 index) external view returns (address) {
        require(index < _allEscrows.length, "EscrowFactory: index out of bounds");
        return _allEscrows[index];
    }

    /// @inheritdoc IEscrowFactory
    /// @notice WARNING: unbounded — will revert at scale due to block gas limit.
    ///         Use getEscrowCount() + getEscrow(index) for production pagination.
    function getAllEscrows() external view returns (address[] memory) {
        return _allEscrows;
    }
}
