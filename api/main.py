from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session, init_db
from app.schemas import UserCreate, UserRead, SupportTicketCreate, SupportTicketRead
from app.services import create_user, create_support_ticket, list_support_tickets
from scheduler.jobs import catchup_missed_roi


app = FastAPI(title="InvestmentBot API")


@app.on_event("startup")
def on_startup():
	init_db()


# Dependency for FastAPI to use SQLAlchemy session per-request

def session_dep():
	with get_session() as session:
		yield session


@app.get("/health")
def health():
	return {"status": "ok"}


@app.post("/admin/users", response_model=UserRead)
def admin_create_user(payload: UserCreate, session: Session = Depends(session_dep)):
	user = create_user(session, user_id=payload.user_id, name=payload.name, initial_balance=payload.initial_balance)
	return user


@app.post("/support", response_model=SupportTicketRead)
def create_ticket(payload: SupportTicketCreate, session: Session = Depends(session_dep)):
	# Accepts tickets from bots or external clients
	ticket = create_support_ticket(session, user_id=payload.user_id, message=payload.message)
	return ticket


@app.get("/admin/tickets", response_model=list[SupportTicketRead])
def admin_list_tickets(session: Session = Depends(session_dep)):
	return list_support_tickets(session)


@app.post("/admin/recovery/catchup-roi")
async def admin_catchup_roi():
	"""Admin endpoint to manually trigger ROI catch-up"""
	try:
		processed_users, total_payments = await catchup_missed_roi()
		return {
			"success": True,
			"message": f"ROI catch-up completed successfully",
			"processed_users": processed_users,
			"total_payments": total_payments,
			"timestamp": datetime.utcnow().isoformat()
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"ROI catch-up failed: {str(e)}")


@app.get("/admin/recovery/status")
def admin_recovery_status(session: Session = Depends(session_dep)):
	"""Get system recovery status and health"""
	from app.services import list_users, get_user_roi_status
	
	try:
		users = list_users(session)
		user_statuses = []
		
		for user in users:
			status = get_user_roi_status(user)
			user_statuses.append(status)
		
		# Calculate summary statistics
		total_users = len(users)
		active_roi_users = len([u for u in user_statuses if u["roi_cycles_completed"] > 0])
		completed_users = len([u for u in user_statuses if u["roi_cycles_completed"] >= u["max_cycles"]])
		pending_users = total_users - active_roi_users - completed_users
		
		return {
			"system_health": "healthy",
			"total_users": total_users,
			"active_roi_users": active_roi_users,
			"completed_users": completed_users,
			"pending_users": pending_users,
			"user_details": user_statuses,
			"timestamp": datetime.utcnow().isoformat()
		}
		
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to get recovery status: {str(e)}")


# Add missing import
from datetime import datetime


