from datetime import datetime
from typing import List
from pydantic import BaseModel, Field

class CalendarMeeting(BaseModel):
    date: datetime = Field(..., description="The date and time of the meeting")
    place: str = Field(..., description="The location of the meeting")
    participants: List[str] = Field(..., description="List of participants in the meeting")
