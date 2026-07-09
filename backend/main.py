from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURATION & SECRETS
# ==========================================
SECRET_KEY = "your-super-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Email configuration (Use a Gmail App Password or an SMTP service like SendGrid)
SMTP_SERVER = "smtp.gmail.com" # Example using Gmail SMTP
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("SMTP") # Replace with your sender email
SMTP_PASSWORD = os.getenv("SMTP_PASS")    # Replace with your app password
DESTINATION_EMAIL = "sivijay@proton.me"

load_dotenv()
# ==========================================
# 2. DATABASE SETUP (SQLite for simplicity)
# ==========================================
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

SQLALCHEMY_DATABASE_URL = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?sslmode=require"
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 3. SECURITY & SCHEMAS
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Pydantic Schemas for validation matching your frontend forms
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ==========================================
# 4. APP INITIALIZATION & CORS
# ==========================================
app = FastAPI(title="SynergyApp Backend")

# Allow your Vercel frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", # Vite local dev server
        "https://synergy-app-two.vercel.app/" # Your deployed app
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 5. EMAIL SENDING LOGIC
# ==========================================
def send_email_background(contact: ContactForm):
    """Sends email in the background so the API doesn't hang."""
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = DESTINATION_EMAIL
    msg['Subject'] = f"SynergyApp Portfolio: {contact.subject}"

    body = f"""
    New message from your SynergyApp Website!
    
    Name: {contact.name}
    Email: {contact.email}
    Subject: {contact.subject}
    
    Message:
    {contact.message}
    """
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_USERNAME, DESTINATION_EMAIL, text)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")

# ==========================================
# 6. API ROUTES
# ==========================================

@app.post("/auth/signup", response_model=Token)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_pw = get_password_hash(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm expects 'username' and 'password' fields.
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/contact/send")
def send_contact_email(contact: ContactForm, background_tasks: BackgroundTasks):
    # Adds the email sending task to a background queue so the user gets an instant success response
    background_tasks.add_task(send_email_background, contact)
    return {"message": "Email is being sent!"}
