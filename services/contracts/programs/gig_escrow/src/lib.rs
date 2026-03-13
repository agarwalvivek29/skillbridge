use anchor_lang::prelude::*;
use anchor_lang::system_program;
use anchor_spl::token::{self, Token, TokenAccount, Transfer};

declare_id!("11111111111111111111111111111111");

/// Maximum length of a gig_id string (used for account sizing).
const MAX_GIG_ID_LEN: usize = 64;

/// Maximum number of milestones per escrow.
const MAX_MILESTONES: usize = 20;

/// Maximum platform fee: 10% (1000 basis points).
const MAX_FEE_BPS: u16 = 1000;

// ─── Milestone status constants ─────────────────────────────────────────────

const MILESTONE_PENDING: u8 = 0;
const MILESTONE_COMPLETED: u8 = 1;
const MILESTONE_DISPUTED: u8 = 2;
const MILESTONE_RESOLVED: u8 = 3;

// ─── Dispute resolution constants ───────────────────────────────────────────

const RESOLUTION_PAY_FREELANCER: u8 = 0;
const RESOLUTION_REFUND_CLIENT: u8 = 1;
const RESOLUTION_SPLIT: u8 = 2;

#[program]
pub mod gig_escrow {
    use super::*;

    /// Create an escrow PDA for a gig. Called by the client before depositing funds.
    ///
    /// Seeds: `[b"escrow", gig_id.as_bytes()]`
    pub fn initialize_escrow(
        ctx: Context<InitializeEscrow>,
        gig_id: String,
        freelancer: Pubkey,
        arbitrator: Pubkey,
        token_mint: Option<Pubkey>,
        milestone_amounts: Vec<u64>,
        platform_fee_bps: u16,
        fee_recipient: Pubkey,
    ) -> Result<()> {
        require!(
            !gig_id.is_empty() && gig_id.len() <= MAX_GIG_ID_LEN,
            EscrowError::InvalidGigId
        );
        require!(
            !milestone_amounts.is_empty() && milestone_amounts.len() <= MAX_MILESTONES,
            EscrowError::InvalidMilestones
        );
        require!(platform_fee_bps <= MAX_FEE_BPS, EscrowError::FeeTooHigh);
        require!(
            freelancer != Pubkey::default(),
            EscrowError::InvalidFreelancer
        );
        require!(
            arbitrator != Pubkey::default(),
            EscrowError::InvalidArbitrator
        );
        require!(
            fee_recipient != Pubkey::default(),
            EscrowError::InvalidFeeRecipient
        );
        require!(
            ctx.accounts.client.key() != freelancer,
            EscrowError::ClientEqualsFreelancer
        );

        let mut total: u64 = 0;
        let mut statuses: Vec<u8> = Vec::with_capacity(milestone_amounts.len());
        for amount in &milestone_amounts {
            require!(*amount > 0, EscrowError::ZeroMilestoneAmount);
            total = total.checked_add(*amount).ok_or(EscrowError::Overflow)?;
            statuses.push(MILESTONE_PENDING);
        }

        let escrow = &mut ctx.accounts.escrow;
        escrow.gig_id = gig_id;
        escrow.client = ctx.accounts.client.key();
        escrow.freelancer = freelancer;
        escrow.arbitrator = arbitrator;
        escrow.token_mint = token_mint;
        escrow.milestone_amounts = milestone_amounts;
        escrow.milestone_statuses = statuses;
        escrow.platform_fee_bps = platform_fee_bps;
        escrow.fee_recipient = fee_recipient;
        escrow.total_deposited = 0;
        escrow.total_released = 0;
        escrow.is_funded = false;
        escrow.client_emergency_signed = false;
        escrow.freelancer_emergency_signed = false;
        escrow.bump = ctx.bumps.escrow;

        emit!(EscrowInitialized {
            escrow: escrow.key(),
            gig_id: escrow.gig_id.clone(),
            client: escrow.client,
            freelancer: escrow.freelancer,
            total_amount: total,
        });

        Ok(())
    }

    /// Deposit funds (SOL or SPL token) into the escrow vault. Only the client can call this.
    ///
    /// For SOL: transfers lamports from client to the vault PDA.
    /// For SPL: transfers tokens from the client's token account to the vault token account.
    pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow;
        require!(!escrow.is_funded, EscrowError::AlreadyFunded);

