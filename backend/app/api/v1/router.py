from __future__ import annotations
"""API v1 root router."""

from fastapi import APIRouter

from app.api.v1 import auth, sync

router = APIRouter()

router.include_router(auth.router, prefix="/auth")
router.include_router(sync.router, prefix="/sync")

from app.api.v1 import activities, api_keys, billing, rules, webhooks

router.include_router(activities.router, prefix="/activities")
router.include_router(billing.router, prefix="/billing")
router.include_router(webhooks.router, prefix="/webhooks")
router.include_router(api_keys.router, prefix="/api-keys")
router.include_router(rules.router, prefix="/rules")

# Sub-routers below will be enabled as they are implemented in phase 3 blocks:
# router.include_router(routes.router, prefix="/routes")
# router.include_router(billing.router, prefix="/billing")
# router.include_router(api_keys.router, prefix="/api-keys")
# router.include_router(billing.router, prefix="/billing")
# router.include_router(api_keys.router, prefix="/api-keys")
