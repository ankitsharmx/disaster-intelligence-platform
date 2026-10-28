from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.notification import NotificationSubscription
from app.models.user import User
from app.schemas.notification import SubscriptionCreate, SubscriptionOut, NotificationDispatchTest
from app.api.deps import get_current_user

router = APIRouter(prefix="/notifications", tags=["Push Notifications & Subscriptions"])


@router.post("/subscribe", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
async def subscribe_push_notifications(
    sub_in: SubscriptionCreate,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register or update a browser Web Push subscription with optional district targeting.
    Handles idempotent registration and reactivation of subscriptions.
    """
    res = await db.execute(select(NotificationSubscription).filter_by(endpoint=sub_in.endpoint))
    existing = res.scalar_one_or_none()

    if existing:
        existing.p256dh = sub_in.p256dh
        existing.auth = sub_in.auth
        existing.district_id = sub_in.district_id
        existing.is_active = True
        if current_user:
            existing.user_id = current_user.id
        await db.commit()
        await db.refresh(existing)
        return existing

    new_sub = NotificationSubscription(
        endpoint=sub_in.endpoint,
        p256dh=sub_in.p256dh,
        auth=sub_in.auth,
        district_id=sub_in.district_id,
        user_id=current_user.id if current_user else None,
        is_active=True,
    )
    db.add(new_sub)
    await db.commit()
    await db.refresh(new_sub)
    return new_sub


@router.post("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_push_notifications(
    endpoint: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark a push subscription as inactive or removed."""
    res = await db.execute(select(NotificationSubscription).filter_by(endpoint=endpoint))
    sub = res.scalar_one_or_none()
    if sub:
        sub.is_active = False
        await db.commit()
    return {"message": "Subscription cancelled"}


@router.post("/test-dispatch", status_code=status.HTTP_200_OK)
async def test_dispatch_notification(
    payload: NotificationDispatchTest,
    db: AsyncSession = Depends(get_db),
):
    """
    Simulate dispatch of a targeted push notification to all subscribers in a district.
    Handles reporting of successful recipients vs simulated expired subscriptions.
    """
    res = await db.execute(
        select(NotificationSubscription).filter(
            NotificationSubscription.district_id == payload.district_id,
            NotificationSubscription.is_active == True,
        )
    )
    subscribers = res.scalars().all()
    
    # In a full production setup with VAPID keys, pywebpush delivers payloads to endpoints.
    # Here we record delivery targeting, simulated receipts, and handle expired endpoints.
    delivered_count = 0
    expired_count = 0
    for sub in subscribers:
        if "expired" in sub.endpoint.lower():
            sub.is_active = False
            expired_count += 1
        else:
            delivered_count += 1

    if expired_count > 0:
        await db.commit()

    return {
        "status": "dispatched",
        "district_id": payload.district_id,
        "title": payload.title,
        "targeted_subscribers": len(subscribers),
        "delivered_count": delivered_count,
        "expired_pruned": expired_count,
    }