        // Calculate expected total from milestone amounts
        let expected_total: u64 = escrow
            .milestone_amounts
            .iter()
            .try_fold(0u64, |acc, &a| acc.checked_add(a))
            .ok_or(EscrowError::Overflow)?;

        require!(amount == expected_total, EscrowError::InvalidDepositAmount);

        if escrow.token_mint.is_some() {
            // SPL token deposit
            let client_token = ctx
                .accounts
                .client_token_account
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;
            let vault_token = ctx
                .accounts
                .vault_token_account
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;
            let token_program = ctx
                .accounts
                .token_program
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;

            let transfer_accounts = Transfer {
                from: client_token.to_account_info(),
                to: vault_token.to_account_info(),
                authority: ctx.accounts.client.to_account_info(),
            };
            let cpi_ctx = CpiContext::new(token_program.to_account_info(), transfer_accounts);
            token::transfer(cpi_ctx, amount)?;
        } else {
            // SOL deposit: transfer lamports from client to vault PDA
            system_program::transfer(
                CpiContext::new(
                    ctx.accounts.system_program.to_account_info(),
                    system_program::Transfer {
                        from: ctx.accounts.client.to_account_info(),
                        to: ctx.accounts.vault.to_account_info(),
                    },
                ),
                amount,
            )?;
        }

        escrow.total_deposited = amount;
        escrow.is_funded = true;

        emit!(EscrowFunded {
            escrow: escrow.key(),
            client: escrow.client,
            amount,
        });

