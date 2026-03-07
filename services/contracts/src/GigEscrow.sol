// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IGigEscrow} from "./interfaces/IGigEscrow.sol";

/// @dev Minimal ERC-20 interface — only the functions GigEscrow needs
interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title GigEscrow
/// @notice Per-gig escrow contract for SkillBridge. Locks client funds and releases
///         them per-milestone on approval. Supports ETH and ERC-20 (USDC) payment.
/// @dev Deployed by EscrowFactory. The factory owner acts as arbitrator.
contract GigEscrow is IGigEscrow {
    // ─── Errors ───────────────────────────────────────────────────────────────────

    error OnlyClient();
    error OnlyArbitrator();
    error OnlyClientOrFreelancer();
    error AlreadyFunded();
    error NotFunded();
    error InvalidMilestoneIndex();
    error MilestoneNotPending();
    error MilestoneNotDisputed();
    error InvalidETHAmount();
    error NoETHForERC20();
    error SplitExceedsMilestone();
    error AlreadySigned();
    error NotBothSigned();
    error NoFundsToWithdraw();
    error ETHTransferFailed();
    error ERC20TransferFailed();
    /// @notice Reverts when ETH is sent directly instead of via deposit()
    error UseDepositInstead();

    // ─── Immutables ───────────────────────────────────────────────────────────────

    address public immutable client;
    address public immutable freelancer;
    /// @notice address(0) = ETH; any other = ERC-20 token (e.g. USDC on Base)
    address public immutable tokenAddress;
    address public immutable platformFeeRecipient;
    /// @notice Address allowed to call resolveDispute (factory owner / platform oracle)
    address public immutable arbitrator;
    uint256 public immutable platformFeeBasisPoints;
    uint256 public immutable totalAmount;

    // ─── Mutable State ────────────────────────────────────────────────────────────

    bool public funded;

    uint256[] private _milestoneAmounts;
    MilestoneStatus[] private _milestoneStatuses;

    /// @dev Emergency withdrawal: both parties must sign before execution
    bool public clientSignedEmergency;
    bool public freelancerSignedEmergency;

    // ─── Constructor ─────────────────────────────────────────────────────────────

    /// @param _client               Address that deposits funds and approves milestones
    /// @param _freelancer           Address that receives milestone payouts
    /// @param _tokenAddress         address(0) for ETH, ERC-20 contract address for tokens
    /// @param amounts               Per-milestone amounts (each must be > 0)
    /// @param _platformFeeBps       Fee in basis points, capped at 1000 (10%)
    /// @param _platformFeeRecipient Receives the platform cut on each completeMilestone
    /// @param _arbitrator           Allowed to resolve disputes (factory owner)
    constructor(
        address _client,
        address _freelancer,
        address _tokenAddress,
        uint256[] memory amounts,
        uint256 _platformFeeBps,
        address _platformFeeRecipient,
        address _arbitrator
    ) {
        require(_client != address(0), "GigEscrow: invalid client");
        require(_freelancer != address(0), "GigEscrow: invalid freelancer");
        require(_client != _freelancer, "GigEscrow: client and freelancer cannot be the same address");
        require(_platformFeeRecipient != address(0), "GigEscrow: invalid fee recipient");
        require(_arbitrator != address(0), "GigEscrow: invalid arbitrator");
        require(amounts.length > 0, "GigEscrow: no milestones");
        require(_platformFeeBps <= 1000, "GigEscrow: fee exceeds 10%");

        client = _client;
        freelancer = _freelancer;
        tokenAddress = _tokenAddress;
        platformFeeBasisPoints = _platformFeeBps;
        platformFeeRecipient = _platformFeeRecipient;
        arbitrator = _arbitrator;

        uint256 total;
        for (uint256 i; i < amounts.length; ++i) {
            require(amounts[i] > 0, "GigEscrow: milestone amount is zero");
            total += amounts[i];
            _milestoneAmounts.push(amounts[i]);
            _milestoneStatuses.push(MilestoneStatus.PENDING);
        }
        totalAmount = total;
    }

    // ─── Modifiers ────────────────────────────────────────────────────────────────

    modifier onlyClient() {
        if (msg.sender != client) revert OnlyClient();
        _;
    }

    modifier onlyArbitrator() {
        if (msg.sender != arbitrator) revert OnlyArbitrator();
        _;
    }

    modifier onlyClientOrFreelancer() {
        if (msg.sender != client && msg.sender != freelancer) revert OnlyClientOrFreelancer();
        _;
    }

    modifier whenFunded() {
        if (!funded) revert NotFunded();
        _;
    }

    modifier validIndex(uint256 index) {
        if (index >= _milestoneStatuses.length) revert InvalidMilestoneIndex();
        _;
    }

    // ─── Deposit ─────────────────────────────────────────────────────────────────

    /// @inheritdoc IGigEscrow
    function deposit() external payable onlyClient {
        if (funded) revert AlreadyFunded();

        if (tokenAddress == address(0)) {
            // ETH path: msg.value must equal totalAmount exactly
            if (msg.value != totalAmount) revert InvalidETHAmount();
        } else {
            // ERC-20 path: no ETH must accompany this call
            if (msg.value != 0) revert NoETHForERC20();
            bool ok = IERC20(tokenAddress).transferFrom(msg.sender, address(this), totalAmount);
            if (!ok) revert ERC20TransferFailed();
        }

        funded = true;
        emit EscrowFunded(client, totalAmount, tokenAddress);
    }

    // ─── Milestone Lifecycle ─────────────────────────────────────────────────────

    /// @inheritdoc IGigEscrow
    function completeMilestone(uint256 index)
        external
        onlyClient
        whenFunded
        validIndex(index)
    {
        if (_milestoneStatuses[index] != MilestoneStatus.PENDING) revert MilestoneNotPending();

        uint256 amount = _milestoneAmounts[index];
        uint256 fee = (amount * platformFeeBasisPoints) / 10_000;
        uint256 net = amount - fee;

        // Checks-effects-interactions: update state before external calls
        _milestoneStatuses[index] = MilestoneStatus.COMPLETED;

        _transfer(freelancer, net);
        if (fee > 0) _transfer(platformFeeRecipient, fee);

        emit FundsReleased(index, freelancer, net, fee);
    }

    /// @inheritdoc IGigEscrow
    function raiseDispute(uint256 index)
        external
        onlyClientOrFreelancer
        whenFunded
        validIndex(index)
    {
        if (_milestoneStatuses[index] != MilestoneStatus.PENDING) revert MilestoneNotPending();

        _milestoneStatuses[index] = MilestoneStatus.DISPUTED;
        emit DisputeRaised(index, msg.sender);
    }

    /// @inheritdoc IGigEscrow
    /// @dev PAY_FREELANCER pays the full milestone amount to the freelancer with no
    ///      platform fee deducted. This is intentional: dispute resolution is an
    ///      adversarial path initiated by the arbitrator, not a voluntary completion.
    ///      The platform fee applies only to cooperative completeMilestone() calls.
    ///      Known limitation: a colluding client+freelancer could game this to avoid
    ///      the fee. Mitigation: the arbitrator (platform) controls dispute resolution,
    ///      so self-serving disputes will be rejected at the off-chain review stage.
    function resolveDispute(uint256 index, DisputeResolution resolution, uint256 freelancerSplitAmount)
        external
        onlyArbitrator
        whenFunded
        validIndex(index)
    {
        if (_milestoneStatuses[index] != MilestoneStatus.DISPUTED) revert MilestoneNotDisputed();

        uint256 amount = _milestoneAmounts[index];
        uint256 freelancerPay;
        uint256 clientPay;

        if (resolution == DisputeResolution.PAY_FREELANCER) {
            // Full milestone amount to freelancer; no platform fee — see @dev above
            freelancerPay = amount;
        } else if (resolution == DisputeResolution.REFUND_CLIENT) {
            clientPay = amount;
        } else {
            // SPLIT: freelancerSplitAmount == 0 is allowed and is equivalent to a
            // full refund to the client (zero-split is a valid arbitration outcome).
            if (freelancerSplitAmount > amount) revert SplitExceedsMilestone();
            freelancerPay = freelancerSplitAmount;
            clientPay = amount - freelancerSplitAmount;
        }

        // Update state before transfers (CEI pattern)
        _milestoneStatuses[index] = MilestoneStatus.RESOLVED;

        if (freelancerPay > 0) _transfer(freelancer, freelancerPay);
        if (clientPay > 0) _transfer(client, clientPay);

        emit DisputeResolved(index, resolution, freelancerPay, clientPay);
    }

    // ─── Emergency Withdrawal (2-of-2 multisig) ───────────────────────────────────

    /// @inheritdoc IGigEscrow
    function signEmergencyWithdrawal() external onlyClientOrFreelancer {
        if (msg.sender == client) {
            if (clientSignedEmergency) revert AlreadySigned();
            clientSignedEmergency = true;
        } else {
            if (freelancerSignedEmergency) revert AlreadySigned();
            freelancerSignedEmergency = true;
        }
        emit EmergencyWithdrawalSigned(msg.sender);
    }

    /// @inheritdoc IGigEscrow
    /// @notice Returns all remaining contract balance to the client.
    /// @dev Known limitation: this always returns funds to the client, even in cases
    ///      where the client is the bad actor. Both parties must consent (2-of-2 sign),
    ///      which means a fraudulent client cannot unilaterally drain the escrow —
    ///      but once the freelancer has also signed, the client receives everything.
    ///      For v1 this is acceptable; a future version may split by milestone status.
    function emergencyWithdraw() external onlyClientOrFreelancer {
        if (!clientSignedEmergency || !freelancerSignedEmergency) revert NotBothSigned();

        uint256 bal = getBalance();
        if (bal == 0) revert NoFundsToWithdraw();

        // Reset signatures before transfer to prevent re-entrancy re-execution
        clientSignedEmergency = false;
        freelancerSignedEmergency = false;

        emit EmergencyWithdrawal(bal);
        _transfer(client, bal);
    }

    // ─── View Functions ───────────────────────────────────────────────────────────

    /// @inheritdoc IGigEscrow
    function getBalance() public view returns (uint256) {
        if (tokenAddress == address(0)) {
            return address(this).balance;
        }
        return IERC20(tokenAddress).balanceOf(address(this));
    }

    /// @inheritdoc IGigEscrow
    function getMilestoneStatus(uint256 index) external view validIndex(index) returns (MilestoneStatus) {
        return _milestoneStatuses[index];
    }

    /// @notice Number of milestones in this escrow
    function milestoneCount() external view returns (uint256) {
        return _milestoneStatuses.length;
    }

    /// @notice Amount allocated to a specific milestone
    function getMilestoneAmount(uint256 index) external view validIndex(index) returns (uint256) {
        return _milestoneAmounts[index];
    }

    // ─── Internal ─────────────────────────────────────────────────────────────────

    /// @dev Transfers `amount` of the escrow's asset to `to`
    function _transfer(address to, uint256 amount) internal {
        if (tokenAddress == address(0)) {
            (bool ok,) = to.call{value: amount}("");
            if (!ok) revert ETHTransferFailed();
        } else {
            bool ok = IERC20(tokenAddress).transfer(to, amount);
            if (!ok) revert ERC20TransferFailed();
        }
    }

    // ─── Reject accidental ETH ────────────────────────────────────────────────────

    /// @dev Direct ETH sends are rejected; use deposit()
    receive() external payable {
        revert UseDepositInstead();
    }
}
