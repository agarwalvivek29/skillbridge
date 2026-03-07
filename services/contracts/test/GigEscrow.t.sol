// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {GigEscrow} from "../src/GigEscrow.sol";
import {IGigEscrow} from "../src/interfaces/IGigEscrow.sol";

/// @dev Minimal ERC-20 mock for testing
contract MockERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    function mint(address to, uint256 amount) external {
        balanceOf[to] += amount;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(balanceOf[from] >= amount, "insufficient balance");
        require(allowance[from][msg.sender] >= amount, "insufficient allowance");
        allowance[from][msg.sender] -= amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}

contract GigEscrowTest is Test {
    // ─── Actors ───────────────────────────────────────────────────────────────────

    address constant CLIENT = address(0xC11E01);
    address constant FREELANCER = address(0xF12EE);
    address constant ARBITRATOR = address(0xA12B);
    address constant FEE_RECIPIENT = address(0xFEE);
    address constant STRANGER = address(0x5773);

    uint256 constant FEE_BPS = 500; // 5%

    // ─── Fixtures ─────────────────────────────────────────────────────────────────

    GigEscrow internal escrow;
    MockERC20 internal token;

    uint256[] internal twoMilestones;

    function setUp() public {
        twoMilestones = new uint256[](2);
        twoMilestones[0] = 1 ether;
        twoMilestones[1] = 2 ether;

        escrow = new GigEscrow(
            CLIENT,
            FREELANCER,
            address(0), // ETH
            twoMilestones,
            FEE_BPS,
            FEE_RECIPIENT,
            ARBITRATOR
        );

        token = new MockERC20();
    }

    // ─── Helper ───────────────────────────────────────────────────────────────────

    function _makeERC20Escrow(uint256[] memory amounts) internal returns (GigEscrow erc20Escrow) {
        erc20Escrow = new GigEscrow(
            CLIENT,
            FREELANCER,
            address(token),
            amounts,
            FEE_BPS,
            FEE_RECIPIENT,
            ARBITRATOR
        );
    }

    function _fundETH(GigEscrow e) internal {
        uint256 total = e.totalAmount();
        vm.deal(CLIENT, total);
        vm.prank(CLIENT);
        e.deposit{value: total}();
    }

    function _fundERC20(GigEscrow e) internal {
        uint256 total = e.totalAmount();
        token.mint(CLIENT, total);
        vm.prank(CLIENT);
        token.approve(address(e), total);
        vm.prank(CLIENT);
        e.deposit();
    }

    // ─── Constructor ─────────────────────────────────────────────────────────────

    function test_constructor_storesParams() public view {
        assertEq(escrow.client(), CLIENT);
        assertEq(escrow.freelancer(), FREELANCER);
        assertEq(escrow.tokenAddress(), address(0));
        assertEq(escrow.platformFeeBasisPoints(), FEE_BPS);
        assertEq(escrow.platformFeeRecipient(), FEE_RECIPIENT);
        assertEq(escrow.arbitrator(), ARBITRATOR);
        assertEq(escrow.totalAmount(), 3 ether);
        assertEq(escrow.milestoneCount(), 2);
        assertFalse(escrow.funded());
    }

    function test_constructor_revertsOnNoMilestones() public {
        uint256[] memory empty;
        vm.expectRevert("GigEscrow: no milestones");
        new GigEscrow(CLIENT, FREELANCER, address(0), empty, FEE_BPS, FEE_RECIPIENT, ARBITRATOR);
    }

    function test_constructor_revertsOnZeroMilestoneAmount() public {
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = 0;
        vm.expectRevert("GigEscrow: milestone amount is zero");
        new GigEscrow(CLIENT, FREELANCER, address(0), amounts, FEE_BPS, FEE_RECIPIENT, ARBITRATOR);
    }

    function test_constructor_revertsOnFeeExceedsCap() public {
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = 1 ether;
        vm.expectRevert("GigEscrow: fee exceeds 10%");
        new GigEscrow(CLIENT, FREELANCER, address(0), amounts, 1001, FEE_RECIPIENT, ARBITRATOR);
    }

    // ─── deposit() — ETH ─────────────────────────────────────────────────────────

    function test_deposit_ETH_success() public {
        vm.deal(CLIENT, 3 ether);
        vm.expectEmit(true, false, false, true);
        emit IGigEscrow.EscrowFunded(CLIENT, 3 ether, address(0));

        vm.prank(CLIENT);
        escrow.deposit{value: 3 ether}();

        assertTrue(escrow.funded());
        assertEq(address(escrow).balance, 3 ether);
    }

    function test_deposit_ETH_revertsOnWrongAmount() public {
        vm.deal(CLIENT, 10 ether);
        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.InvalidETHAmount.selector);
        escrow.deposit{value: 1 ether}();
    }

    function test_deposit_ETH_revertsOnDoubleDeposit() public {
        _fundETH(escrow);
        vm.deal(CLIENT, 3 ether);
        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.AlreadyFunded.selector);
        escrow.deposit{value: 3 ether}();
    }

    function test_deposit_ETH_revertsForNonClient() public {
        vm.deal(STRANGER, 3 ether);
        vm.prank(STRANGER);
        vm.expectRevert(GigEscrow.OnlyClient.selector);
        escrow.deposit{value: 3 ether}();
    }

    // ─── deposit() — ERC-20 ──────────────────────────────────────────────────────

    function test_deposit_ERC20_success() public {
        GigEscrow e = _makeERC20Escrow(twoMilestones);
        uint256 total = e.totalAmount();
        token.mint(CLIENT, total);

        vm.prank(CLIENT);
        token.approve(address(e), total);

        vm.expectEmit(true, false, false, true);
        emit IGigEscrow.EscrowFunded(CLIENT, total, address(token));

        vm.prank(CLIENT);
        e.deposit();

        assertTrue(e.funded());
        assertEq(token.balanceOf(address(e)), total);
    }

    function test_deposit_ERC20_revertsIfETHSent() public {
        GigEscrow e = _makeERC20Escrow(twoMilestones);
        token.mint(CLIENT, e.totalAmount());
        vm.prank(CLIENT);
        token.approve(address(e), e.totalAmount());

        vm.deal(CLIENT, 1);
        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.NoETHForERC20.selector);
        e.deposit{value: 1}();
    }

    // ─── completeMilestone() — ETH ───────────────────────────────────────────────

    function test_completeMilestone_ETH_success() public {
        _fundETH(escrow);

        uint256 freelancerBefore = FREELANCER.balance;
        uint256 feeBefore = FEE_RECIPIENT.balance;

        // milestone 0 = 1 ether; fee = 5% = 0.05 ether; net = 0.95 ether
        vm.expectEmit(true, true, false, true);
        emit IGigEscrow.FundsReleased(0, FREELANCER, 0.95 ether, 0.05 ether);

        vm.prank(CLIENT);
        escrow.completeMilestone(0);

        assertEq(FREELANCER.balance - freelancerBefore, 0.95 ether);
        assertEq(FEE_RECIPIENT.balance - feeBefore, 0.05 ether);
        assertEq(uint8(escrow.getMilestoneStatus(0)), uint8(IGigEscrow.MilestoneStatus.COMPLETED));
    }

    function test_completeMilestone_ETH_revertsOnlyClient() public {
        _fundETH(escrow);
        vm.prank(STRANGER);
        vm.expectRevert(GigEscrow.OnlyClient.selector);
        escrow.completeMilestone(0);
    }

    function test_completeMilestone_revertsNotFunded() public {
        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.NotFunded.selector);
        escrow.completeMilestone(0);
    }

    function test_completeMilestone_revertsInvalidIndex() public {
        _fundETH(escrow);
        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.InvalidMilestoneIndex.selector);
        escrow.completeMilestone(99);
    }

    function test_completeMilestone_revertsOnAlreadyCompleted() public {
        _fundETH(escrow);
        vm.prank(CLIENT);
        escrow.completeMilestone(0);

        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.MilestoneNotPending.selector);
        escrow.completeMilestone(0);
    }

    // ─── completeMilestone() — ERC-20 ────────────────────────────────────────────

    function test_completeMilestone_ERC20_success() public {
        GigEscrow e = _makeERC20Escrow(twoMilestones);
        _fundERC20(e);

        uint256 freelancerBefore = token.balanceOf(FREELANCER);
        uint256 feeBefore = token.balanceOf(FEE_RECIPIENT);

        vm.prank(CLIENT);
        e.completeMilestone(0); // 1 ether, 5% fee

        assertEq(token.balanceOf(FREELANCER) - freelancerBefore, 0.95 ether);
        assertEq(token.balanceOf(FEE_RECIPIENT) - feeBefore, 0.05 ether);
    }

    // ─── raiseDispute() ──────────────────────────────────────────────────────────

    function test_raiseDispute_byClient() public {
        _fundETH(escrow);

        vm.expectEmit(true, true, false, false);
        emit IGigEscrow.DisputeRaised(0, CLIENT);

        vm.prank(CLIENT);
        escrow.raiseDispute(0);

        assertEq(uint8(escrow.getMilestoneStatus(0)), uint8(IGigEscrow.MilestoneStatus.DISPUTED));
    }

    function test_raiseDispute_byFreelancer() public {
        _fundETH(escrow);

        vm.expectEmit(true, true, false, false);
        emit IGigEscrow.DisputeRaised(1, FREELANCER);

        vm.prank(FREELANCER);
        escrow.raiseDispute(1);

        assertEq(uint8(escrow.getMilestoneStatus(1)), uint8(IGigEscrow.MilestoneStatus.DISPUTED));
    }

    function test_raiseDispute_revertsStranger() public {
        _fundETH(escrow);
        vm.prank(STRANGER);
        vm.expectRevert(GigEscrow.OnlyClientOrFreelancer.selector);
        escrow.raiseDispute(0);
    }

    function test_raiseDispute_revertsIfAlreadyDisputed() public {
        _fundETH(escrow);
        vm.prank(CLIENT);
        escrow.raiseDispute(0);

        vm.prank(FREELANCER);
        vm.expectRevert(GigEscrow.MilestoneNotPending.selector);
        escrow.raiseDispute(0);
    }

    // ─── resolveDispute() ────────────────────────────────────────────────────────

    function _disputeMilestone(uint256 index) internal {
        _fundETH(escrow);
        vm.prank(CLIENT);
        escrow.raiseDispute(index);
    }

    function test_resolveDispute_payFreelancer() public {
        _disputeMilestone(0);
        uint256 before = FREELANCER.balance;

        vm.prank(ARBITRATOR);
        escrow.resolveDispute(0, IGigEscrow.DisputeResolution.PAY_FREELANCER, 0);

        assertEq(FREELANCER.balance - before, 1 ether);
        assertEq(uint8(escrow.getMilestoneStatus(0)), uint8(IGigEscrow.MilestoneStatus.RESOLVED));
    }

    function test_resolveDispute_refundClient() public {
        _disputeMilestone(0);
        uint256 before = CLIENT.balance;

        vm.prank(ARBITRATOR);
        escrow.resolveDispute(0, IGigEscrow.DisputeResolution.REFUND_CLIENT, 0);

        assertEq(CLIENT.balance - before, 1 ether);
        assertEq(uint8(escrow.getMilestoneStatus(0)), uint8(IGigEscrow.MilestoneStatus.RESOLVED));
    }

    function test_resolveDispute_split() public {
        _disputeMilestone(0);
        uint256 freelancerBefore = FREELANCER.balance;
        uint256 clientBefore = CLIENT.balance;

        // Split: freelancer gets 0.6, client gets 0.4
        vm.prank(ARBITRATOR);
        escrow.resolveDispute(0, IGigEscrow.DisputeResolution.SPLIT, 0.6 ether);

        assertEq(FREELANCER.balance - freelancerBefore, 0.6 ether);
        assertEq(CLIENT.balance - clientBefore, 0.4 ether);
    }

    function test_resolveDispute_revertsOnlyArbitrator() public {
        _disputeMilestone(0);
        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.OnlyArbitrator.selector);
        escrow.resolveDispute(0, IGigEscrow.DisputeResolution.PAY_FREELANCER, 0);
    }

    function test_resolveDispute_revertsIfNotDisputed() public {
        _fundETH(escrow);
        vm.prank(ARBITRATOR);
        vm.expectRevert(GigEscrow.MilestoneNotDisputed.selector);
        escrow.resolveDispute(0, IGigEscrow.DisputeResolution.PAY_FREELANCER, 0);
    }

    function test_resolveDispute_revertsIfSplitExceedsMilestone() public {
        _disputeMilestone(0);
        vm.prank(ARBITRATOR);
        vm.expectRevert(GigEscrow.SplitExceedsMilestone.selector);
        escrow.resolveDispute(0, IGigEscrow.DisputeResolution.SPLIT, 2 ether); // > 1 ether milestone
    }

    // ─── Emergency Withdrawal ────────────────────────────────────────────────────

    function test_emergencyWithdraw_requiresBothSignatures() public {
        _fundETH(escrow);

        // Only client signs
        vm.prank(CLIENT);
        escrow.signEmergencyWithdrawal();

        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.NotBothSigned.selector);
        escrow.emergencyWithdraw();
    }

    function test_emergencyWithdraw_success() public {
        _fundETH(escrow);
        uint256 clientBefore = CLIENT.balance;

        vm.prank(CLIENT);
        escrow.signEmergencyWithdrawal();

        vm.prank(FREELANCER);
        escrow.signEmergencyWithdrawal();

        uint256 bal = escrow.getBalance();

        vm.expectEmit(false, false, false, true);
        emit IGigEscrow.EmergencyWithdrawal(bal);

        vm.prank(CLIENT);
        escrow.emergencyWithdraw();

        assertEq(CLIENT.balance - clientBefore, 3 ether);
        assertEq(address(escrow).balance, 0);
    }

    function test_emergencyWithdraw_revertsOnDoubleSigning() public {
        _fundETH(escrow);
        vm.prank(CLIENT);
        escrow.signEmergencyWithdrawal();

        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.AlreadySigned.selector);
        escrow.signEmergencyWithdrawal();
    }

    function test_emergencyWithdraw_revertsNoFunds() public {
        vm.prank(CLIENT);
        escrow.signEmergencyWithdrawal();
        vm.prank(FREELANCER);
        escrow.signEmergencyWithdrawal();

        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.NoFundsToWithdraw.selector);
        escrow.emergencyWithdraw();
    }

    // ─── Fuzz: completeMilestone fee accounting (ETH) ────────────────────────────

    /// @dev Verifies: fee + net == amount, net goes to freelancer, fee to recipient
    function testFuzz_completeMilestone_feeAccountingETH(uint96 milestoneAmount) public {
        vm.assume(milestoneAmount > 0);

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = milestoneAmount;

        GigEscrow e = new GigEscrow(CLIENT, FREELANCER, address(0), amounts, FEE_BPS, FEE_RECIPIENT, ARBITRATOR);

        vm.deal(CLIENT, milestoneAmount);
        vm.prank(CLIENT);
        e.deposit{value: milestoneAmount}();

        uint256 freelancerBefore = FREELANCER.balance;
        uint256 feeBefore = FEE_RECIPIENT.balance;

        vm.prank(CLIENT);
        e.completeMilestone(0);

        uint256 expectedFee = (uint256(milestoneAmount) * FEE_BPS) / 10_000;
        uint256 expectedNet = milestoneAmount - expectedFee;

        assertEq(FREELANCER.balance - freelancerBefore, expectedNet, "freelancer net mismatch");
        assertEq(FEE_RECIPIENT.balance - feeBefore, expectedFee, "platform fee mismatch");
        assertEq(expectedNet + expectedFee, milestoneAmount, "fee + net must equal milestone");
    }

    /// @dev Verifies fee accounting for ERC-20 path
    function testFuzz_completeMilestone_feeAccountingERC20(uint96 milestoneAmount) public {
        vm.assume(milestoneAmount > 0);

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = milestoneAmount;

        GigEscrow e = new GigEscrow(CLIENT, FREELANCER, address(token), amounts, FEE_BPS, FEE_RECIPIENT, ARBITRATOR);

        token.mint(CLIENT, milestoneAmount);
        vm.prank(CLIENT);
        token.approve(address(e), milestoneAmount);
        vm.prank(CLIENT);
        e.deposit();

        uint256 freelancerBefore = token.balanceOf(FREELANCER);
        uint256 feeBefore = token.balanceOf(FEE_RECIPIENT);

        vm.prank(CLIENT);
        e.completeMilestone(0);

        uint256 expectedFee = (uint256(milestoneAmount) * FEE_BPS) / 10_000;
        uint256 expectedNet = milestoneAmount - expectedFee;

        assertEq(token.balanceOf(FREELANCER) - freelancerBefore, expectedNet, "freelancer net mismatch");
        assertEq(token.balanceOf(FEE_RECIPIENT) - feeBefore, expectedFee, "platform fee mismatch");
    }

    /// @dev Fuzz: split amounts always partition the milestone correctly
    function testFuzz_resolveDispute_splitPartitions(uint96 milestoneAmount, uint96 freelancerSplit) public {
        vm.assume(milestoneAmount > 0);
        vm.assume(freelancerSplit <= milestoneAmount);

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = milestoneAmount;

        GigEscrow e = new GigEscrow(CLIENT, FREELANCER, address(0), amounts, FEE_BPS, FEE_RECIPIENT, ARBITRATOR);

        vm.deal(CLIENT, milestoneAmount);
        vm.prank(CLIENT);
        e.deposit{value: milestoneAmount}();

        vm.prank(CLIENT);
        e.raiseDispute(0);

        uint256 freelancerBefore = FREELANCER.balance;
        uint256 clientBefore = CLIENT.balance;

        vm.prank(ARBITRATOR);
        e.resolveDispute(0, IGigEscrow.DisputeResolution.SPLIT, freelancerSplit);

        uint256 clientSplit = milestoneAmount - freelancerSplit;
        assertEq(FREELANCER.balance - freelancerBefore, freelancerSplit);
        assertEq(CLIENT.balance - clientBefore, clientSplit);
        // All funds accounted for
        assertEq(
            (FREELANCER.balance - freelancerBefore) + (CLIENT.balance - clientBefore),
            milestoneAmount
        );
    }

    /// @dev Fuzz: total released across all milestones never exceeds total deposited
    function testFuzz_totalReleasedNeverExceedsDeposit(uint96 a, uint96 b) public {
        vm.assume(a > 0 && b > 0);

        uint256[] memory amounts = new uint256[](2);
        amounts[0] = a;
        amounts[1] = b;
        uint256 total = uint256(a) + b;

        GigEscrow e = new GigEscrow(CLIENT, FREELANCER, address(0), amounts, FEE_BPS, FEE_RECIPIENT, ARBITRATOR);

        vm.deal(CLIENT, total);
        vm.prank(CLIENT);
        e.deposit{value: total}();

        vm.prank(CLIENT);
        e.completeMilestone(0);
        vm.prank(CLIENT);
        e.completeMilestone(1);

        // All funds should be distributed (no balance left)
        assertEq(address(e).balance, 0, "escrow should be empty after all milestones");
    }

    // ─── emergencyWithdraw — access control ──────────────────────────────────────

    function test_emergencyWithdraw_revertsForStranger() public {
        _fundETH(escrow);
        vm.prank(CLIENT);
        escrow.signEmergencyWithdrawal();
        vm.prank(FREELANCER);
        escrow.signEmergencyWithdrawal();

        vm.prank(STRANGER);
        vm.expectRevert(GigEscrow.OnlyClientOrFreelancer.selector);
        escrow.emergencyWithdraw();
    }

    function test_emergencyWithdraw_resetsSignedFlags() public {
        _fundETH(escrow);
        vm.prank(CLIENT);
        escrow.signEmergencyWithdrawal();
        vm.prank(FREELANCER);
        escrow.signEmergencyWithdrawal();

        vm.prank(CLIENT);
        escrow.emergencyWithdraw();

        // Flags must be reset after execution
        assertFalse(escrow.clientSignedEmergency());
        assertFalse(escrow.freelancerSignedEmergency());
    }

    // ─── M4: Partial-balance emergency withdrawal ─────────────────────────────────

    /// @dev Fund escrow → complete milestone 0 → emergency withdraw → assert only
    ///      remaining balance (milestone 1 funds) is returned to client
    function test_emergencyWithdraw_partialBalance() public {
        // Both milestones: 1 ether + 2 ether = 3 ether total
        _fundETH(escrow);

        // Complete milestone 0 (releases 1 ether minus fee)
        vm.prank(CLIENT);
        escrow.completeMilestone(0);

        // Remaining balance = 2 ether (milestone 1 untouched)
        uint256 remaining = escrow.getBalance();
        assertEq(remaining, 2 ether);

        uint256 clientBefore = CLIENT.balance;

        vm.prank(CLIENT);
        escrow.signEmergencyWithdrawal();
        vm.prank(FREELANCER);
        escrow.signEmergencyWithdrawal();

        vm.prank(CLIENT);
        escrow.emergencyWithdraw();

        // Client receives exactly the remaining balance, not the original total
        assertEq(CLIENT.balance - clientBefore, 2 ether);
        assertEq(address(escrow).balance, 0);
    }

    // ─── m3: completeMilestone reverts on DISPUTED / RESOLVED state ───────────────

    function test_completeMilestone_revertsOnDisputedMilestone() public {
        _fundETH(escrow);

        // Raise dispute on milestone 0
        vm.prank(CLIENT);
        escrow.raiseDispute(0);

        // completeMilestone should revert because status is DISPUTED not PENDING
        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.MilestoneNotPending.selector);
        escrow.completeMilestone(0);
    }

    function test_completeMilestone_revertsOnResolvedMilestone() public {
        _fundETH(escrow);

        // Dispute then resolve milestone 0
        vm.prank(CLIENT);
        escrow.raiseDispute(0);
        vm.prank(ARBITRATOR);
        escrow.resolveDispute(0, IGigEscrow.DisputeResolution.REFUND_CLIENT, 0);

        // completeMilestone should revert because status is RESOLVED not PENDING
        vm.prank(CLIENT);
        vm.expectRevert(GigEscrow.MilestoneNotPending.selector);
        escrow.completeMilestone(0);
    }

    // ─── m5: client != freelancer in constructor ──────────────────────────────────

    function test_constructor_revertsClientEqualsFreelancer() public {
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = 1 ether;
        vm.expectRevert("GigEscrow: client and freelancer cannot be the same address");
        new GigEscrow(CLIENT, CLIENT, address(0), amounts, FEE_BPS, FEE_RECIPIENT, ARBITRATOR);
    }
}