        Ok(())
    }

    /// Complete a milestone: release the milestone amount to the freelancer (minus platform fee).
    /// Only the client can call this.
    pub fn complete_milestone(ctx: Context<CompleteMilestone>, milestone_index: u8) -> Result<()> {
        let escrow = &ctx.accounts.escrow;
        require!(escrow.is_funded, EscrowError::NotFunded);

        let idx = milestone_index as usize;
        require!(
            idx < escrow.milestone_statuses.len(),
            EscrowError::InvalidMilestoneIndex
        );
        require!(
            escrow.milestone_statuses[idx] == MILESTONE_PENDING,
            EscrowError::MilestoneNotPending
        );

        let amount = escrow.milestone_amounts[idx];
        let fee = (amount as u128)
            .checked_mul(escrow.platform_fee_bps as u128)
            .ok_or(EscrowError::Overflow)?
            .checked_div(10_000)
            .ok_or(EscrowError::Overflow)? as u64;
        let net = amount.checked_sub(fee).ok_or(EscrowError::Overflow)?;

        // Build signer seeds for the vault PDA
        let escrow_key = escrow.key();
        let vault_bump = ctx.bumps.vault;
        let vault_seeds: &[&[u8]] = &[b"vault", escrow_key.as_ref(), &[vault_bump]];

        if escrow.token_mint.is_some() {
            // SPL token transfers
            let vault_token = ctx
                .accounts
                .vault_token_account
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;
            let freelancer_token = ctx
                .accounts
                .freelancer_token_account
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;
            let token_program = ctx
                .accounts
                .token_program
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;

            // Pay freelancer
            let transfer_to_freelancer = Transfer {
                from: vault_token.to_account_info(),
                to: freelancer_token.to_account_info(),
                authority: ctx.accounts.vault.to_account_info(),
            };
            token::transfer(
                CpiContext::new_with_signer(
                    token_program.to_account_info(),
                    transfer_to_freelancer,
                    &[vault_seeds],
                ),
                net,
            )?;

            // Pay platform fee
            if fee > 0 {
                let fee_token = ctx
                    .accounts
                    .fee_recipient_token_account
                    .as_ref()
                    .ok_or(EscrowError::MissingTokenAccount)?;
                let transfer_fee = Transfer {
                    from: vault_token.to_account_info(),
                    to: fee_token.to_account_info(),
                    authority: ctx.accounts.vault.to_account_info(),
                };
                token::transfer(
                    CpiContext::new_with_signer(
                        token_program.to_account_info(),
                        transfer_fee,
                        &[vault_seeds],
                    ),
                    fee,
                )?;
            }
        } else {
            // SOL transfers from vault PDA
            // Pay freelancer
            **ctx
                .accounts
                .vault
                .to_account_info()
                .try_borrow_mut_lamports()? -= net;
            **ctx
                .accounts
                .freelancer
                .to_account_info()
                .try_borrow_mut_lamports()? += net;

            // Pay platform fee
            if fee > 0 {
                **ctx
                    .accounts
                    .vault
                    .to_account_info()
                    .try_borrow_mut_lamports()? -= fee;
                **ctx
                    .accounts
                    .fee_recipient
                    .to_account_info()
                    .try_borrow_mut_lamports()? += fee;
            }
        }

        // Update state after transfers
        let escrow = &mut ctx.accounts.escrow;
        escrow.milestone_statuses[idx] = MILESTONE_COMPLETED;
        escrow.total_released = escrow
            .total_released
            .checked_add(amount)
            .ok_or(EscrowError::Overflow)?;

        emit!(FundsReleased {
            escrow: escrow.key(),
            milestone_index,
            freelancer: escrow.freelancer,
            net_amount: net,
            fee_amount: fee,
        });

        Ok(())
    }

    /// Raise a dispute on a pending milestone. Either the client or freelancer can call this.
    pub fn raise_dispute(ctx: Context<RaiseDispute>, milestone_index: u8) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow;
        require!(escrow.is_funded, EscrowError::NotFunded);

        let idx = milestone_index as usize;
        require!(
            idx < escrow.milestone_statuses.len(),
            EscrowError::InvalidMilestoneIndex
        );
        require!(
            escrow.milestone_statuses[idx] == MILESTONE_PENDING,
            EscrowError::MilestoneNotPending
        );

        escrow.milestone_statuses[idx] = MILESTONE_DISPUTED;

        emit!(DisputeRaised {
            escrow: escrow.key(),
            milestone_index,
            raised_by: ctx.accounts.signer.key(),
        });

        Ok(())
    }

    /// Resolve a disputed milestone. Only the arbitrator can call this.
    ///
    /// `resolution`: 0 = PAY_FREELANCER, 1 = REFUND_CLIENT, 2 = SPLIT
    /// `freelancer_split_amount`: only used when resolution == SPLIT
    ///
    /// Dispute resolution does not deduct a platform fee. This is intentional:
    /// dispute resolution is adversarial, not cooperative. The platform fee applies
    /// only to voluntary `complete_milestone` calls.
    pub fn resolve_dispute(
        ctx: Context<ResolveDispute>,
        milestone_index: u8,
        resolution: u8,
        freelancer_split_amount: u64,
    ) -> Result<()> {
        let escrow = &ctx.accounts.escrow;
        require!(escrow.is_funded, EscrowError::NotFunded);

        let idx = milestone_index as usize;
        require!(
            idx < escrow.milestone_statuses.len(),
            EscrowError::InvalidMilestoneIndex
        );
        require!(
            escrow.milestone_statuses[idx] == MILESTONE_DISPUTED,
            EscrowError::MilestoneNotDisputed
        );

        let amount = escrow.milestone_amounts[idx];
        let (freelancer_pay, client_pay) = match resolution {
            RESOLUTION_PAY_FREELANCER => (amount, 0u64),
            RESOLUTION_REFUND_CLIENT => (0u64, amount),
            RESOLUTION_SPLIT => {
                require!(
                    freelancer_split_amount <= amount,
                    EscrowError::SplitExceedsMilestone
                );
                (
                    freelancer_split_amount,
                    amount
                        .checked_sub(freelancer_split_amount)
                        .ok_or(EscrowError::Overflow)?,
                )
            }
            _ => return Err(EscrowError::InvalidResolution.into()),
        };

        // Build signer seeds for the vault PDA
        let escrow_key = escrow.key();
        let vault_bump = ctx.bumps.vault;
        let vault_seeds: &[&[u8]] = &[b"vault", escrow_key.as_ref(), &[vault_bump]];

        if escrow.token_mint.is_some() {
            let vault_token = ctx
                .accounts
                .vault_token_account
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;
            let token_program = ctx
                .accounts
                .token_program
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;

            if freelancer_pay > 0 {
                let freelancer_token = ctx
                    .accounts
                    .freelancer_token_account
                    .as_ref()
                    .ok_or(EscrowError::MissingTokenAccount)?;
                let xfer = Transfer {
                    from: vault_token.to_account_info(),
                    to: freelancer_token.to_account_info(),
                    authority: ctx.accounts.vault.to_account_info(),
                };
                token::transfer(
                    CpiContext::new_with_signer(
                        token_program.to_account_info(),
                        xfer,
                        &[vault_seeds],
                    ),
                    freelancer_pay,
                )?;
            }
            if client_pay > 0 {
                let client_token = ctx
                    .accounts
                    .client_token_account
                    .as_ref()
                    .ok_or(EscrowError::MissingTokenAccount)?;
                let xfer = Transfer {
                    from: vault_token.to_account_info(),
                    to: client_token.to_account_info(),
                    authority: ctx.accounts.vault.to_account_info(),
                };
                token::transfer(
                    CpiContext::new_with_signer(
                        token_program.to_account_info(),
                        xfer,
                        &[vault_seeds],
                    ),
                    client_pay,
                )?;
            }
        } else {
            // SOL transfers
            if freelancer_pay > 0 {
                **ctx
                    .accounts
                    .vault
                    .to_account_info()
                    .try_borrow_mut_lamports()? -= freelancer_pay;
                **ctx
                    .accounts
                    .freelancer
                    .to_account_info()
                    .try_borrow_mut_lamports()? += freelancer_pay;
            }
            if client_pay > 0 {
                **ctx
                    .accounts
                    .vault
                    .to_account_info()
                    .try_borrow_mut_lamports()? -= client_pay;
                **ctx
                    .accounts
                    .client
                    .to_account_info()
                    .try_borrow_mut_lamports()? += client_pay;
            }
        }

        // Update state
        let escrow = &mut ctx.accounts.escrow;
        escrow.milestone_statuses[idx] = MILESTONE_RESOLVED;
        escrow.total_released = escrow
            .total_released
            .checked_add(amount)
            .ok_or(EscrowError::Overflow)?;

        emit!(DisputeResolved {
            escrow: escrow.key(),
            milestone_index,
            resolution,
            freelancer_pay,
            client_pay,
        });

        Ok(())
    }

    /// Sign the emergency withdrawal. Both client and freelancer must call this
    /// before `emergency_withdraw` can execute.
    pub fn sign_emergency_withdrawal(ctx: Context<SignEmergencyWithdrawal>) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow;
        let signer = ctx.accounts.signer.key();

        if signer == escrow.client {
            require!(!escrow.client_emergency_signed, EscrowError::AlreadySigned);
            escrow.client_emergency_signed = true;
        } else if signer == escrow.freelancer {
            require!(
                !escrow.freelancer_emergency_signed,
                EscrowError::AlreadySigned
            );
            escrow.freelancer_emergency_signed = true;
        } else {
            return Err(EscrowError::Unauthorized.into());
        }

        emit!(EmergencyWithdrawalSigned {
            escrow: escrow.key(),
            signer,
        });

        Ok(())
    }

    /// Execute emergency withdrawal after both client and freelancer have signed.
    /// Returns all remaining vault funds to the client.
    ///
    /// Known limitation: funds always go to the client. Both parties must consent
    /// (2-of-2 sign), so a fraudulent client cannot drain unilaterally. For v1 this
    /// is acceptable; a future version may split by milestone status.
    pub fn emergency_withdraw(ctx: Context<EmergencyWithdraw>) -> Result<()> {
        let escrow = &mut ctx.accounts.escrow;
        require!(
            escrow.client_emergency_signed && escrow.freelancer_emergency_signed,
            EscrowError::NotBothSigned
        );

        // Reset signatures before transfer to prevent re-execution
        escrow.client_emergency_signed = false;
        escrow.freelancer_emergency_signed = false;

        let escrow_key = escrow.key();
        let vault_bump = ctx.bumps.vault;
        let vault_seeds: &[&[u8]] = &[b"vault", escrow_key.as_ref(), &[vault_bump]];

        if escrow.token_mint.is_some() {
            let vault_token = ctx
                .accounts
                .vault_token_account
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;
            let client_token = ctx
                .accounts
                .client_token_account
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;
            let token_program = ctx
                .accounts
                .token_program
                .as_ref()
                .ok_or(EscrowError::MissingTokenAccount)?;

            let balance = vault_token.amount;
            require!(balance > 0, EscrowError::NoFundsToWithdraw);

            let xfer = Transfer {
                from: vault_token.to_account_info(),
                to: client_token.to_account_info(),
                authority: ctx.accounts.vault.to_account_info(),
            };
            token::transfer(
                CpiContext::new_with_signer(token_program.to_account_info(), xfer, &[vault_seeds]),
                balance,
            )?;
        } else {
            let vault_lamports = ctx.accounts.vault.to_account_info().lamports();
            require!(vault_lamports > 0, EscrowError::NoFundsToWithdraw);

            **ctx
                .accounts
                .vault
                .to_account_info()
                .try_borrow_mut_lamports()? -= vault_lamports;
            **ctx
                .accounts
                .client
                .to_account_info()
                .try_borrow_mut_lamports()? += vault_lamports;
        }

        emit!(EmergencyWithdrawal {
            escrow: escrow.key(),
            client: escrow.client,
        });

        Ok(())
    }
}

