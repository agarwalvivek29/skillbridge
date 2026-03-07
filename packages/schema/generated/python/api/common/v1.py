# Compatibility shim — re-exports all symbols from the real common/v1.py module.
# Betterproto bug: generates `from .common import v1` (relative) instead of
# `from common import v1` (absolute). This shim file makes api.common.v1 == common.v1.
from common.v1 import *  # noqa: F401, F403
