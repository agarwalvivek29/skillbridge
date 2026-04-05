use anchor_lang::prelude::*;

// Reputation program for SkillBridge - tracks freelancer reputation on-chain
// PDA seeds: [b"reputation", wallet_address.as_bytes()]

declare_id!("Rep1tation1111111111111111111111111111111111");

/// Maximum length for strings
const MAX_URI_LEN: usize = 256;

#[program]
pub mod reputation {
    use super::*;

    /// Initialize a reputation account for a user
    /// Seeds: [b"reputation", user_wallet.as_bytes()]
    pub fn initialize_reputation(
        ctx: Context<InitializeReputation>,
    ) -> Result<()> {
        let reputation = &mut ctx.accounts.reputation;
        let user_wallet = ctx.accounts.user.key();
        
        reputation.wallet_address = user_wallet;
        reputation.gigs_completed = 0;
        reputation.gigs_as_client = 0;
        reputation.total_earned = 0;
        reputation.average_ai_score = 0;
        reputation.dispute_rate_pct = 0;
        reputation.average_rating_x100 = 0;
        reputation.rating_count = 0;
        reputation.last_synced_at = Clock::get()?.unix_timestamp;
        reputation.bump = ctx.bumps.reputation;

        msg!("Reputation initialized for: {}", user_wallet);
        Ok(())
    }

    /// Update reputation after a gig is completed
    /// Called via CPI from gig_escrow program or by authorized API
    pub fn update_reputation_on_complete(
        ctx: Context<UpdateReputation>,
        earned_amount: u64,
        ai_score: u8,
    ) -> Result<()> {
        require!(ai_score <= 100, ReputationError::InvalidScore);
        
        let reputation = &mut ctx.accounts.reputation;
        
        // Update gigs completed
        reputation.gigs_completed = reputation.gigs_completed
            .checked_add(1)
            .ok_or(ReputationError::Overflow)?;
        
        // Update total earned
        reputation.total_earned = reputation.total_earned
            .checked_add(earned_amount)
            .ok_or(ReputationError::Overflow)?;
        
        // Update average AI score (weighted average)
        let total_score = (reputation.average_ai_score as u64)
            .checked_mul(reputation.gigs_completed as u64 - 1)
            .unwrap_or(0)
            .checked_add(ai_score as u64)
            .ok_or(ReputationError::Overflow)?;
        
        reputation.average_ai_score = (total_score / reputation.gigs_completed as u64) as u8;
        reputation.last_synced_at = Clock::get()?.unix_timestamp;

        msg!(
            "Reputation updated: gigs={}, earned={}, avg_score={}",
            reputation.gigs_completed,
            reputation.total_earned,
            reputation.average_ai_score
        );
        Ok(())
    }

    /// Update reputation when user acts as client
    pub fn update_reputation_as_client(
        ctx: Context<UpdateReputation>,
    ) -> Result<()> {
        let reputation = &mut ctx.accounts.reputation;
        
        reputation.gigs_as_client = reputation.gigs_as_client
            .checked_add(1)
            .ok_or(ReputationError::Overflow)?;
        reputation.last_synced_at = Clock::get()?.unix_timestamp;

        msg!("Client reputation updated: gigs_as_client={}", reputation.gigs_as_client);
        Ok(())
    }

    /// Update rating received from counterparty
    pub fn update_rating(
        ctx: Context<UpdateReputation>,
        rating_x100: u16, // Rating 0-500 (0-5.00 stars)
    ) -> Result<()> {
        require!(rating_x100 <= 500, ReputationError::InvalidRating);
        
        let reputation = &mut ctx.accounts.reputation;
        
        // Update average rating (weighted)
        let total_rating = (reputation.average_rating_x100 as u64)
            .checked_mul(reputation.rating_count as u64)
            .unwrap_or(0)
            .checked_add(rating_x100 as u64)
            .ok_or(ReputationError::Overflow)?;
        
        reputation.rating_count = reputation.rating_count
            .checked_add(1)
            .ok_or(ReputationError::Overflow)?;
        
        reputation.average_rating_x100 = (total_rating / reputation.rating_count as u64) as u16;
        reputation.last_synced_at = Clock::get()?.unix_timestamp;

        msg!(
            "Rating updated: count={}, avg={}",
            reputation.rating_count,
            reputation.average_rating_x100
        );
        Ok(())
    }

