from __future__ import annotations

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session, init_db
from app.schemas import UserCreate, UserRead, SupportTicketCreate, SupportTicketRead
from app.services import create_user, create_support_ticket, list_support_tickets


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