// ─── Account Structs ────────────────────────────────────────────────────────

#[account]
pub struct Escrow {
    /// Unique gig identifier (max 64 chars).
    pub gig_id: String,
    /// Client who deposits funds and approves milestones.
    pub client: Pubkey,
    /// Freelancer who receives milestone payouts.
    pub freelancer: Pubkey,
    /// Arbitrator who can resolve disputes.
    pub arbitrator: Pubkey,
    /// SPL token mint. None (all zeros) means SOL.
    pub token_mint: Option<Pubkey>,
    /// Per-milestone amounts in lamports (SOL) or token base units (SPL).
    pub milestone_amounts: Vec<u64>,
    /// Per-milestone statuses: 0=PENDING, 1=COMPLETED, 2=DISPUTED, 3=RESOLVED.
    pub milestone_statuses: Vec<u8>,
    /// Platform fee in basis points (e.g. 500 = 5%). Max 1000 (10%).
    pub platform_fee_bps: u16,
    /// Address that receives the platform fee cut.
    pub fee_recipient: Pubkey,
    /// Total lamports/tokens deposited.
    pub total_deposited: u64,
    /// Total lamports/tokens released (completed + resolved).
    pub total_released: u64,
    /// Whether funds have been deposited.
    pub is_funded: bool,
    /// Client has signed emergency withdrawal.
    pub client_emergency_signed: bool,
    /// Freelancer has signed emergency withdrawal.
    pub freelancer_emergency_signed: bool,
    /// PDA bump seed.
    pub bump: u8,
}

