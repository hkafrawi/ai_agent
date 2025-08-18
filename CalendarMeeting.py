from datetime import datetime
from typing import List

class CalendarMeeting:
    def __init__(self, date: datetime, place: str, participants: List[str]):
        self.date = date
        self.place = place
        self.participants = participants

    def __str__(self):
        return f"Date: {self.date}, Place: {self.place}, Participants: {', '.join(self.participants)}"