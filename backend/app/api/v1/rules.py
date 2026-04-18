from __future__ import annotations
"""API endpoints for Pro+ users managing sync filtering rules."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.models.sync import SyncRule
from app.db.models.user import User

router = APIRouter(tags=["rules"])


class RuleCreate(BaseModel):
    name: str
    direction: str
    conditions: dict
    actions: dict
    rule_order: int = 0
    is_active: bool = True


@router.get("")
async def list_rules(
    user: User = Depends(deps.get_current_user),
    _tier: None = Depends(deps.require_tier("pro")),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, Any]:
    """List all sync rules for the current user."""
    stmt = (
        select(SyncRule)
        .where(SyncRule.user_id == user.id)
        .order_by(SyncRule.rule_order.asc())
    )
    result = await db.execute(stmt)
    rules = result.scalars().all()

    return {
        "data": [
            {
                "id": str(r.id),
                "name": r.name,
                "is_active": r.is_active,
                "direction": r.direction,
                "rule_order": r.rule_order,
                "conditions": r.conditions,
                "actions": r.actions,
            }
            for r in rules
        ]
    }


@router.post("")
async def create_rule(
    payload: RuleCreate,
    user: User = Depends(deps.get_current_user),
    _tier: None = Depends(deps.require_tier("pro")),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, Any]:
    """Create a new sync filtering rule."""
    if payload.direction not in ("komoot_to_strava", "strava_to_komoot", "both"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid direction.")
        
    stmt = select(SyncRule).where(SyncRule.user_id == user.id)
    result = await db.execute(stmt)
    existing_rules = result.scalars().all()
    
    if len(existing_rules) >= 15:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Maximum of 15 rules allowed.")

    new_rule = SyncRule(
        user_id=user.id,
        name=payload.name,
        direction=payload.direction,
        conditions=payload.conditions,
        actions=payload.actions,
        rule_order=payload.rule_order,
        is_active=payload.is_active,
    )
    db.add(new_rule)
    await db.commit()

    return {"status": "success", "id": str(new_rule.id)}


@router.put("/{rule_id}")
async def update_rule(
    rule_id: str,
    payload: RuleCreate,
    user: User = Depends(deps.get_current_user),
    _tier: None = Depends(deps.require_tier("pro")),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, Any]:
    """Update an existing sync rule."""
    if payload.direction not in ("komoot_to_strava", "strava_to_komoot", "both"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid direction.")

    result = await db.execute(
        select(SyncRule).where(SyncRule.id == rule_id, SyncRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found.")

    rule.name = payload.name
    rule.direction = payload.direction
    rule.conditions = payload.conditions
    rule.actions = payload.actions
    rule.rule_order = payload.rule_order
    rule.is_active = payload.is_active
    await db.commit()

    return {"status": "success", "id": str(rule.id)}


@router.delete("/{rule_id}")
async def delete_rule(
    rule_id: str,
    user: User = Depends(deps.get_current_user),
    _tier: None = Depends(deps.require_tier("pro")),
    db: AsyncSession = Depends(deps.get_db),
) -> dict[str, str]:
    """Delete an existing sync rule."""
    result = await db.execute(
        select(SyncRule).where(SyncRule.id == rule_id, SyncRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found.")

    await db.delete(rule)
    await db.commit()
    return {"status": "success"}