impl Escrow {
    /// Calculate the space needed for an Escrow account.
    /// 8 (discriminator) + fields
    pub fn space(num_milestones: usize, gig_id_len: usize) -> usize {
        8                           // anchor discriminator
        + 4 + gig_id_len           // String: 4-byte length prefix + data
        + 32                        // client
        + 32                        // freelancer
        + 32                        // arbitrator
        + 1 + 32                    // Option<Pubkey>: 1 tag + 32 data
        + 4 + (num_milestones * 8)  // Vec<u64>: 4-byte prefix + data
        + 4 + num_milestones        // Vec<u8>: 4-byte prefix + data
        + 2                         // platform_fee_bps (u16)
        + 32                        // fee_recipient
        + 8                         // total_deposited
        + 8                         // total_released
        + 1                         // is_funded
        + 1                         // client_emergency_signed
        + 1                         // freelancer_emergency_signed
        + 1 // bump
    }
}

// ─── Instruction Contexts ───────────────────────────────────────────────────

#[derive(Accounts)]
#[instruction(gig_id: String, freelancer: Pubkey, arbitrator: Pubkey, token_mint: Option<Pubkey>, milestone_amounts: Vec<u64>)]
pub struct InitializeEscrow<'info> {
    #[account(
        init,
        payer = client,
        space = Escrow::space(milestone_amounts.len(), gig_id.len()),
        seeds = [b"escrow", gig_id.as_bytes()],
        bump,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(mut)]
    pub client: Signer<'info>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(
        mut,
        seeds = [b"escrow", escrow.gig_id.as_bytes()],
        bump = escrow.bump,
        has_one = client,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(mut)]
    pub client: Signer<'info>,

    /// Vault PDA that holds SOL. For SPL deposits, SOL vault still required as seed anchor.
    /// CHECK: This is a PDA used as a vault; validated by seeds constraint.
    #[account(
        mut,
        seeds = [b"vault", escrow.key().as_ref()],
        bump,
    )]
    pub vault: SystemAccount<'info>,

    /// Client's SPL token account (required only for SPL deposits).
    #[account(mut)]
    pub client_token_account: Option<Account<'info, TokenAccount>>,

    /// Vault's SPL token account (required only for SPL deposits).
    #[account(mut)]
    pub vault_token_account: Option<Account<'info, TokenAccount>>,

    pub token_program: Option<Program<'info, Token>>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(milestone_index: u8)]
