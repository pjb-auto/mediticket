from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import uuid
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from io import StringIO
import csv
from typing import List
import os

from app import models, schemas
from app.routes import auth
from app.database import get_db
from fastapi_utils.tasks import repeat_every

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

# Mailconfiguratie uit .env
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)
mail = FastMail(conf)

router = APIRouter()
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
TOEGESTANE_FORMATEN = {"image/jpeg", "image/png", "application/pdf", "text/plain"}


@router.post("/nieuw", response_model=schemas.TicketOut)
def nieuw_ticket(ticket: schemas.TicketCreate, db: Session = Depends(get_db)):
    ticket_id = str(uuid.uuid4())
    db_ticket = models.Ticket(
        id=ticket_id,
        gebruiker_id=ticket.gebruiker_id,
        vraagtekst=ticket.vraagtekst
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)

    # E-mailnotificatie zonder inhoud
    try:
        bericht = MessageSchema(
            subject="Nieuw medisch ticket ingediend",
            recipients=[ticket.gebruiker_id],  # ← eventueel vast e-mailadres hier
            body="Uw vraag werd geregistreerd. U ontvangt later een antwoord via de applicatie.",
            subtype="plain"
        )
        mail.send_message(bericht)
    except Exception as fout:
        print(f"❗ E-mailverzending mislukt: {fout}")

    return db_ticket


@router.post("/{ticket_id}/upload")
def upload_bijlage(ticket_id: str, bestand: UploadFile = File(...), db: Session = Depends(get_db)):
    if bestand.content_type not in TOEGESTANE_FORMATEN:
        raise HTTPException(status_code=400, detail="Bestandstype niet toegestaan")
    bijlage_id = str(uuid.uuid4())
    bestandspad = UPLOAD_DIR / f"{bijlage_id}_{bestand.filename}"
    with open(bestandspad, "wb") as buffer:
        shutil.copyfileobj(bestand.file, buffer)
    bijlage = models.Attachment(
        id=bijlage_id,
        vraag_id=ticket_id,
        bestandsnaam=bestand.filename,
        bestandspad=str(bestandspad)
    )
    db.add(bijlage)
    db.commit()
    return {"bijlage_id": bijlage_id, "bestandspad": str(bestandspad)}


@router.get("/{ticket_id}/bijlagen/{bijlage_id}")
def download_bijlage(ticket_id: str, bijlage_id: str, db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    bijlage = db.query(models.Attachment).filter(models.Attachment.id == bijlage_id, models.Attachment.vraag_id == ticket_id).first()
    if not bijlage:
        raise HTTPException(status_code=404, detail="Bijlage niet gevonden")
    return FileResponse(path=bijlage.bestandspad, filename=bijlage.bestandsnaam)


@router.post("/antwoord")
def beantwoord_ticket(data: schemas.AntwoordCreate, db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    antwoord_id = str(uuid.uuid4())
    antwoord = models.Antwoord(
        id=antwoord_id,
        vraag_id=data.vraag_id,
        antwoordtekst=data.antwoordtekst
    )
    db.add(antwoord)
    ticket = db.query(models.Ticket).filter(models.Ticket.id == data.vraag_id).first()
    if ticket:
        ticket.status = models.TicketStatus.beantwoord
    db.commit()
    return {"antwoord_id": antwoord_id, "status": "beantwoord"}


@router.get("/onbeantwoord", response_model=List[schemas.TicketOut])
def lijst_onbeantwoord(db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    return db.query(models.Ticket).filter(models.Ticket.status == models.TicketStatus.ingediend).all()


@router.get("/{ticket_id}", response_model=schemas.TicketOut)
def ticket_detail(ticket_id: str, db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket niet gevonden")
    return ticket


@router.get("/", response_model=List[schemas.TicketOut])
def alle_tickets(db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    return db.query(models.Ticket).order_by(models.Ticket.aanmaakdatum.desc()).all()


@router.get("/gebruiker/{user_id}", response_model=List[schemas.TicketOut])
def tickets_per_gebruiker(user_id: str, db: Session = Depends(get_db)):
    return db.query(models.Ticket).filter(models.Ticket.gebruiker_id == user_id).order_by(models.Ticket.aanmaakdatum.desc()).all()


@router.on_event("startup")
@repeat_every(seconds=86400)
def archiveer_inactieve_tickets():
    db = next(get_db())
    grens = datetime.utcnow() - timedelta(days=30)
    tickets = db.query(models.Ticket).filter(models.Ticket.status == models.TicketStatus.ingediend, models.Ticket.aanmaakdatum < grens).all()
    for t in tickets:
        t.status = models.TicketStatus.beantwoord
    db.commit()


@router.get("/export", response_class=StreamingResponse)
def exporteer_tickets(db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Gebruiker", "Vraag", "Status", "Datum", "Gelezen", "Annotatie"])
    for t in db.query(models.Ticket).all():
        writer.writerow([t.id, t.gebruiker_id, t.vraagtekst, t.status, t.aanmaakdatum, t.gelezen, t.annotatie])
    output.seek(0)
    return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=tickets.csv"})


@router.get("/dashboard")
def dashboard_data(db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    totaal = db.query(models.Ticket).count()
    open_tickets = db.query(models.Ticket).filter(models.Ticket.status == models.TicketStatus.ingediend).count()
    beantwoord = db.query(models.Ticket).filter(models.Ticket.status == models.TicketStatus.beantwoord).count()
    laatste = db.query(models.Ticket).order_by(models.Ticket.aanmaakdatum.desc()).limit(5).all()
    return {
        "totaal_tickets": totaal,
        "open": open_tickets,
        "beantwoord": beantwoord,
        "laatste_5": [
            {"id": t.id, "datum": t.aanmaakdatum, "vraag": t.vraagtekst[:50]} for t in laatste
        ]
    }


@router.post("/{ticket_id}/gelezen")
def markeer_gelezen(ticket_id: str, data: schemas.TicketUpdateLezen, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket niet gevonden")
    ticket.gelezen = data.gelezen
    db.commit()
    return {"status": "bijgewerkt"}


@router.post("/{ticket_id}/annotatie")
def voeg_annotatie_toe(ticket_id: str, data: schemas.TicketAnnotatie, db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket niet gevonden")
    ticket.annotatie = data.annotatie
    db.commit()
    return {"status": "annotatie toegevoegd"}
