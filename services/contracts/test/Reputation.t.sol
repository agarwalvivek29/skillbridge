// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {Reputation} from "../src/Reputation.sol";
import {IReputation} from "../src/interfaces/IReputation.sol";

contract ReputationTest is Test {
    // ─── Actors ───────────────────────────────────────────────────────────────────

    address constant FREELANCER_A = address(0xF12EE1);
    address constant FREELANCER_B = address(0xF12EE2);
    address constant STRANGER = address(0x5773);

    Reputation internal rep;

    function setUp() public {
        rep = new Reputation();
    }

    // ─── Constructor ─────────────────────────────────────────────────────────────

    function test_constructor_setsOwner() public view {
        assertEq(rep.owner(), address(this));
    }

    function test_initialValues_areZero() public view {
        assertEq(rep.gigsCompleted(FREELANCER_A), 0);
        assertEq(rep.totalEarned(FREELANCER_A), 0);
        assertEq(rep.averageAiScore(FREELANCER_A), 0);
    }

    // ─── recordCompletion() ──────────────────────────────────────────────────────

    function test_recordCompletion_updatesStats() public {
        rep.recordCompletion(FREELANCER_A, 1 ether, 85);

        assertEq(rep.gigsCompleted(FREELANCER_A), 1);
        assertEq(rep.totalEarned(FREELANCER_A), 1 ether);
        assertEq(rep.averageAiScore(FREELANCER_A), 85);
    }

    function test_recordCompletion_multipleUpdates() public {
        rep.recordCompletion(FREELANCER_A, 1 ether, 80);
        rep.recordCompletion(FREELANCER_A, 2 ether, 90);

        assertEq(rep.gigsCompleted(FREELANCER_A), 2);
        assertEq(rep.totalEarned(FREELANCER_A), 3 ether);
        // average = (80 + 90) / 2 = 85
        assertEq(rep.averageAiScore(FREELANCER_A), 85);
    }

    function test_recordCompletion_independentFreelancers() public {
        rep.recordCompletion(FREELANCER_A, 1 ether, 80);
        rep.recordCompletion(FREELANCER_B, 5 ether, 95);

        assertEq(rep.gigsCompleted(FREELANCER_A), 1);
        assertEq(rep.totalEarned(FREELANCER_A), 1 ether);
        assertEq(rep.gigsCompleted(FREELANCER_B), 1);
        assertEq(rep.totalEarned(FREELANCER_B), 5 ether);
        assertEq(rep.averageAiScore(FREELANCER_B), 95);
    }

    function test_recordCompletion_emitsEvent() public {
        vm.expectEmit(true, false, false, true);
        emit IReputation.ReputationUpdated(FREELANCER_A, 1, 1 ether, 85);

        rep.recordCompletion(FREELANCER_A, 1 ether, 85);
    }

    function test_recordCompletion_revertsForStranger() public {
        vm.prank(STRANGER);
        vm.expectRevert(Reputation.OnlyOwner.selector);
        rep.recordCompletion(FREELANCER_A, 1 ether, 85);
    }

    function test_recordCompletion_revertsForZeroAddress() public {
        vm.expectRevert(Reputation.ZeroAddress.selector);
        rep.recordCompletion(address(0), 1 ether, 85);
    }

    function test_recordCompletion_revertsForInvalidAiScore() public {
        vm.expectRevert(Reputation.InvalidAiScore.selector);
        rep.recordCompletion(FREELANCER_A, 1 ether, 101);
    }

    function test_recordCompletion_zeroEarnedAllowed() public {
        rep.recordCompletion(FREELANCER_A, 0, 75);
        assertEq(rep.gigsCompleted(FREELANCER_A), 1);
        assertEq(rep.totalEarned(FREELANCER_A), 0);
        assertEq(rep.averageAiScore(FREELANCER_A), 75);
    }

    function test_recordCompletion_zeroAiScoreAllowed() public {
        rep.recordCompletion(FREELANCER_A, 1 ether, 0);
        assertEq(rep.averageAiScore(FREELANCER_A), 0);
    }

    function test_recordCompletion_boundaryAiScore100() public {
        rep.recordCompletion(FREELANCER_A, 1 ether, 100);
        assertEq(rep.averageAiScore(FREELANCER_A), 100);
    }

    // ─── Ownership ───────────────────────────────────────────────────────────────

    function test_proposeOwner_setPendingOwner() public {
        rep.proposeOwner(STRANGER);
        assertEq(rep.pendingOwner(), STRANGER);
    }

    function test_proposeOwner_revertsForNonOwner() public {
        vm.prank(STRANGER);
        vm.expectRevert(Reputation.OnlyOwner.selector);
        rep.proposeOwner(STRANGER);
    }

    function test_proposeOwner_revertsForZeroAddress() public {
        vm.expectRevert(Reputation.ZeroAddress.selector);
        rep.proposeOwner(address(0));
    }

    function test_acceptOwnership_transfersOwnership() public {
        rep.proposeOwner(STRANGER);

        vm.prank(STRANGER);
        rep.acceptOwnership();

        assertEq(rep.owner(), STRANGER);
        assertEq(rep.pendingOwner(), address(0));
    }

    function test_acceptOwnership_revertsForNonPending() public {
        rep.proposeOwner(STRANGER);

        vm.prank(FREELANCER_A);
        vm.expectRevert(Reputation.OnlyPendingOwner.selector);
        rep.acceptOwnership();
    }

    // ─── aiScoreSum view ─────────────────────────────────────────────────────────

    function test_aiScoreSum_returnsRawSum() public {
        rep.recordCompletion(FREELANCER_A, 1 ether, 80);
        rep.recordCompletion(FREELANCER_A, 2 ether, 90);
        assertEq(rep.aiScoreSum(FREELANCER_A), 170);
    }

    // ─── Fuzz Tests ──────────────────────────────────────────────────────────────

    /// @dev Fuzz: average AI score is always between 0 and 100
    function testFuzz_averageAiScoreInRange(uint8 score1, uint8 score2) public {
        vm.assume(score1 <= 100);
        vm.assume(score2 <= 100);

        rep.recordCompletion(FREELANCER_A, 1 ether, score1);
        rep.recordCompletion(FREELANCER_A, 1 ether, score2);

        uint256 avg = rep.averageAiScore(FREELANCER_A);
        assertLe(avg, 100, "average must be <= 100");
    }

    /// @dev Fuzz: totalEarned accumulates correctly
    function testFuzz_totalEarnedAccumulates(uint96 earned1, uint96 earned2) public {
        rep.recordCompletion(FREELANCER_A, earned1, 50);
        rep.recordCompletion(FREELANCER_A, earned2, 50);

        assertEq(
            rep.totalEarned(FREELANCER_A),
            uint256(earned1) + uint256(earned2),
            "totalEarned must be sum of all earned amounts"
        );
    }

    /// @dev Fuzz: gigsCompleted increments by 1 each time
    function testFuzz_gigsCompletedIncrements(uint8 count) public {
        vm.assume(count > 0 && count <= 50);
        for (uint8 i = 0; i < count; i++) {
            rep.recordCompletion(FREELANCER_A, 1 ether, 50);
        }
        assertEq(rep.gigsCompleted(FREELANCER_A), count);
    }
}
