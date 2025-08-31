from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.api_v1.endpoints.auth import get_current_active_user
from app.schemas.user import User as UserSchema
from app.schemas.visit import (
    VisitCreate, VisitUpdate, Visit, VisitList, VisitReschedule, VisitCancel, VisitSlice
)
from app.services.visit import (
    create_visit, get_visit, get_user_visits, update_visit,
    cancel_visit, reschedule_visit
)

router = APIRouter()

@router.post("/", response_model=Visit)
async def schedule_visit(
    visit: VisitCreate,
    current_user: UserSchema = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await create_visit(db, current_user.id, visit)

@router.get("/", response_model=VisitList)
async def get_my_visits(
    current_user: UserSchema = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_user_visits(db, current_user.id)

@router.get("/upcoming/", response_model=VisitSlice)
async def get_upcoming_visits(
    current_user: UserSchema = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.visit import get_user_upcoming_visits
    return await get_user_upcoming_visits(db, current_user.id)

@router.get("/past/", response_model=VisitSlice)
async def get_past_visits(
    current_user: UserSchema = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.visit import get_user_past_visits
    return await get_user_past_visits(db, current_user.id)

@router.get("/{visit_id}", response_model=Visit)
async def get_visit_details(
    visit_id: int,
    current_user: UserSchema = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    visit = await get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    # Check if visit belongs to current user
    if visit.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return visit

@router.put("/{visit_id}", response_model=Visit)
async def update_visit_details(
    visit_id: int,
    visit_update: VisitUpdate,
    current_user: UserSchema = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    visit = await get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    # Check if visit belongs to current user
    if visit.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await update_visit(db, visit_id, visit_update)

@router.post("/{visit_id}/reschedule", response_model=Visit)
async def reschedule_visit_date(
    visit_id: int,
    reschedule_data: VisitReschedule,
    current_user: UserSchema = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    visit = await get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    # Check if visit belongs to current user
    if visit.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    updated = await reschedule_visit(db, visit_id, reschedule_data.new_date, reschedule_data.reason)
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to reschedule visit")
    return updated

@router.post("/{visit_id}/cancel", response_model=Visit)
async def cancel_visit_request(
    visit_id: int,
    cancel_data: VisitCancel,
    current_user: UserSchema = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    visit = await get_visit(db, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    
    # Check if visit belongs to current user
    if visit.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    updated = await cancel_visit(db, visit_id, cancel_data.reason)
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to cancel visit")
    return updated