    /// Update dispute rate
    pub fn update_dispute_rate(
        ctx: Context<UpdateReputation>,
        total_gigs: u32,
        disputed_gigs: u32,
    ) -> Result<()> {
        require!(disputed_gigs <= total_gigs, ReputationError::InvalidDisputeCount);
        
        let reputation = &mut ctx.accounts.reputation;
        
        if total_gigs > 0 {
            reputation.dispute_rate_pct = ((disputed_gigs as u64 * 100) / total_gigs as u64) as u8;
        }
        reputation.last_synced_at = Clock::get()?.unix_timestamp;

        msg!("Dispute rate updated: {}%", reputation.dispute_rate_pct);
        Ok(())
    }

    /// Sync reputation data (called by background sync job)
    pub fn sync_reputation(
        ctx: Context<UpdateReputation>,
        gigs_completed: u32,
        gigs_as_client: u32,
        total_earned: u64,
        average_ai_score: u8,
        dispute_rate_pct: u8,
        average_rating_x100: u16,
        rating_count: u32,
    ) -> Result<()> {
        // Only authority can sync
        require!(
            ctx.accounts.authority.key() == ctx.accounts.reputation.wallet_address
                || ctx.accounts.authority.key() == ctx.accounts.program_authority.key(),
            ReputationError::Unauthorized
        );

        let reputation = &mut ctx.accounts.reputation;
        
        reputation.gigs_completed = gigs_completed;
        reputation.gigs_as_client = gigs_as_client;
        reputation.total_earned = total_earned;
        reputation.average_ai_score = average_ai_score;
        reputation.dispute_rate_pct = dispute_rate_pct;
        reputation.average_rating_x100 = average_rating_x100;
        reputation.rating_count = rating_count;
        reputation.last_synced_at = Clock::get()?.unix_timestamp;

        msg!("Reputation synced at {}", reputation.last_synced_at);
        Ok(())
    }
}

// ─── Account Structures ────────────────────────────────────────────────────

#[derive(Accounts)]
pub struct InitializeReputation<'info> {
    #[account(
        init,
        payer = user,
        space = ReputationAccount::SIZE,
        seeds = [b"reputation", user.key().as_ref()],
        bump
    )]
    pub reputation: Account<'info, ReputationAccount>,
    
    #[account(mut)]
    pub user: Signer<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UpdateReputation<'info> {
    #[account(
        mut,
        seeds = [b"reputation", reputation.wallet_address.as_ref()],
        bump = reputation.bump,
    )]
    pub reputation: Account<'info, ReputationAccount>,
    
    /// Authority that can update (user themselves or program authority)
    pub authority: Signer<'info>,
    
    /// Program authority (PDA or designated admin)
    /// CHECK: This is the program's authority for automated updates
    pub program_authority: AccountInfo<'info>,
}

// ─── Data Structures ──────────────────────────────────────────────────────

#[account]
pub struct ReputationAccount {
    /// User's wallet address (also the PDA seed)
    pub wallet_address: Pubkey,
    /// Number of gigs completed as freelancer
    pub gigs_completed: u32,
    /// Number of gigs created as client
    pub gigs_as_client: u32,
    /// Total earnings in lamports/smallest unit
    pub total_earned: u64,
    /// Average AI review score (0-100)
    pub average_ai_score: u8,
    /// Dispute rate percentage (0-100)
    pub dispute_rate_pct: u8,
    /// Average rating x100 (0-500 for 0-5.00 stars)
    pub average_rating_x100: u16,
    /// Number of ratings received
    pub rating_count: u32,
    /// Last sync timestamp
    pub last_synced_at: i64,
    /// PDA bump
    pub bump: u8,
}

impl ReputationAccount {
    /// Account size calculation
    pub const SIZE: usize = 8 + // discriminator
        32 + // wallet_address: Pubkey
        4 +  // gigs_completed: u32
        4 +  // gigs_as_client: u32
        8 +  // total_earned: u64
        1 +  // average_ai_score: u8
        1 +  // dispute_rate_pct: u8
        2 +  // average_rating_x100: u16
        4 +  // rating_count: u32
        8 +  // last_synced_at: i64
        1;   // bump: u8
}

// ─── Error Codes ──────────────────────────────────────────────────────────

#[error_code]
pub enum ReputationError {
    #[msg("Invalid AI score, must be 0-100")]
    InvalidScore,
    #[msg("Invalid rating, must be 0-500")]
    InvalidRating,
    #[msg("Invalid dispute count")]
    InvalidDisputeCount,
    #[msg("Arithmetic overflow")]
    Overflow,
    #[msg("Unauthorized to update reputation")]
    Unauthorized,
}
