// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/EscrowFactory.sol";
import "../src/GigEscrow.sol";
import "../src/interfaces/IGigEscrow.sol";

contract EscrowFactoryTest is Test {
    EscrowFactory public factory;

    address public factoryOwner = address(0xF);
    address public client = address(0x1);
    address public freelancer = address(0x2);
    address public arbitrator = address(0x3);

    uint256[] public amounts;

    function setUp() public {
        vm.prank(factoryOwner);
        factory = new EscrowFactory();

        amounts.push(1 ether);
        amounts.push(2 ether);
    }

    // ─── Constructor ─────────────────────────────────────────────────────────

    function test_owner_isDeployer() public view {
        assertEq(factory.owner(), factoryOwner);
    }

    // ─── createEscrow ─────────────────────────────────────────────────────────

    function test_createEscrow_deploysContract() public {
        address escrowAddr = factory.createEscrow(client, freelancer, arbitrator, amounts);
        assertTrue(escrowAddr != address(0));
        assertTrue(escrowAddr.code.length > 0);
    }

    function test_createEscrow_emitsEscrowCreated() public {
        vm.expectEmit(false, true, true, true);
        emit IEscrowFactory.EscrowCreated(address(0), client, freelancer, 3 ether);
        factory.createEscrow(client, freelancer, arbitrator, amounts);
    }

    function test_createEscrow_escrowHasCorrectParties() public {
        address escrowAddr = factory.createEscrow(client, freelancer, arbitrator, amounts);
        GigEscrow escrow = GigEscrow(payable(escrowAddr));

        assertEq(escrow.client(), client);
        assertEq(escrow.freelancer(), freelancer);
        assertEq(escrow.arbitrator(), arbitrator);
    }

    function test_createEscrow_escrowHasCorrectMilestones() public {
        address escrowAddr = factory.createEscrow(client, freelancer, arbitrator, amounts);
        GigEscrow escrow = GigEscrow(payable(escrowAddr));

        assertEq(escrow.milestoneCount(), 2);
        (, uint256 a0) = escrow.getMilestone(0);
        (, uint256 a1) = escrow.getMilestone(1);
        assertEq(a0, 1 ether);
        assertEq(a1, 2 ether);
    }

    function test_createEscrow_differentCallsDeployDifferentContracts() public {
        address e1 = factory.createEscrow(client, freelancer, arbitrator, amounts);
        address e2 = factory.createEscrow(client, freelancer, arbitrator, amounts);
        assertTrue(e1 != e2);
    }

    function test_createEscrow_reverts_zeroClientAddress() public {
        vm.expectRevert("EscrowFactory: zero client address");
        factory.createEscrow(address(0), freelancer, arbitrator, amounts);
    }

    function test_createEscrow_reverts_zeroFreelancerAddress() public {
        vm.expectRevert("EscrowFactory: zero freelancer address");
        factory.createEscrow(client, address(0), arbitrator, amounts);
    }

    function test_createEscrow_reverts_zeroArbitratorAddress() public {
        vm.expectRevert("EscrowFactory: zero arbitrator address");
        factory.createEscrow(client, freelancer, address(0), amounts);
    }

    function test_createEscrow_reverts_noMilestones() public {
        uint256[] memory empty;
        vm.expectRevert("EscrowFactory: no milestones");
        factory.createEscrow(client, freelancer, arbitrator, empty);
    }

    function test_createEscrow_reverts_zeroMilestoneAmount() public {
        uint256[] memory bad = new uint256[](2);
        bad[0] = 0;
        bad[1] = 1 ether;
        vm.expectRevert("EscrowFactory: milestone amount must be > 0");
        factory.createEscrow(client, freelancer, arbitrator, bad);
    }

    // ─── Fuzz: createEscrow ───────────────────────────────────────────────────

    function testFuzz_createEscrow_anyValidAddresses(
        address fuzzClient,
        address fuzzFreelancer,
        address fuzzArbitrator,
        uint256 amount0,
        uint256 amount1
    ) public {
        vm.assume(fuzzClient != address(0));
        vm.assume(fuzzFreelancer != address(0));
        vm.assume(fuzzArbitrator != address(0));
        vm.assume(fuzzClient != fuzzFreelancer);
        vm.assume(amount0 > 0 && amount0 <= 1_000_000 ether);
        vm.assume(amount1 > 0 && amount1 <= 1_000_000 ether);

        uint256[] memory fuzzAmounts = new uint256[](2);
        fuzzAmounts[0] = amount0;
        fuzzAmounts[1] = amount1;

        address escrowAddr = factory.createEscrow(fuzzClient, fuzzFreelancer, fuzzArbitrator, fuzzAmounts);
        assertTrue(escrowAddr != address(0));
        assertTrue(escrowAddr.code.length > 0);
    }

    function testFuzz_createEscrow_totalAmountMatchesSum(uint96 seed) public {
        uint256 count = (uint256(seed) % 4) + 1;
        uint256[] memory fuzzAmounts = new uint256[](count);
        uint256 expectedTotal;
        for (uint256 i; i < count; ++i) {
            fuzzAmounts[i] = ((uint256(seed) >> (i * 4)) % 3 ether) + 0.001 ether;
            expectedTotal += fuzzAmounts[i];
        }

        address escrowAddr = factory.createEscrow(client, freelancer, arbitrator, fuzzAmounts);
        GigEscrow escrow = GigEscrow(payable(escrowAddr));

        assertEq(escrow.totalAmount(), expectedTotal);
    }

    function testFuzz_createEscrow_manyEscrows(uint8 count) public {
        uint8 n = uint8(bound(count, 1, 20));
        address[] memory deployed = new address[](n);
        for (uint256 i; i < n; ++i) {
            deployed[i] = factory.createEscrow(
                address(uint160(i + 100)),
                address(uint160(i + 200)),
                arbitrator,
                amounts
            );
        }

        // All addresses unique
        for (uint256 i; i < n; ++i) {
            for (uint256 j = i + 1; j < n; ++j) {
                assertTrue(deployed[i] != deployed[j]);
            }
        }
    }
}
