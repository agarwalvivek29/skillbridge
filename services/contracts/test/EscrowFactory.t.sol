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
    address constant NEW_OWNER = address(0xBEEF);

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

        vm.prank(OWNER);
        address escrowAddr = factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);

        assertTrue(escrowAddr != address(0), "escrow not deployed");
    }

    function test_createEscrow_escrowHasCorrectParams() public {
        vm.prank(OWNER);
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
        vm.prank(OWNER);
        factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);
        vm.prank(OWNER);
        factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);

        address[] memory all = factory.getAllEscrows();
        assertEq(all.length, 2);
    }

    function test_createEscrow_revertsForNonOwner() public {
        vm.prank(STRANGER);
        vm.expectRevert(EscrowFactory.OnlyOwner.selector);
        factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);
    }

    function test_createEscrow_revertsZeroClient() public {
        vm.prank(OWNER);
        vm.expectRevert(EscrowFactory.ZeroAddress.selector);
        factory.createEscrow(address(0), FREELANCER, address(0), twoMilestones, FEE_BPS);
    }

    function test_createEscrow_revertsZeroFreelancer() public {
        vm.prank(OWNER);
        vm.expectRevert(EscrowFactory.ZeroAddress.selector);
        factory.createEscrow(CLIENT, address(0), address(0), twoMilestones, FEE_BPS);
    }

    function test_createEscrow_revertsEmptyMilestones() public {
        uint256[] memory empty;
        vm.prank(OWNER);
        vm.expectRevert(EscrowFactory.InvalidMilestones.selector);
        factory.createEscrow(CLIENT, FREELANCER, address(0), empty, FEE_BPS);
    }

    function test_createEscrow_revertsClientEqualsFreelancer() public {
        vm.prank(OWNER);
        vm.expectRevert(EscrowFactory.ClientEqualsFreelancer.selector);
        factory.createEscrow(CLIENT, CLIENT, address(0), twoMilestones, FEE_BPS);
    }

    function test_createEscrow_revertsOnZeroMilestoneAmount() public {
        uint256[] memory amounts = new uint256[](2);
        amounts[0] = 1 ether;
        amounts[1] = 0;
        vm.prank(OWNER);
        vm.expectRevert(EscrowFactory.ZeroMilestoneAmount.selector);
        factory.createEscrow(CLIENT, FREELANCER, address(0), amounts, FEE_BPS);
    }

    function test_createEscrow_revertsOnFeeTooHigh() public {
        vm.prank(OWNER);
        vm.expectRevert(EscrowFactory.FeeTooHigh.selector);
        factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, 1001);
    }

    // ─── Paginated Access ─────────────────────────────────────────────────────────

    function test_getEscrowCount_returnsCorrectCount() public {
        assertEq(factory.getEscrowCount(), 0);
        vm.prank(OWNER);
        factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);
        assertEq(factory.getEscrowCount(), 1);
        vm.prank(OWNER);
        factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);
        assertEq(factory.getEscrowCount(), 2);
    }

    function test_getEscrow_returnsCorrectAddress() public {
        vm.prank(OWNER);
        address escrowAddr = factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);
        assertEq(factory.getEscrow(0), escrowAddr);
    }

    function test_getEscrow_revertsOutOfBounds() public {
        vm.expectRevert("EscrowFactory: index out of bounds");
        factory.getEscrow(0);
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

    // ─── Two-step Ownership Transfer ─────────────────────────────────────────────

    function test_proposeOwner_success() public {
        vm.prank(OWNER);
        factory.proposeOwner(NEW_OWNER);
        assertEq(factory.pendingOwner(), NEW_OWNER);
        assertEq(factory.owner(), OWNER); // still old owner until accepted
    }

    function test_proposeOwner_emitsEvent() public {
        vm.expectEmit(true, true, false, false);
        emit EscrowFactory.OwnershipTransferProposed(OWNER, NEW_OWNER);
        vm.prank(OWNER);
        factory.proposeOwner(NEW_OWNER);
    }

    function test_proposeOwner_revertsNonOwner() public {
        vm.prank(STRANGER);
        vm.expectRevert(EscrowFactory.OnlyOwner.selector);
        factory.proposeOwner(NEW_OWNER);
    }

    function test_proposeOwner_revertsZeroAddress() public {
        vm.prank(OWNER);
        vm.expectRevert(EscrowFactory.ZeroAddress.selector);
        factory.proposeOwner(address(0));
    }

    function test_acceptOwnership_success() public {
        vm.prank(OWNER);
        factory.proposeOwner(NEW_OWNER);

        vm.expectEmit(true, true, false, false);
        emit EscrowFactory.OwnershipTransferred(OWNER, NEW_OWNER);

        vm.prank(NEW_OWNER);
        factory.acceptOwnership();

        assertEq(factory.owner(), NEW_OWNER);
        assertEq(factory.pendingOwner(), address(0));
    }

    function test_acceptOwnership_revertsIfNotPendingOwner() public {
        vm.prank(OWNER);
        factory.proposeOwner(NEW_OWNER);

        vm.prank(STRANGER);
        vm.expectRevert(EscrowFactory.OnlyPendingOwner.selector);
        factory.acceptOwnership();
    }

    function test_acceptOwnership_revertsIfNoPendingTransfer() public {
        vm.prank(OWNER);
        vm.expectRevert(EscrowFactory.OnlyPendingOwner.selector);
        factory.acceptOwnership();
    }

    // ─── Fuzz: multiple escrows get correct fee recipient ─────────────────────────

    function testFuzz_createEscrow_multipleDeploys(uint8 count) public {
        vm.assume(count > 0 && count <= 20);

        for (uint256 i; i < count; ++i) {
            vm.prank(OWNER);
            factory.createEscrow(CLIENT, FREELANCER, address(0), twoMilestones, FEE_BPS);
        }

        address[] memory all = factory.getAllEscrows();
        assertEq(all.length, count);
        assertEq(factory.getEscrowCount(), count);

        // All escrows should share the same fee recipient and arbitrator
        for (uint256 i; i < count; ++i) {
            GigEscrow e = GigEscrow(payable(all[i]));
            assertEq(e.platformFeeRecipient(), FEE_RECIPIENT);
            assertEq(e.arbitrator(), OWNER);
        }
    }
}
