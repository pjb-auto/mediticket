from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routes import tickets, auth, users
from app.database import engine, Base, get_db
from app.models import ActieLog
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Database starten
Base.metadata.create_all(bind=engine)

# Rate limiter configureren
limiter = Limiter(key_func=get_remote_address)

# Logging configureren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mediticket")

# FastAPI app
app = FastAPI()
app.state.limiter = limiter

# Rate limit handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(status_code=429, content={"detail": "Te veel verzoeken, probeer later opnieuw."})

# Middleware: logging + audit trail
@app.middleware("http")
async def combined_logging(request: Request, call_next):
    ip = request.client.host
    agent = request.headers.get("user-agent", "onbekend")
    logger.info(f"📥 Verzoek van IP: {ip} - User-Agent: {agent} - URL: {request.url}")

    response = await call_next(request)

    # Actie loggen in database (zonder falen bij fout)
    try:
        db: Session = next(get_db())
        log = ActieLog(
            pad=request.url.path,
            methode=request.method,
            tijdstip=datetime.utcnow(),
            ip=ip,
            user_agent=agent
        )
        db.add(log)
        db.commit()
    except:
        pass

    return response

# Routes toevoegen
app.include_router(tickets.router, prefix="/tickets", tags=["Tickets"])
app.include_router(auth.router, prefix="/auth", tags=["Authenticatie"])
app.include_router(users.router, prefix="/gebruikers", tags=["Gebruikers"])
