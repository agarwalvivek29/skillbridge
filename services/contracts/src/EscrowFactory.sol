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
    error InvalidFeeRecipient();
    error InvalidClient();
    error InvalidFreelancer();

    // ─── State ────────────────────────────────────────────────────────────────────

    address public owner;
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
    function createEscrow(
        address client,
        address freelancer,
        address tokenAddress,
        uint256[] calldata milestoneAmounts,
        uint256 platformFeeBasisPoints
    ) external returns (address escrowAddress) {
        if (client == address(0)) revert InvalidClient();
        if (freelancer == address(0)) revert InvalidFreelancer();

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

        uint256 total;
        for (uint256 i; i < milestoneAmounts.length; ++i) {
            total += milestoneAmounts[i];
        }

        emit EscrowCreated(escrowAddress, client, freelancer, tokenAddress, total);
    }

    // ─── Admin Functions ──────────────────────────────────────────────────────────

    /// @inheritdoc IEscrowFactory
    function setFeeRecipient(address newRecipient) external onlyOwner {
        if (newRecipient == address(0)) revert InvalidFeeRecipient();
        emit FeeRecipientUpdated(feeRecipient, newRecipient);
        feeRecipient = newRecipient;
    }

    /// @notice Transfer factory ownership (and arbitrator rights) to a new address
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "EscrowFactory: invalid new owner");
        owner = newOwner;
    }

    // ─── View Functions ───────────────────────────────────────────────────────────

    /// @inheritdoc IEscrowFactory
    function getAllEscrows() external view returns (address[] memory) {
        return _allEscrows;
    }
}
