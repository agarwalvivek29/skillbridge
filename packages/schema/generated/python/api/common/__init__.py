# Compatibility shim — betterproto generates `from .common import v1` inside api/v1.py
# which resolves to api.common.v1 (relative import). This module re-exports everything
# from the actual top-level common package so that import succeeds.