pub struct CompleteMilestone<'info> {
    #[account(
        mut,
        seeds = [b"escrow", escrow.gig_id.as_bytes()],
        bump = escrow.bump,
        has_one = client,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(mut)]
    pub client: Signer<'info>,

    /// CHECK: Validated via has_one on escrow. Receives milestone payout.
    #[account(
        mut,
        constraint = freelancer.key() == escrow.freelancer @ EscrowError::InvalidFreelancer,
    )]
    pub freelancer: UncheckedAccount<'info>,

    /// CHECK: Validated against escrow.fee_recipient. Receives platform fee.
    #[account(
        mut,
        constraint = fee_recipient.key() == escrow.fee_recipient @ EscrowError::InvalidFeeRecipient,
    )]
    pub fee_recipient: UncheckedAccount<'info>,

    /// Vault PDA holding SOL.
    /// CHECK: Validated by seeds.
    #[account(
        mut,
        seeds = [b"vault", escrow.key().as_ref()],
        bump,
    )]
    pub vault: SystemAccount<'info>,

    /// Vault's SPL token account (optional, for SPL escrows).
    #[account(mut)]
    pub vault_token_account: Option<Account<'info, TokenAccount>>,

    /// Freelancer's SPL token account (optional, for SPL escrows).
    #[account(mut)]
    pub freelancer_token_account: Option<Account<'info, TokenAccount>>,

    /// Fee recipient's SPL token account (optional, for SPL escrows).
    #[account(mut)]
    pub fee_recipient_token_account: Option<Account<'info, TokenAccount>>,

    pub token_program: Option<Program<'info, Token>>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(milestone_index: u8)]
pub struct RaiseDispute<'info> {
    #[account(
        mut,
        seeds = [b"escrow", escrow.gig_id.as_bytes()],
        bump = escrow.bump,
    )]
    pub escrow: Account<'info, Escrow>,

    /// Either the client or the freelancer.
    #[account(
        constraint = signer.key() == escrow.client || signer.key() == escrow.freelancer @ EscrowError::Unauthorized,
    )]
    pub signer: Signer<'info>,
}

#[derive(Accounts)]
#[instruction(milestone_index: u8)]
pub struct ResolveDispute<'info> {
    #[account(
        mut,
        seeds = [b"escrow", escrow.gig_id.as_bytes()],
        bump = escrow.bump,
        has_one = arbitrator,
    )]
    pub escrow: Account<'info, Escrow>,

    pub arbitrator: Signer<'info>,

    /// CHECK: Validated via constraint. Receives funds on PAY_FREELANCER or SPLIT.
    #[account(
        mut,
        constraint = freelancer.key() == escrow.freelancer @ EscrowError::InvalidFreelancer,
    )]
    pub freelancer: UncheckedAccount<'info>,

    /// CHECK: Validated via constraint. Receives funds on REFUND_CLIENT or SPLIT.
    #[account(
        mut,
        constraint = client.key() == escrow.client @ EscrowError::Unauthorized,
    )]
    pub client: UncheckedAccount<'info>,

    /// Vault PDA holding SOL.
    /// CHECK: Validated by seeds.
    #[account(
        mut,
        seeds = [b"vault", escrow.key().as_ref()],
        bump,
    )]
    pub vault: SystemAccount<'info>,

    /// Vault's SPL token account (optional).
    #[account(mut)]
    pub vault_token_account: Option<Account<'info, TokenAccount>>,

    /// Freelancer's SPL token account (optional).
    #[account(mut)]
    pub freelancer_token_account: Option<Account<'info, TokenAccount>>,

    /// Client's SPL token account (optional).
    #[account(mut)]
    pub client_token_account: Option<Account<'info, TokenAccount>>,

    pub token_program: Option<Program<'info, Token>>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct SignEmergencyWithdrawal<'info> {
    #[account(
        mut,
        seeds = [b"escrow", escrow.gig_id.as_bytes()],
        bump = escrow.bump,
    )]
    pub escrow: Account<'info, Escrow>,

    /// Either the client or the freelancer.
    #[account(
        constraint = signer.key() == escrow.client || signer.key() == escrow.freelancer @ EscrowError::Unauthorized,
    )]
    pub signer: Signer<'info>,
}

