from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TicketStatus(str, Enum):
    ingediend = "ingediend"
    beantwoord = "beantwoord"

class TicketCreate(BaseModel):
    gebruiker_id: str
    vraagtekst: str

class TicketOut(BaseModel):
    id: str
    gebruiker_id: str
    vraagtekst: str
    status: TicketStatus
    aanmaakdatum: datetime
    gelezen: bool
    annotatie: Optional[str] = None

    class Config:
        orm_mode = True

class AntwoordCreate(BaseModel):
    vraag_id: str
    antwoordtekst: str

class AntwoordOut(BaseModel):
    id: str
    vraag_id: str
    antwoordtekst: str
    verzend_datum: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginData(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    id: str
    itsme_id: str

class UserOut(BaseModel):
    id: str
    itsme_id: str
    registratie_datum: datetime

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    itsme_id: str

class TicketUpdateLezen(BaseModel):
    gelezen: bool

class TicketAnnotatie(BaseModel):
    annotatie: str
