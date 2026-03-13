import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { GigEscrow } from "../target/types/gig_escrow";
import {
  Keypair,
  LAMPORTS_PER_SOL,
  PublicKey,
  SystemProgram,
} from "@solana/web3.js";
import { expect } from "chai";

describe("gig_escrow", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.GigEscrow as Program<GigEscrow>;

  // Test wallets
  const client = Keypair.generate();
  const freelancer = Keypair.generate();
  const arbitrator = Keypair.generate();
  const feeRecipient = Keypair.generate();

  const gigId = "gig-001";
  const milestoneAmounts = [
    new anchor.BN(1 * LAMPORTS_PER_SOL),
    new anchor.BN(2 * LAMPORTS_PER_SOL),
  ];
  const platformFeeBps = 500; // 5%

  let escrowPda: PublicKey;
  let escrowBump: number;
  let vaultPda: PublicKey;
  let vaultBump: number;

  before(async () => {
    // Airdrop SOL to test wallets
    const airdropAmount = 100 * LAMPORTS_PER_SOL;

    const clientAirdrop = await provider.connection.requestAirdrop(
      client.publicKey,
      airdropAmount,
    );
    await provider.connection.confirmTransaction(clientAirdrop);

    const freelancerAirdrop = await provider.connection.requestAirdrop(
      freelancer.publicKey,
      airdropAmount,
    );
    await provider.connection.confirmTransaction(freelancerAirdrop);

    const arbitratorAirdrop = await provider.connection.requestAirdrop(
      arbitrator.publicKey,
      airdropAmount,
    );
    await provider.connection.confirmTransaction(arbitratorAirdrop);

    // Derive PDAs
    [escrowPda, escrowBump] = PublicKey.findProgramAddressSync(
      [Buffer.from("escrow"), Buffer.from(gigId)],
      program.programId,
    );

    [vaultPda, vaultBump] = PublicKey.findProgramAddressSync(
      [Buffer.from("vault"), escrowPda.toBuffer()],
      program.programId,
    );
  });

  describe("initialize_escrow", () => {
    it("creates an escrow PDA for a gig", async () => {
      await program.methods
        .initializeEscrow(
          gigId,
          freelancer.publicKey,
          arbitrator.publicKey,
          null, // SOL escrow (no token mint)
          milestoneAmounts,
          platformFeeBps,
          feeRecipient.publicKey,
        )
        .accounts({
          escrow: escrowPda,
          client: client.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([client])
        .rpc();

      const escrowAccount = await program.account.escrow.fetch(escrowPda);

      expect(escrowAccount.gigId).to.equal(gigId);
      expect(escrowAccount.client.toBase58()).to.equal(
        client.publicKey.toBase58(),
      );
      expect(escrowAccount.freelancer.toBase58()).to.equal(
        freelancer.publicKey.toBase58(),
      );
      expect(escrowAccount.arbitrator.toBase58()).to.equal(
        arbitrator.publicKey.toBase58(),
      );
      expect(escrowAccount.tokenMint).to.be.null;
      expect(escrowAccount.milestoneAmounts.length).to.equal(2);
      expect(escrowAccount.milestoneStatuses).to.deep.equal([0, 0]); // PENDING
      expect(escrowAccount.platformFeeBps).to.equal(platformFeeBps);
      expect(escrowAccount.isFunded).to.be.false;
      expect(escrowAccount.clientEmergencySigned).to.be.false;
      expect(escrowAccount.freelancerEmergencySigned).to.be.false;
    });

    it("rejects duplicate gig_id (PDA already exists)", async () => {
      try {
        await program.methods
          .initializeEscrow(
            gigId,
            freelancer.publicKey,
            arbitrator.publicKey,
            null,
            milestoneAmounts,
            platformFeeBps,
            feeRecipient.publicKey,
          )
          .accounts({
            escrow: escrowPda,
            client: client.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([client])
          .rpc();
        expect.fail("should have thrown");
      } catch (err) {
        // Account already initialized — Anchor rejects duplicate PDA init
        expect(err).to.exist;
      }
    });
  });

  describe("deposit", () => {
    it("deposits SOL into the vault", async () => {
      const totalAmount = milestoneAmounts.reduce(
        (acc, a) => acc.add(a),
        new anchor.BN(0),
      );

      await program.methods
        .deposit(totalAmount)
        .accounts({
          escrow: escrowPda,
          client: client.publicKey,
          vault: vaultPda,
          clientTokenAccount: null,
          vaultTokenAccount: null,
          tokenProgram: null,
          systemProgram: SystemProgram.programId,
        })
        .signers([client])
        .rpc();

      const escrowAccount = await program.account.escrow.fetch(escrowPda);
      expect(escrowAccount.isFunded).to.be.true;
      expect(escrowAccount.totalDeposited.toNumber()).to.equal(
        totalAmount.toNumber(),
      );

      // Verify vault balance
      const vaultBalance = await provider.connection.getBalance(vaultPda);
      expect(vaultBalance).to.equal(totalAmount.toNumber());
    });

    it("rejects double deposit", async () => {
      const totalAmount = milestoneAmounts.reduce(
        (acc, a) => acc.add(a),
        new anchor.BN(0),
      );

      try {
        await program.methods
          .deposit(totalAmount)
          .accounts({
            escrow: escrowPda,
            client: client.publicKey,
            vault: vaultPda,
            clientTokenAccount: null,
            vaultTokenAccount: null,
            tokenProgram: null,
            systemProgram: SystemProgram.programId,
          })
          .signers([client])
          .rpc();
        expect.fail("should have thrown");
      } catch (err) {
        expect(err.toString()).to.include("AlreadyFunded");
      }
    });
  });

  describe("complete_milestone", () => {
    it("releases milestone 0 to freelancer with fee deduction", async () => {
      const freelancerBalanceBefore = await provider.connection.getBalance(
        freelancer.publicKey,
      );
      const feeRecipientBalanceBefore = await provider.connection.getBalance(
        feeRecipient.publicKey,
      );

      await program.methods
        .completeMilestone(0)
        .accounts({
          escrow: escrowPda,
          client: client.publicKey,
          freelancer: freelancer.publicKey,
          feeRecipient: feeRecipient.publicKey,
          vault: vaultPda,
          vaultTokenAccount: null,
          freelancerTokenAccount: null,
          feeRecipientTokenAccount: null,
          tokenProgram: null,
          systemProgram: SystemProgram.programId,
        })
        .signers([client])
        .rpc();

      const amount = milestoneAmounts[0].toNumber();
      const expectedFee = Math.floor((amount * platformFeeBps) / 10_000);
      const expectedNet = amount - expectedFee;

      const freelancerBalanceAfter = await provider.connection.getBalance(
        freelancer.publicKey,
      );
      const feeRecipientBalanceAfter = await provider.connection.getBalance(
        feeRecipient.publicKey,
      );

      expect(freelancerBalanceAfter - freelancerBalanceBefore).to.equal(
        expectedNet,
      );
      expect(feeRecipientBalanceAfter - feeRecipientBalanceBefore).to.equal(
        expectedFee,
      );

      const escrowAccount = await program.account.escrow.fetch(escrowPda);
      expect(escrowAccount.milestoneStatuses[0]).to.equal(1); // COMPLETED
    });

    it("rejects completing an already completed milestone", async () => {
      try {
        await program.methods
          .completeMilestone(0)
          .accounts({
            escrow: escrowPda,
            client: client.publicKey,
            freelancer: freelancer.publicKey,
            feeRecipient: feeRecipient.publicKey,
            vault: vaultPda,
            vaultTokenAccount: null,
            freelancerTokenAccount: null,
            feeRecipientTokenAccount: null,
            tokenProgram: null,
            systemProgram: SystemProgram.programId,
          })
          .signers([client])
          .rpc();
        expect.fail("should have thrown");
      } catch (err) {
        expect(err.toString()).to.include("MilestoneNotPending");
      }
    });
  });

  // ─── Dispute flow: use milestone 1 (still PENDING) ────────────────────────

  describe("raise_dispute", () => {
    it("allows client to raise dispute on a pending milestone", async () => {
      await program.methods
        .raiseDispute(1)
        .accounts({
          escrow: escrowPda,
          signer: client.publicKey,
        })
        .signers([client])
        .rpc();

      const escrowAccount = await program.account.escrow.fetch(escrowPda);
      expect(escrowAccount.milestoneStatuses[1]).to.equal(2); // DISPUTED
    });

    it("rejects dispute on non-pending milestone", async () => {
      try {
        await program.methods
          .raiseDispute(1)
          .accounts({
            escrow: escrowPda,
            signer: client.publicKey,
          })
          .signers([client])
          .rpc();
        expect.fail("should have thrown");
      } catch (err) {
        expect(err.toString()).to.include("MilestoneNotPending");
      }
    });
  });

  describe("resolve_dispute", () => {
    it("arbitrator resolves dispute with PAY_FREELANCER", async () => {
      const freelancerBalanceBefore = await provider.connection.getBalance(
        freelancer.publicKey,
      );

      await program.methods
        .resolveDispute(1, 0, new anchor.BN(0)) // resolution=0 (PAY_FREELANCER)
        .accounts({
          escrow: escrowPda,
          arbitrator: arbitrator.publicKey,
          freelancer: freelancer.publicKey,
          client: client.publicKey,
          vault: vaultPda,
          vaultTokenAccount: null,
          freelancerTokenAccount: null,
          clientTokenAccount: null,
          tokenProgram: null,
          systemProgram: SystemProgram.programId,
        })
        .signers([arbitrator])
        .rpc();

      const amount = milestoneAmounts[1].toNumber();
      const freelancerBalanceAfter = await provider.connection.getBalance(
        freelancer.publicKey,
      );
      expect(freelancerBalanceAfter - freelancerBalanceBefore).to.equal(amount);

      const escrowAccount = await program.account.escrow.fetch(escrowPda);
      expect(escrowAccount.milestoneStatuses[1]).to.equal(3); // RESOLVED
    });
  });

  // ─── Dispute resolve: REFUND_CLIENT and SPLIT ─────────────────────────────

  describe("resolve_dispute (REFUND_CLIENT and SPLIT)", () => {
    // Create a second escrow to test remaining resolution types
    const gigId2 = "gig-002";
    let escrowPda2: PublicKey;
    let vaultPda2: PublicKey;

    const milestones2 = [
      new anchor.BN(1 * LAMPORTS_PER_SOL),
      new anchor.BN(1 * LAMPORTS_PER_SOL),
      new anchor.BN(1 * LAMPORTS_PER_SOL),
    ];

    before(async () => {
      [escrowPda2] = PublicKey.findProgramAddressSync(
        [Buffer.from("escrow"), Buffer.from(gigId2)],
        program.programId,
      );
      [vaultPda2] = PublicKey.findProgramAddressSync(
        [Buffer.from("vault"), escrowPda2.toBuffer()],
        program.programId,
      );

      // Initialize
      await program.methods
        .initializeEscrow(
          gigId2,
          freelancer.publicKey,
          arbitrator.publicKey,
          null,
          milestones2,
          platformFeeBps,
          feeRecipient.publicKey,
        )
        .accounts({
          escrow: escrowPda2,
          client: client.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([client])
        .rpc();

      // Deposit
      const total = milestones2.reduce(
        (acc, a) => acc.add(a),
        new anchor.BN(0),
      );
      await program.methods
        .deposit(total)
        .accounts({
          escrow: escrowPda2,
          client: client.publicKey,
          vault: vaultPda2,
          clientTokenAccount: null,
          vaultTokenAccount: null,
          tokenProgram: null,
          systemProgram: SystemProgram.programId,
        })
        .signers([client])
        .rpc();

      // Dispute milestones 0 and 1
      await program.methods
        .raiseDispute(0)
        .accounts({ escrow: escrowPda2, signer: client.publicKey })
        .signers([client])
        .rpc();

      await program.methods
        .raiseDispute(1)
        .accounts({ escrow: escrowPda2, signer: freelancer.publicKey })
        .signers([freelancer])
        .rpc();
    });

    it("resolves with REFUND_CLIENT", async () => {
      const clientBalanceBefore = await provider.connection.getBalance(
        client.publicKey,
      );

      await program.methods
        .resolveDispute(0, 1, new anchor.BN(0)) // REFUND_CLIENT
        .accounts({
          escrow: escrowPda2,
          arbitrator: arbitrator.publicKey,
          freelancer: freelancer.publicKey,
          client: client.publicKey,
          vault: vaultPda2,
          vaultTokenAccount: null,
          freelancerTokenAccount: null,
          clientTokenAccount: null,
          tokenProgram: null,
          systemProgram: SystemProgram.programId,
        })
        .signers([arbitrator])
        .rpc();

      const clientBalanceAfter = await provider.connection.getBalance(
        client.publicKey,
      );
      const amount = milestones2[0].toNumber();
      expect(clientBalanceAfter - clientBalanceBefore).to.equal(amount);

      const escrow = await program.account.escrow.fetch(escrowPda2);
      expect(escrow.milestoneStatuses[0]).to.equal(3); // RESOLVED
    });

    it("resolves with SPLIT", async () => {
      const splitAmount = new anchor.BN(0.6 * LAMPORTS_PER_SOL);
      const milestoneAmount = milestones2[1].toNumber();
      const expectedClientPay = milestoneAmount - splitAmount.toNumber();

      const freelancerBefore = await provider.connection.getBalance(
        freelancer.publicKey,
      );
      const clientBefore = await provider.connection.getBalance(
        client.publicKey,
      );

      await program.methods
        .resolveDispute(1, 2, splitAmount) // SPLIT
        .accounts({
          escrow: escrowPda2,
          arbitrator: arbitrator.publicKey,
          freelancer: freelancer.publicKey,
          client: client.publicKey,
          vault: vaultPda2,
          vaultTokenAccount: null,
          freelancerTokenAccount: null,
          clientTokenAccount: null,
          tokenProgram: null,
          systemProgram: SystemProgram.programId,
        })
        .signers([arbitrator])
        .rpc();

      const freelancerAfter = await provider.connection.getBalance(
        freelancer.publicKey,
      );
      const clientAfter = await provider.connection.getBalance(
        client.publicKey,
      );

      expect(freelancerAfter - freelancerBefore).to.equal(
        splitAmount.toNumber(),
      );
      expect(clientAfter - clientBefore).to.equal(expectedClientPay);

      const escrow = await program.account.escrow.fetch(escrowPda2);
      expect(escrow.milestoneStatuses[1]).to.equal(3); // RESOLVED
    });
  });

  // ─── Emergency withdrawal ─────────────────────────────────────────────────

  describe("emergency_withdrawal", () => {
    const gigId3 = "gig-003";
    let escrowPda3: PublicKey;
    let vaultPda3: PublicKey;

    const milestones3 = [new anchor.BN(2 * LAMPORTS_PER_SOL)];

    before(async () => {
      [escrowPda3] = PublicKey.findProgramAddressSync(
        [Buffer.from("escrow"), Buffer.from(gigId3)],
        program.programId,
      );
      [vaultPda3] = PublicKey.findProgramAddressSync(
        [Buffer.from("vault"), escrowPda3.toBuffer()],
        program.programId,
      );

      await program.methods
        .initializeEscrow(
          gigId3,
          freelancer.publicKey,
          arbitrator.publicKey,
          null,
          milestones3,
          platformFeeBps,
          feeRecipient.publicKey,
        )
        .accounts({
          escrow: escrowPda3,
          client: client.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([client])
        .rpc();

      const total = milestones3.reduce(
        (acc, a) => acc.add(a),
        new anchor.BN(0),
      );
      await program.methods
        .deposit(total)
        .accounts({
          escrow: escrowPda3,
          client: client.publicKey,
          vault: vaultPda3,
          clientTokenAccount: null,
          vaultTokenAccount: null,
          tokenProgram: null,
          systemProgram: SystemProgram.programId,
        })
        .signers([client])
        .rpc();
    });

    it("rejects emergency_withdraw before both parties sign", async () => {
      try {
        await program.methods
          .emergencyWithdraw()
          .accounts({
            escrow: escrowPda3,
            signer: client.publicKey,
            client: client.publicKey,
            vault: vaultPda3,
            vaultTokenAccount: null,
            clientTokenAccount: null,
            tokenProgram: null,
            systemProgram: SystemProgram.programId,
          })
          .signers([client])
          .rpc();
        expect.fail("should have thrown");
      } catch (err) {
        expect(err.toString()).to.include("NotBothSigned");
      }
    });

    it("client signs emergency withdrawal", async () => {
      await program.methods
        .signEmergencyWithdrawal()
        .accounts({
          escrow: escrowPda3,
          signer: client.publicKey,
        })
        .signers([client])
        .rpc();

      const escrow = await program.account.escrow.fetch(escrowPda3);
      expect(escrow.clientEmergencySigned).to.be.true;
      expect(escrow.freelancerEmergencySigned).to.be.false;
    });

    it("rejects duplicate sign from client", async () => {
      try {
        await program.methods
          .signEmergencyWithdrawal()
          .accounts({
            escrow: escrowPda3,
            signer: client.publicKey,
          })
          .signers([client])
          .rpc();
        expect.fail("should have thrown");
      } catch (err) {
        expect(err.toString()).to.include("AlreadySigned");
      }
    });

    it("freelancer signs emergency withdrawal", async () => {
      await program.methods
        .signEmergencyWithdrawal()
        .accounts({
          escrow: escrowPda3,
          signer: freelancer.publicKey,
        })
        .signers([freelancer])
        .rpc();

      const escrow = await program.account.escrow.fetch(escrowPda3);
      expect(escrow.clientEmergencySigned).to.be.true;
      expect(escrow.freelancerEmergencySigned).to.be.true;
    });

    it("executes emergency withdrawal after both sign", async () => {
      const clientBefore = await provider.connection.getBalance(
        client.publicKey,
      );
      const vaultBefore = await provider.connection.getBalance(vaultPda3);

      await program.methods
        .emergencyWithdraw()
        .accounts({
          escrow: escrowPda3,
          signer: client.publicKey,
          client: client.publicKey,
          vault: vaultPda3,
          vaultTokenAccount: null,
          clientTokenAccount: null,
          tokenProgram: null,
          systemProgram: SystemProgram.programId,
        })
        .signers([client])
        .rpc();

      const clientAfter = await provider.connection.getBalance(
        client.publicKey,
      );
      const vaultAfter = await provider.connection.getBalance(vaultPda3);

      // Client should receive all vault funds (minus tx fee)
      // We check that client balance increased and vault is empty
      expect(clientAfter).to.be.greaterThan(clientBefore);
      expect(vaultAfter).to.equal(0);

      const escrow = await program.account.escrow.fetch(escrowPda3);
      expect(escrow.clientEmergencySigned).to.be.false;
      expect(escrow.freelancerEmergencySigned).to.be.false;
    });
  });
});
