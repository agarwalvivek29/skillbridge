"""domain/reputation_sync.py — Background sync of on-chain reputation data."""

from __future__ import annotations
import json
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.domain.reputation import upsert_reputation, validate_wallet_address

logger = logging.getLogger(__name__)
_ABI_PATH = (
    Path(__file__).resolve().parents[4] / "contracts" / "abi" / "Reputation.json"
)


async def sync_reputation_from_chain(
    db: AsyncSession,
    *,
    from_block: int | str = "earliest",
    to_block: int | str = "latest",
) -> int:
    contract_address = settings.reputation_contract_address
    if not contract_address:
        logger.warning("reputation_contract_address not set; skipping sync")
        return 0
    try:
        from web3 import Web3
    except ImportError:
        logger.warning("web3 not installed; skipping chain sync")
        return 0
    w3 = Web3(Web3.HTTPProvider(settings.base_rpc_url))
    if not w3.is_connected():
        return 0
    with open(_ABI_PATH) as f:
        abi = json.load(f)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_address), abi=abi
    )
    events = contract.events.ReputationUpdated.create_filter(
        fromBlock=from_block, toBlock=to_block
    ).get_all_entries()
    synced = 0
    for event in events:
        args = event["args"]
        freelancer = args["freelancer"].lower()
        try:
            validate_wallet_address(freelancer)
        except Exception:
            continue
        await upsert_reputation(
            db,
            freelancer,
            gigs_completed=args["gigsCompleted"],
            total_earned=str(args["totalEarned"]),
            average_ai_score=args["averageAiScore"],
        )
        synced += 1
    if synced > 0:
        await db.commit()
    return synced
