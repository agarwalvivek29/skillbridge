// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {EscrowFactory} from "../src/EscrowFactory.sol";
import {GigEscrow} from "../src/GigEscrow.sol";
import {IEscrowFactory} from "../src/interfaces/IEscrowFactory.sol";

contract EscrowFactoryTest is Test {
    // ─── Actors ───────────────────────────────────────────────────────────────────

    address constant OWNER = address(0xA551);
    address constant FEE_RECIPIENT = address(0xFEE1);
    address constant CLIENT = address(0xC11E01);
    address constant FREELANCER = address(0xF12EE);
    address constant STRANGER = address(0x5773);
    address constant NEW_FEE_RECIPIENT = address(0xFEE2);

    uint256 constant FEE_BPS = 500;

    // ─── Fixtures ─────────────────────────────────────────────────────────────────

    EscrowFactory internal factory;
    uint256[] internal twoMilestones;

    function setUp() public {
        vm.prank(OWNER);
        factory = new EscrowFactory(FEE_RECIPIENT);

        twoMilestones = new uint256[](2);
        twoMilestones[0] = 1 ether;
        twoMilestones[1] = 2 ether;
    }

    // ─── Constructor ─────────────────────────────────────────────────────────────

    function test_constructor_setsOwnerAndFeeRecipient() public view {
        assertEq(factory.owner(), OWNER);
        assertEq(factory.feeRecipient(), FEE_RECIPIENT);
    }

    function test_constructor_revertsOnZeroFeeRecipient() public {
        vm.expectRevert("EscrowFactory: invalid fee recipient");
        new EscrowFactory(address(0));
    }

    // ─── createEscrow ─────────────────────────────────────────────────────────────

    function test_createEscrow_deploysGigEscrow() public {
        vm.expectEmit(false, true, true, false);
        emit IEscrowFactory.EscrowCreated(address(0), CLIENT, FREELANCER, address(0), 3 ether);

        address escrowAddr = factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);

        assertTrue(escrowAddr != address(0), "escrow not deployed");
    }

    function test_createEscrow_escrowHasCorrectParams() public {
        address escrowAddr = factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);
        GigEscrow escrow = GigEscrow(payable(escrowAddr));

        assertEq(escrow.client(), CLIENT);
        assertEq(escrow.freelancer(), FREELANCER);
        assertEq(escrow.tokenAddress(), address(0));
        assertEq(escrow.platformFeeBasisPoints(), FEE_BPS);
        assertEq(escrow.platformFeeRecipient(), FEE_RECIPIENT);
        assertEq(escrow.arbitrator(), OWNER); // factory owner is arbitrator
        assertEq(escrow.totalAmount(), 3 ether);
        assertEq(escrow.milestoneCount(), 2);
    }

    function test_createEscrow_tracksAllEscrows() public {
        factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);
        factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);

        address[] memory all = factory.getAllEscrows();
        assertEq(all.length, 2);
    }

    function test_createEscrow_revertsZeroClient() public {
        vm.expectRevert(EscrowFactory.InvalidClient.selector);
        factory.createEscrow(address(0), FREELANCER, address(0), twoMilestones, FEE_BPS);
    }

    function test_createEscrow_revertsZeroFreelancer() public {
        vm.expectRevert(EscrowFactory.InvalidFreelancer.selector);
        factory.createEscrow(CLIENT, address(0), address(0), twoMilestones, FEE_BPS);
    }

    // ─── setFeeRecipient ─────────────────────────────────────────────────────────

    function test_setFeeRecipient_ownerCanUpdate() public {
        vm.expectEmit(true, true, false, false);
        emit IEscrowFactory.FeeRecipientUpdated(FEE_RECIPIENT, NEW_FEE_RECIPIENT);

        vm.prank(OWNER);
        factory.setFeeRecipient(NEW_FEE_RECIPIENT);

        assertEq(factory.feeRecipient(), NEW_FEE_RECIPIENT);
    }

    function test_setFeeRecipient_revertsNonOwner() public {
        vm.prank(STRANGER);
        vm.expectRevert(EscrowFactory.OnlyOwner.selector);
        factory.setFeeRecipient(NEW_FEE_RECIPIENT);
    }

    function test_setFeeRecipient_revertsZeroAddress() public {
        vm.prank(OWNER);
        vm.expectRevert(EscrowFactory.InvalidFeeRecipient.selector);
        factory.setFeeRecipient(address(0));
    }

    // ─── transferOwnership ───────────────────────────────────────────────────────

    function test_transferOwnership_success() public {
        vm.prank(OWNER);
        factory.transferOwnership(STRANGER);
        assertEq(factory.owner(), STRANGER);
    }

    function test_transferOwnership_revertsNonOwner() public {
        vm.prank(STRANGER);
        vm.expectRevert(EscrowFactory.OnlyOwner.selector);
        factory.transferOwnership(STRANGER);
    }

    // ─── Fuzz: multiple escrows get correct fee recipient ─────────────────────────

    function testFuzz_createEscrow_multipleDeploys(uint8 count) public {
        vm.assume(count > 0 && count <= 20);

        for (uint256 i; i < count; ++i) {
            factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);
        }

        address[] memory all = factory.getAllEscrows();
        assertEq(all.length, count);

        // All escrows should share the same fee recipient and arbitrator
        for (uint256 i; i < count; ++i) {
            GigEscrow e = GigEscrow(payable(all[i]));
            assertEq(e.platformFeeRecipient(), FEE_RECIPIENT);
            assertEq(e.arbitrator(), OWNER);
        }
    }
}
