from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
from .database import Base

class TicketStatus(str, enum.Enum):
    ingediend = "ingediend"
    beantwoord = "beantwoord"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    itsme_id = Column(String, unique=True, index=True)
    registratie_datum = Column(DateTime, default=datetime.utcnow)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(String, primary_key=True, index=True)
    gebruiker_id = Column(String, ForeignKey("users.id"))
    vraagtekst = Column(Text)
    status = Column(Enum(TicketStatus), default=TicketStatus.ingediend)
    aanmaakdatum = Column(DateTime, default=datetime.utcnow)
    gelezen = Column(Boolean, default=False)
    annotatie = Column(Text, nullable=True)

    gebruiker = relationship("User")
    antwoord = relationship("Antwoord", uselist=False, back_populates="ticket")
    bijlagen = relationship("Attachment", back_populates="ticket")

class Antwoord(Base):
    __tablename__ = "antwoorden"
    id = Column(String, primary_key=True, index=True)
    vraag_id = Column(String, ForeignKey("tickets.id"))
    antwoordtekst = Column(Text)
    verzend_datum = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="antwoord")

class Attachment(Base):
    __tablename__ = "bijlagen"
    id = Column(String, primary_key=True, index=True)
    vraag_id = Column(String, ForeignKey("tickets.id"))
    bestandsnaam = Column(String)
    bestandspad = Column(String)
    upload_datum = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="bijlagen")

class ActieLog(Base):
    __tablename__ = "actielog"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    pad = Column(String)
    methode = Column(String)
    tijdstip = Column(DateTime, default=datetime.utcnow)
    ip = Column(String)
    user_agent = Column(String)