#[derive(Accounts)]
pub struct EmergencyWithdraw<'info> {
    #[account(
        mut,
        seeds = [b"escrow", escrow.gig_id.as_bytes()],
        bump = escrow.bump,
    )]
    pub escrow: Account<'info, Escrow>,

    /// Either the client or the freelancer can trigger after both have signed.
    #[account(
        constraint = signer.key() == escrow.client || signer.key() == escrow.freelancer @ EscrowError::Unauthorized,
    )]
    pub signer: Signer<'info>,

    /// CHECK: Validated via constraint. Receives all remaining funds.
    #[account(
        mut,
        constraint = client.key() == escrow.client @ EscrowError::Unauthorized,
    )]
    pub client: UncheckedAccount<'info>,

    /// Vault PDA holding SOL.
    /// CHECK: Validated by seeds.
    #[account(
        mut,
        seeds = [b"vault", escrow.key().as_ref()],
        bump,
    )]
    pub vault: SystemAccount<'info>,

    /// Vault's SPL token account (optional).
    #[account(mut)]
    pub vault_token_account: Option<Account<'info, TokenAccount>>,

    /// Client's SPL token account (optional).
    #[account(mut)]
    pub client_token_account: Option<Account<'info, TokenAccount>>,

    pub token_program: Option<Program<'info, Token>>,

    pub system_program: Program<'info, System>,
}

// ─── Events ─────────────────────────────────────────────────────────────────

#[event]
pub struct EscrowInitialized {
    pub escrow: Pubkey,
    pub gig_id: String,
    pub client: Pubkey,
    pub freelancer: Pubkey,
    pub total_amount: u64,
}

#[event]
pub struct EscrowFunded {
    pub escrow: Pubkey,
    pub client: Pubkey,
    pub amount: u64,
}

#[event]
pub struct FundsReleased {
    pub escrow: Pubkey,
    pub milestone_index: u8,
    pub freelancer: Pubkey,
    pub net_amount: u64,
    pub fee_amount: u64,
}

#[event]
pub struct DisputeRaised {
    pub escrow: Pubkey,
    pub milestone_index: u8,
    pub raised_by: Pubkey,
}

#[event]
pub struct DisputeResolved {
    pub escrow: Pubkey,
    pub milestone_index: u8,
    pub resolution: u8,
    pub freelancer_pay: u64,
    pub client_pay: u64,
}

#[event]
pub struct EmergencyWithdrawalSigned {
    pub escrow: Pubkey,
    pub signer: Pubkey,
}

#[event]
pub struct EmergencyWithdrawal {
    pub escrow: Pubkey,
    pub client: Pubkey,
}

// ─── Errors ─────────────────────────────────────────────────────────────────

#[error_code]
pub enum EscrowError {
    #[msg("Invalid gig ID: must be 1-64 characters")]
    InvalidGigId,
    #[msg("Invalid milestones: must have 1-20 milestones")]
    InvalidMilestones,
    #[msg("Platform fee exceeds maximum of 10% (1000 bps)")]
    FeeTooHigh,
    #[msg("Invalid freelancer address")]
    InvalidFreelancer,
    #[msg("Invalid arbitrator address")]
    InvalidArbitrator,
    #[msg("Invalid fee recipient address")]
    InvalidFeeRecipient,
    #[msg("Client and freelancer cannot be the same address")]
    ClientEqualsFreelancer,
    #[msg("Milestone amount must be greater than zero")]
    ZeroMilestoneAmount,
    #[msg("Arithmetic overflow")]
    Overflow,
    #[msg("Escrow is already funded")]
    AlreadyFunded,
    #[msg("Deposit amount must equal total of all milestone amounts")]
    InvalidDepositAmount,
    #[msg("Missing required SPL token account")]
    MissingTokenAccount,
    #[msg("Escrow is not funded")]
    NotFunded,
    #[msg("Invalid milestone index")]
    InvalidMilestoneIndex,
    #[msg("Milestone is not in PENDING status")]
    MilestoneNotPending,
    #[msg("Milestone is not in DISPUTED status")]
    MilestoneNotDisputed,
    #[msg("Invalid dispute resolution value")]
    InvalidResolution,
    #[msg("Freelancer split exceeds milestone amount")]
    SplitExceedsMilestone,
    #[msg("Unauthorized: signer is not client or freelancer")]
    Unauthorized,
    #[msg("Emergency withdrawal already signed by this party")]
    AlreadySigned,
    #[msg("Both client and freelancer must sign before emergency withdrawal")]
    NotBothSigned,
    #[msg("No funds to withdraw")]
    NoFundsToWithdraw,
}
