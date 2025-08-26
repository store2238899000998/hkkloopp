from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
	user_id: int
	name: str
	initial_balance: float = Field(ge=0)


class UserRead(BaseModel):
	user_id: int
	name: str
	initial_balance: float
	current_balance: float
	start_date: datetime
	next_roi_date: datetime | None
	roi_cycles_completed: int
	can_withdraw: bool

	class Config:
		from_attributes = True


class SupportTicketCreate(BaseModel):
	user_id: int
	message: str


class SupportTicketRead(BaseModel):
	ticket_id: str
	user_id: int
	message: str
	created_at: datetime

	class Config:
		from_attributes = True


