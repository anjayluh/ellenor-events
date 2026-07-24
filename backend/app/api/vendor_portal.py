from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import CurrentUser, get_current_user, get_project_membership, membership_role
from app.core.permissions import VENDORS_MANAGE_PERMISSION, PROJECT_ADMIN_ROLES, require_permission
from app.db.session import get_db
from app.models.vendor_portal import VendorBooking, VendorPayment, VendorPortfolioItem, VendorProfile
from app.schemas.vendor_portal import (
    VendorBookingCreate,
    VendorBookingRead,
    VendorBookingUpdate,
    VendorPaymentCreate,
    VendorPaymentRead,
    VendorPortfolioCreate,
    VendorPortfolioRead,
    VendorProfileRead,
    VendorProfileUpsert,
)
from app.services.audit_service import write_audit_log

router = APIRouter()


def get_vendor_profile_or_404(db: Session, user_id: UUID) -> VendorProfile:
    profile = db.query(VendorProfile).filter(VendorProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")
    return profile


def get_booking_or_404(db: Session, booking_id: UUID) -> VendorBooking:
    booking = db.query(VendorBooking).filter(VendorBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor booking not found")
    return booking


@router.get("/marketplace", response_model=list[VendorProfileRead])
def list_vendor_marketplace(category: str | None = None, db: Session = Depends(get_db)):
    query = db.query(VendorProfile).filter(VendorProfile.status == "active")
    if category:
        query = query.filter(VendorProfile.category == category)
    return query.order_by(VendorProfile.business_name.asc()).all()


@router.get("/marketplace/{vendor_user_id}/portfolio", response_model=list[VendorPortfolioRead])
def vendor_marketplace_portfolio(vendor_user_id: UUID, db: Session = Depends(get_db)):
    get_vendor_profile_or_404(db, vendor_user_id)
    return db.query(VendorPortfolioItem).filter(VendorPortfolioItem.vendor_user_id == vendor_user_id).order_by(VendorPortfolioItem.created_at.desc()).all()


@router.get("/portal/profile", response_model=VendorProfileRead)
def get_my_vendor_profile(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_vendor_profile_or_404(db, current_user.id)


@router.put("/portal/profile", response_model=VendorProfileRead)
def upsert_my_vendor_profile(payload: VendorProfileUpsert, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(VendorProfile).filter(VendorProfile.user_id == current_user.id).first()
    if not profile:
        profile = VendorProfile(user_id=current_user.id, **payload.model_dump())
        db.add(profile)
    else:
        for field, value in payload.model_dump().items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now(timezone.utc)
    write_audit_log(db, "vendor.profile_upserted", actor_user_id=current_user.id)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/portal/portfolio", response_model=list[VendorPortfolioRead])
def list_my_portfolio(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    get_vendor_profile_or_404(db, current_user.id)
    return db.query(VendorPortfolioItem).filter(VendorPortfolioItem.vendor_user_id == current_user.id).order_by(VendorPortfolioItem.created_at.desc()).all()


@router.post("/portal/portfolio", response_model=VendorPortfolioRead)
def create_my_portfolio_item(payload: VendorPortfolioCreate, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    get_vendor_profile_or_404(db, current_user.id)
    item = VendorPortfolioItem(vendor_user_id=current_user.id, **payload.model_dump())
    db.add(item)
    write_audit_log(db, "vendor.portfolio_created", actor_user_id=current_user.id)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/portal/portfolio/{item_id}")
def delete_my_portfolio_item(item_id: UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(VendorPortfolioItem).filter(VendorPortfolioItem.id == item_id, VendorPortfolioItem.vendor_user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio item not found")
    db.delete(item)
    write_audit_log(db, "vendor.portfolio_deleted", actor_user_id=current_user.id, metadata={"item_id": str(item_id)})
    db.commit()
    return {"status": "deleted"}


@router.get("/portal/bookings", response_model=list[VendorBookingRead])
def list_my_vendor_bookings(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    get_vendor_profile_or_404(db, current_user.id)
    return db.query(VendorBooking).filter(VendorBooking.vendor_user_id == current_user.id).order_by(VendorBooking.created_at.desc()).all()


@router.patch("/portal/bookings/{booking_id}", response_model=VendorBookingRead)
def update_my_vendor_booking(booking_id: UUID, payload: VendorBookingUpdate, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = get_booking_or_404(db, booking_id)
    if booking.vendor_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor booking access required")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(booking, field, value)
    booking.updated_at = datetime.now(timezone.utc)
    write_audit_log(db, "vendor.booking_updated", actor_user_id=current_user.id, project_id=booking.project_id, metadata={"booking_id": str(booking_id)})
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/portal/bookings/{booking_id}/payments", response_model=list[VendorPaymentRead])
def list_vendor_payments(booking_id: UUID, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = get_booking_or_404(db, booking_id)
    if booking.vendor_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor booking access required")
    return db.query(VendorPayment).filter(VendorPayment.booking_id == booking_id).order_by(VendorPayment.created_at.desc()).all()


@router.post("/portal/bookings/{booking_id}/payments", response_model=VendorPaymentRead)
def create_vendor_payment(booking_id: UUID, payload: VendorPaymentCreate, current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = get_booking_or_404(db, booking_id)
    if booking.vendor_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vendor booking access required")
    payment = VendorPayment(booking_id=booking_id, **payload.model_dump())
    db.add(payment)
    write_audit_log(db, "vendor.payment_recorded", actor_user_id=current_user.id, project_id=booking.project_id, metadata={"booking_id": str(booking_id)})
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/projects/{project_id}/bookings", response_model=list[VendorBookingRead])
def list_project_vendor_bookings(project_id: UUID, membership=Depends(get_project_membership), db: Session = Depends(get_db)):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, VENDORS_MANAGE_PERMISSION)
    return db.query(VendorBooking).filter(VendorBooking.project_id == project_id).order_by(VendorBooking.created_at.desc()).all()


@router.post("/projects/{project_id}/bookings", response_model=VendorBookingRead)
def create_project_vendor_booking(
    project_id: UUID,
    payload: VendorBookingCreate,
    current_user: CurrentUser = Depends(get_current_user),
    membership=Depends(get_project_membership),
    db: Session = Depends(get_db),
):
    require_permission(membership_role(membership), getattr(membership, "permissions_json", None), PROJECT_ADMIN_ROLES, VENDORS_MANAGE_PERMISSION)
    get_vendor_profile_or_404(db, payload.vendor_user_id)
    booking = VendorBooking(project_id=project_id, requested_by=current_user.id, **payload.model_dump())
    db.add(booking)
    write_audit_log(db, "vendor.booking_requested", actor_user_id=current_user.id, project_id=project_id, metadata={"vendor_user_id": str(payload.vendor_user_id)})
    db.commit()
    db.refresh(booking)
    return booking
