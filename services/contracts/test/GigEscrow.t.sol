// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/GigEscrow.sol";
import "../src/interfaces/IGigEscrow.sol";

/// @notice Helper contract that rejects ETH (to test failed-transfer paths)
contract RejectingReceiver {
    receive() external payable {
        revert("rejecting ETH");
    }
}

/// @notice Malicious receiver to test reentrancy protection
contract MaliciousReceiver {
    GigEscrow public target;
    bool public attackTriggered;

    receive() external payable {
        if (!attackTriggered && address(target).balance > 0) {
            attackTriggered = true;
            // Attempt reentrant completeMilestone — should revert due to COMPLETED state
            try target.completeMilestone(0) {} catch {}
        }
    }

    function setTarget(GigEscrow _target) external {
        target = _target;
    }
}

contract GigEscrowTest is Test {
    GigEscrow public escrow;

    address public client = address(0x1);
    address public freelancer = address(0x2);
    address public arbitrator = address(0x3);
    address public stranger = address(0x4);

    uint256[] public amounts;
    uint256 public totalAmount;

    // ─── Setup ────────────────────────────────────────────────────────────────

    function setUp() public {
        amounts.push(1 ether);
        amounts.push(2 ether);
        amounts.push(3 ether);
        totalAmount = 6 ether;

        escrow = new GigEscrow(client, freelancer, arbitrator, amounts);

        // Fund test accounts
        vm.deal(client, 100 ether);
        vm.deal(freelancer, 100 ether);
        vm.deal(arbitrator, 10 ether);
        vm.deal(stranger, 10 ether);
    }

    // ─── Constructor ─────────────────────────────────────────────────────────

    function test_constructor_storesAddresses() public view {
        assertEq(escrow.client(), client);
        assertEq(escrow.freelancer(), freelancer);
        assertEq(escrow.arbitrator(), arbitrator);
    }

    function test_constructor_storesMilestones() public view {
        assertEq(escrow.milestoneCount(), 3);
        (IGigEscrow.MilestoneStatus s0, uint256 a0) = escrow.getMilestone(0);
        assertEq(a0, 1 ether);
        assertEq(uint8(s0), uint8(IGigEscrow.MilestoneStatus.PENDING));
    }

    function test_constructor_reverts_zeroClientAddress() public {
        vm.expectRevert("GigEscrow: zero client address");
        new GigEscrow(address(0), freelancer, arbitrator, amounts);
    }

    function test_constructor_reverts_zeroFreelancerAddress() public {
        vm.expectRevert("GigEscrow: zero freelancer address");
        new GigEscrow(client, address(0), arbitrator, amounts);
    }

    function test_constructor_reverts_zeroArbitratorAddress() public {
        vm.expectRevert("GigEscrow: zero arbitrator address");
        new GigEscrow(client, freelancer, address(0), amounts);
    }

    function test_constructor_reverts_clientEqualsFreelancer() public {
        vm.expectRevert("GigEscrow: client equals freelancer");
        new GigEscrow(client, client, arbitrator, amounts);
    }

    function test_constructor_reverts_emptyAmounts() public {
        uint256[] memory empty;
        vm.expectRevert("GigEscrow: no milestones");
        new GigEscrow(client, freelancer, arbitrator, empty);
    }

    function test_constructor_reverts_zeroMilestoneAmount() public {
        uint256[] memory bad = new uint256[](2);
        bad[0] = 0;
        bad[1] = 1 ether;
        vm.expectRevert("GigEscrow: milestone amount must be > 0");
        new GigEscrow(client, freelancer, arbitrator, bad);
    }

    // ─── Deposit ──────────────────────────────────────────────────────────────

    function test_deposit_success() public {
        vm.prank(client);
        escrow.deposit{value: totalAmount}();

        assertTrue(escrow.funded());
        assertEq(escrow.getBalance(), totalAmount);
    }

    function test_deposit_emitsEscrowFunded() public {
        vm.expectEmit(true, false, false, true);
        emit IGigEscrow.EscrowFunded(address(escrow), totalAmount);

        vm.prank(client);
        escrow.deposit{value: totalAmount}();
    }

    function test_deposit_reverts_notClient() public {
        vm.prank(stranger);
        vm.expectRevert("GigEscrow: caller is not client");
        escrow.deposit{value: totalAmount}();
    }

    function test_deposit_reverts_alreadyFunded() public {
        vm.prank(client);
        escrow.deposit{value: totalAmount}();

        vm.prank(client);
        vm.expectRevert("GigEscrow: already funded");
        escrow.deposit{value: totalAmount}();
    }

    function test_deposit_reverts_incorrectAmount() public {
        vm.prank(client);
        vm.expectRevert("GigEscrow: incorrect deposit amount");
        escrow.deposit{value: totalAmount - 1}();
    }

    function test_deposit_reverts_overpay() public {
        vm.prank(client);
        vm.expectRevert("GigEscrow: incorrect deposit amount");
        escrow.deposit{value: totalAmount + 1}();
    }

    function test_receive_reverts_directTransfer() public {
        // Low-level call to receive() returns false (caught by the call itself, not propagated)
        vm.prank(client);
        (bool s,) = address(escrow).call{value: 1 ether}("");
        assertFalse(s);
    }

    // ─── Complete milestone ───────────────────────────────────────────────────

    function _fundEscrow() internal {
        vm.prank(client);
        escrow.deposit{value: totalAmount}();
    }

    function test_completeMilestone_byClient() public {
        _fundEscrow();
        uint256 balanceBefore = freelancer.balance;

        vm.prank(client);
        escrow.completeMilestone(0);

        (IGigEscrow.MilestoneStatus s,) = escrow.getMilestone(0);
        assertEq(uint8(s), uint8(IGigEscrow.MilestoneStatus.COMPLETED));
        assertEq(freelancer.balance, balanceBefore + 1 ether);
    }

    function test_completeMilestone_byArbitrator() public {
        _fundEscrow();
        vm.prank(arbitrator);
        escrow.completeMilestone(1);

        (IGigEscrow.MilestoneStatus s,) = escrow.getMilestone(1);
        assertEq(uint8(s), uint8(IGigEscrow.MilestoneStatus.COMPLETED));
    }

    function test_completeMilestone_emitsEvent() public {
        _fundEscrow();
        vm.expectEmit(true, true, false, true);
        emit IGigEscrow.MilestoneCompleted(0, freelancer, 1 ether);

        vm.prank(client);
        escrow.completeMilestone(0);
    }

    function test_completeMilestone_reverts_notFunded() public {
        vm.prank(client);
        vm.expectRevert("GigEscrow: not funded");
        escrow.completeMilestone(0);
    }

    function test_completeMilestone_reverts_invalidIndex() public {
        _fundEscrow();
        vm.prank(client);
        vm.expectRevert("GigEscrow: invalid milestone index");
        escrow.completeMilestone(99);
    }

    function test_completeMilestone_reverts_unauthorized() public {
        _fundEscrow();
        vm.prank(stranger);
        vm.expectRevert("GigEscrow: unauthorized");
        escrow.completeMilestone(0);
    }

    function test_completeMilestone_reverts_alreadyCompleted() public {
        _fundEscrow();
        vm.prank(client);
        escrow.completeMilestone(0);

        vm.prank(client);
        vm.expectRevert("GigEscrow: milestone not in PENDING state");
        escrow.completeMilestone(0);
    }

    // ─── Raise dispute ────────────────────────────────────────────────────────

    function test_raiseDispute_byClient() public {
        _fundEscrow();
        vm.prank(client);
        escrow.raiseDispute(1);

        (IGigEscrow.MilestoneStatus s,) = escrow.getMilestone(1);
        assertEq(uint8(s), uint8(IGigEscrow.MilestoneStatus.DISPUTED));
    }

    function test_raiseDispute_byFreelancer() public {
        _fundEscrow();
        vm.prank(freelancer);
        escrow.raiseDispute(1);

        (IGigEscrow.MilestoneStatus s,) = escrow.getMilestone(1);
        assertEq(uint8(s), uint8(IGigEscrow.MilestoneStatus.DISPUTED));
    }

    function test_raiseDispute_emitsEvent() public {
        _fundEscrow();
        vm.expectEmit(true, true, false, false);
        emit IGigEscrow.DisputeRaised(2, client);

        vm.prank(client);
        escrow.raiseDispute(2);
    }

    function test_raiseDispute_reverts_notFunded() public {
        vm.prank(client);
        vm.expectRevert("GigEscrow: not funded");
        escrow.raiseDispute(0);
    }

    function test_raiseDispute_reverts_unauthorized() public {
        _fundEscrow();
        vm.prank(stranger);
        vm.expectRevert("GigEscrow: caller is not a party");
        escrow.raiseDispute(0);
    }

    function test_raiseDispute_reverts_alreadyCompleted() public {
        _fundEscrow();
        vm.prank(client);
        escrow.completeMilestone(0);

        vm.prank(client);
        vm.expectRevert("GigEscrow: milestone not in PENDING state");
        escrow.raiseDispute(0);
    }

    // ─── Resolve dispute ──────────────────────────────────────────────────────

    function _setupDispute(uint256 index) internal {
        _fundEscrow();
        vm.prank(client);
        escrow.raiseDispute(index);
    }

    function test_resolveDispute_payFreelancer() public {
        _setupDispute(0);
        uint256 balanceBefore = freelancer.balance;

        vm.prank(arbitrator);
        escrow.resolveDispute(0, true);

        (IGigEscrow.MilestoneStatus s,) = escrow.getMilestone(0);
        assertEq(uint8(s), uint8(IGigEscrow.MilestoneStatus.COMPLETED));
        assertEq(freelancer.balance, balanceBefore + 1 ether);
    }

    function test_resolveDispute_refundClient() public {
        _setupDispute(1);
        uint256 balanceBefore = client.balance;

        vm.prank(arbitrator);
        escrow.resolveDispute(1, false);

        (IGigEscrow.MilestoneStatus s,) = escrow.getMilestone(1);
        assertEq(uint8(s), uint8(IGigEscrow.MilestoneStatus.REFUNDED));
        assertEq(client.balance, balanceBefore + 2 ether);
    }

    function test_resolveDispute_emitsEvent() public {
        _setupDispute(2);
        vm.expectEmit(true, false, false, true);
        emit IGigEscrow.DisputeResolved(2, true, 3 ether);

        vm.prank(arbitrator);
        escrow.resolveDispute(2, true);
    }

    function test_resolveDispute_reverts_notArbitrator() public {
        _setupDispute(0);
        vm.prank(client);
        vm.expectRevert("GigEscrow: caller is not arbitrator");
        escrow.resolveDispute(0, true);
    }

    function test_resolveDispute_reverts_notDisputed() public {
        _fundEscrow();
        vm.prank(arbitrator);
        vm.expectRevert("GigEscrow: milestone not in DISPUTED state");
        escrow.resolveDispute(0, true);
    }

    // ─── Emergency withdrawal ─────────────────────────────────────────────────

    function test_emergencyWithdraw_success() public {
        _fundEscrow();
        uint256 clientBalanceBefore = client.balance;

        vm.prank(client);
        escrow.approveEmergencyWithdraw();

        vm.prank(freelancer);
        escrow.approveEmergencyWithdraw();

        escrow.emergencyWithdraw();

        assertEq(escrow.getBalance(), 0);
        assertEq(client.balance, clientBalanceBefore + totalAmount);
    }

    function test_emergencyWithdraw_emitsApprovalEvent() public {
        vm.expectEmit(true, false, false, false);
        emit IGigEscrow.EmergencyWithdrawApproved(client);

        vm.prank(client);
        escrow.approveEmergencyWithdraw();
    }

    function test_emergencyWithdraw_emitsExecutedEvent() public {
        _fundEscrow();
        vm.prank(client);
        escrow.approveEmergencyWithdraw();
        vm.prank(freelancer);
        escrow.approveEmergencyWithdraw();

        vm.expectEmit(false, false, false, true);
        emit IGigEscrow.EmergencyWithdrawExecuted(totalAmount, 0);
        escrow.emergencyWithdraw();
    }

    function test_emergencyWithdraw_reverts_onlyOneApproval() public {
        _fundEscrow();
        vm.prank(client);
        escrow.approveEmergencyWithdraw();

        vm.expectRevert("GigEscrow: both parties must approve");
        escrow.emergencyWithdraw();
    }

    function test_emergencyWithdraw_reverts_noApprovals() public {
        _fundEscrow();
        vm.expectRevert("GigEscrow: both parties must approve");
        escrow.emergencyWithdraw();
    }

    function test_emergencyWithdraw_reverts_doubleExecute() public {
        _fundEscrow();
        vm.prank(client);
        escrow.approveEmergencyWithdraw();
        vm.prank(freelancer);
        escrow.approveEmergencyWithdraw();
        escrow.emergencyWithdraw();

        vm.expectRevert("GigEscrow: emergency withdrawal already executed");
        escrow.emergencyWithdraw();
    }

    function test_emergencyWithdraw_reverts_doubleApprove() public {
        vm.prank(client);
        escrow.approveEmergencyWithdraw();

        vm.prank(client);
        vm.expectRevert("GigEscrow: already approved");
        escrow.approveEmergencyWithdraw();
    }

    function test_emergencyWithdraw_blocksOtherFunctions() public {
        _fundEscrow();
        vm.prank(client);
        escrow.approveEmergencyWithdraw();
        vm.prank(freelancer);
        escrow.approveEmergencyWithdraw();
        escrow.emergencyWithdraw();

        vm.prank(client);
        vm.expectRevert("GigEscrow: emergency withdrawal already executed");
        escrow.completeMilestone(0);
    }

    // ─── Reentrancy protection ────────────────────────────────────────────────

    function test_completeMilestone_noReentrancy() public {
        MaliciousReceiver attacker = new MaliciousReceiver();
        vm.deal(address(attacker), 0);

        // Two milestones: after releasing milestone 0, escrow still holds milestone 1 funds.
        // This means address(target).balance > 0 when receive() fires, so the reentry IS attempted.
        uint256[] memory twoMilestones = new uint256[](2);
        twoMilestones[0] = 1 ether;
        twoMilestones[1] = 1 ether;

        GigEscrow attackTarget = new GigEscrow(client, address(attacker), arbitrator, twoMilestones);
        attacker.setTarget(attackTarget);

        vm.deal(client, 2 ether);
        vm.prank(client);
        attackTarget.deposit{value: 2 ether}();

        // completeMilestone(0) sends 1 ether to attacker; receive() fires and attempts
        // to call completeMilestone(0) again — should fail with "not in PENDING state".
        // The outer call still succeeds (CEI pattern: state was updated before the transfer).
        vm.prank(client);
        attackTarget.completeMilestone(0);

        // Confirm reentry was attempted (escrow still had balance, condition was true)
        assertTrue(attacker.attackTriggered(), "reentrancy was not attempted: test setup invalid");

        // Confirm only one payment went out: milestone 1 still in escrow
        assertEq(attackTarget.getBalance(), 1 ether);

        // Milestone 0 is COMPLETED (not double-paid)
        (IGigEscrow.MilestoneStatus s0,) = attackTarget.getMilestone(0);
        assertEq(uint8(s0), uint8(IGigEscrow.MilestoneStatus.COMPLETED));
    }

    // ─── Fuzz tests ───────────────────────────────────────────────────────────

    /// @dev Fuzz: any exact-match deposit should succeed; anything else should revert
    function testFuzz_deposit_exactAmount(uint96 seed) public {
        // Build amounts from seed
        uint256 a = (uint256(seed) % 10 ether) + 0.001 ether;
        uint256 b = (uint256(seed) % 5 ether) + 0.001 ether;

        uint256[] memory fuzzAmounts = new uint256[](2);
        fuzzAmounts[0] = a;
        fuzzAmounts[1] = b;
        uint256 total = a + b;

        GigEscrow fuzzEscrow = new GigEscrow(client, freelancer, arbitrator, fuzzAmounts);
        vm.deal(client, total + 1 ether);

        // Exact amount succeeds
        vm.prank(client);
        fuzzEscrow.deposit{value: total}();
        assertTrue(fuzzEscrow.funded());
    }

    function testFuzz_deposit_wrongAmount_reverts(uint96 seed) public {
        uint256 a = (uint256(seed) % 10 ether) + 0.001 ether;
        uint256[] memory fuzzAmounts = new uint256[](1);
        fuzzAmounts[0] = a;

        GigEscrow fuzzEscrow = new GigEscrow(client, freelancer, arbitrator, fuzzAmounts);
        vm.deal(client, a + 1 ether);

        // Off-by-one reverts
        vm.prank(client);
        vm.expectRevert("GigEscrow: incorrect deposit amount");
        fuzzEscrow.deposit{value: a + 1}();
    }

    function testFuzz_completeMilestone_invalidIndex_reverts(uint256 badIndex) public {
        _fundEscrow();
        uint256 count = escrow.milestoneCount();
        badIndex = bound(badIndex, count, type(uint256).max);

        vm.prank(client);
        vm.expectRevert("GigEscrow: invalid milestone index");
        escrow.completeMilestone(badIndex);
    }

    function testFuzz_resolveDispute_payOrRefund(uint256 milestoneIndex, bool payFreelancer) public {
        milestoneIndex = bound(milestoneIndex, 0, amounts.length - 1);
        _fundEscrow();

        vm.prank(client);
        escrow.raiseDispute(milestoneIndex);

        uint256 milestoneAmount = amounts[milestoneIndex];

        if (payFreelancer) {
            uint256 fBalanceBefore = freelancer.balance;
            vm.prank(arbitrator);
            escrow.resolveDispute(milestoneIndex, true);
            assertEq(freelancer.balance, fBalanceBefore + milestoneAmount);
        } else {
            uint256 cBalanceBefore = client.balance;
            vm.prank(arbitrator);
            escrow.resolveDispute(milestoneIndex, false);
            assertEq(client.balance, cBalanceBefore + milestoneAmount);
        }
    }

    function testFuzz_allMilestonesCompleted_balanceZero(uint256 seed) public {
        // Build between 1 and 5 milestones with random amounts
        uint256 count = (seed % 5) + 1;
        uint256[] memory fuzzAmounts = new uint256[](count);
        uint256 total;
        for (uint256 i; i < count; ++i) {
            fuzzAmounts[i] = ((seed >> (i * 8)) % 2 ether) + 0.01 ether;
            total += fuzzAmounts[i];
        }

        GigEscrow fuzzEscrow = new GigEscrow(client, freelancer, arbitrator, fuzzAmounts);
        vm.deal(client, total);

        vm.prank(client);
        fuzzEscrow.deposit{value: total}();

        for (uint256 i; i < count; ++i) {
            vm.prank(client);
            fuzzEscrow.completeMilestone(i);
        }

        assertEq(fuzzEscrow.getBalance(), 0);
    }
}
