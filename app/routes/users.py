from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.routes import auth
from app.database import get_db
from typing import List

router = APIRouter()

@router.post("/nieuw", response_model=schemas.UserOut)
def nieuwe_gebruiker(user: schemas.UserCreate, db: Session = Depends(get_db)):
    bestaande = db.query(models.User).filter(models.User.id == user.id).first()
    if bestaande:
        raise HTTPException(status_code=400, detail="Gebruiker bestaat al")
    nieuw = models.User(id=user.id, itsme_id=user.itsme_id)
    db.add(nieuw)
    db.commit()
    db.refresh(nieuw)
    return nieuw

@router.get("/{user_id}", response_model=schemas.UserOut)
def gebruiker_detail(user_id: str, db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    gebruiker = db.query(models.User).filter(models.User.id == user_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")
    return gebruiker

@router.get("/", response_model=List[schemas.UserOut])
def alle_gebruikers(db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    return db.query(models.User).all()

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_gebruiker(user_id: str, user_update: schemas.UserUpdate, db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    gebruiker = db.query(models.User).filter(models.User.id == user_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")
    gebruiker.itsme_id = user_update.itsme_id
    db.commit()
    db.refresh(gebruiker)
    return gebruiker

@router.delete("/{user_id}")
def verwijder_gebruiker(user_id: str, db: Session = Depends(get_db), _: str = Depends(auth.get_current_user)):
    gebruiker = db.query(models.User).filter(models.User.id == user_id).first()
    if not gebruiker:
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")
    db.delete(gebruiker)
    db.commit()
    return {"status": "verwijderd"}
