// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./interfaces/IGigEscrow.sol";

/// @title GigEscrow
/// @notice Per-gig escrow contract. Locks client funds at creation, releases them
///         per-milestone when approved, and supports dispute resolution.
///
/// @dev Access control:
///   - deposit()                   → client only
///   - completeMilestone()         → client or arbitrator
///   - raiseDispute()              → client or freelancer
///   - resolveDispute()            → arbitrator only
///   - approveEmergencyWithdraw()  → client or freelancer
///   - emergencyWithdraw()         → anyone (after both parties approved)
///
/// Security notes:
///   - Follows checks-effects-interactions: state is updated before ETH transfers.
///   - Solidity 0.8.x built-in overflow protection.
///   - No upgradeable proxy — immutable after deployment.
contract GigEscrow is IGigEscrow {
    // ─── State ────────────────────────────────────────────────────────────────

    address public immutable client;
    address public immutable freelancer;
    address public immutable arbitrator;

    bool public funded;
    uint256 private immutable _totalAmount;

    uint256[] private _amounts;
    MilestoneStatus[] private _statuses;

    mapping(address => bool) public emergencyApprovals;
    bool private _emergencyExecuted;

    // ─── Modifiers ────────────────────────────────────────────────────────────

    modifier onlyClient() {
        require(msg.sender == client, "GigEscrow: caller is not client");
        _;
    }

    modifier onlyArbitrator() {
        require(msg.sender == arbitrator, "GigEscrow: caller is not arbitrator");
        _;
    }

    modifier onlyClientOrArbitrator() {
        require(msg.sender == client || msg.sender == arbitrator, "GigEscrow: unauthorized");
        _;
    }

    modifier onlyParty() {
        require(msg.sender == client || msg.sender == freelancer, "GigEscrow: caller is not a party");
        _;
    }

    modifier notEmergencyExecuted() {
        require(!_emergencyExecuted, "GigEscrow: emergency withdrawal already executed");
        _;
    }

    // ─── Constructor ─────────────────────────────────────────────────────────

    /// @param _client       Address of the client
    /// @param _freelancer   Address of the freelancer
    /// @param _arbitrator   Address of the arbitration oracle (API or multisig)
    /// @param amounts_      Per-milestone amounts in wei
    constructor(
        address _client,
        address _freelancer,
        address _arbitrator,
        uint256[] memory amounts_
    ) {
        require(_client != address(0), "GigEscrow: zero client address");
        require(_freelancer != address(0), "GigEscrow: zero freelancer address");
        require(_arbitrator != address(0), "GigEscrow: zero arbitrator address");
        require(_client != _freelancer, "GigEscrow: client equals freelancer");
        require(amounts_.length > 0, "GigEscrow: no milestones");

        client = _client;
        freelancer = _freelancer;
        arbitrator = _arbitrator;

        uint256 total;
        for (uint256 i; i < amounts_.length; ++i) {
            require(amounts_[i] > 0, "GigEscrow: milestone amount must be > 0");
            total += amounts_[i];
            _amounts.push(amounts_[i]);
            _statuses.push(MilestoneStatus.PENDING);
        }
        _totalAmount = total;
    }

    // ─── Deposit ──────────────────────────────────────────────────────────────

    /// @inheritdoc IGigEscrow
    function deposit() external payable onlyClient notEmergencyExecuted {
        require(!funded, "GigEscrow: already funded");
        require(msg.value == _totalAmount, "GigEscrow: incorrect deposit amount");

        // Effects
        funded = true;

        // No external interaction needed — ETH stays in contract
        emit EscrowFunded(address(this), msg.value);
    }

    // ─── Milestone completion ─────────────────────────────────────────────────

    /// @inheritdoc IGigEscrow
    function completeMilestone(uint256 index) external onlyClientOrArbitrator notEmergencyExecuted {
        require(funded, "GigEscrow: not funded");
        require(index < _amounts.length, "GigEscrow: invalid milestone index");
        require(_statuses[index] == MilestoneStatus.PENDING, "GigEscrow: milestone not in PENDING state");

        uint256 amount = _amounts[index];

        // Effects
        _statuses[index] = MilestoneStatus.COMPLETED;

        // Interactions — ETH transfer last (CEI)
        (bool success,) = freelancer.call{value: amount}("");
        require(success, "GigEscrow: transfer to freelancer failed");

        emit MilestoneCompleted(index, freelancer, amount);
    }

    // ─── Dispute ──────────────────────────────────────────────────────────────

    /// @inheritdoc IGigEscrow
    function raiseDispute(uint256 index) external onlyParty notEmergencyExecuted {
        require(funded, "GigEscrow: not funded");
        require(index < _amounts.length, "GigEscrow: invalid milestone index");
        require(_statuses[index] == MilestoneStatus.PENDING, "GigEscrow: milestone not in PENDING state");

        // Effects
        _statuses[index] = MilestoneStatus.DISPUTED;

        emit DisputeRaised(index, msg.sender);
    }

    /// @inheritdoc IGigEscrow
    function resolveDispute(uint256 index, bool payFreelancer) external onlyArbitrator notEmergencyExecuted {
        require(index < _amounts.length, "GigEscrow: invalid milestone index");
        require(_statuses[index] == MilestoneStatus.DISPUTED, "GigEscrow: milestone not in DISPUTED state");

        uint256 amount = _amounts[index];

        if (payFreelancer) {
            // Effects
            _statuses[index] = MilestoneStatus.COMPLETED;
            // Interactions
            (bool success,) = freelancer.call{value: amount}("");
            require(success, "GigEscrow: transfer to freelancer failed");
        } else {
            // Effects
            _statuses[index] = MilestoneStatus.REFUNDED;
            // Interactions
            (bool success,) = client.call{value: amount}("");
            require(success, "GigEscrow: refund to client failed");
        }

        emit DisputeResolved(index, payFreelancer, amount);
    }

    // ─── Emergency withdrawal ─────────────────────────────────────────────────

    /// @inheritdoc IGigEscrow
    function approveEmergencyWithdraw() external onlyParty {
        require(!emergencyApprovals[msg.sender], "GigEscrow: already approved");
        emergencyApprovals[msg.sender] = true;
        emit EmergencyWithdrawApproved(msg.sender);
    }

    /// @inheritdoc IGigEscrow
    /// @notice Distributes remaining balance back to client. Both client and freelancer
    ///         must have called approveEmergencyWithdraw() first.
    function emergencyWithdraw() external notEmergencyExecuted {
        require(
            emergencyApprovals[client] && emergencyApprovals[freelancer],
            "GigEscrow: both parties must approve"
        );

        // Effects — mark executed before any transfer
        _emergencyExecuted = true;

        uint256 remaining = address(this).balance;

        // Return remaining funds to client
        if (remaining > 0) {
            (bool success,) = client.call{value: remaining}("");
            require(success, "GigEscrow: emergency refund to client failed");
        }

        emit EmergencyWithdrawExecuted(remaining, 0);
    }

    // ─── View functions ───────────────────────────────────────────────────────

    /// @inheritdoc IGigEscrow
    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }

    /// @inheritdoc IGigEscrow
    function getMilestone(uint256 index) external view returns (MilestoneStatus status, uint256 amount) {
        require(index < _amounts.length, "GigEscrow: invalid milestone index");
        return (_statuses[index], _amounts[index]);
    }

    /// @inheritdoc IGigEscrow
    function milestoneCount() external view returns (uint256) {
        return _amounts.length;
    }

    /// @notice Returns the total amount that must be deposited.
    function totalAmount() external view returns (uint256) {
        return _totalAmount;
    }

    // ─── Receive / fallback ───────────────────────────────────────────────────

    /// @dev Reject accidental ETH sends outside of deposit().
    receive() external payable {
        revert("GigEscrow: use deposit()");
    }

    fallback() external payable {
        revert("GigEscrow: use deposit()");
    }
}
