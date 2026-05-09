import os
import json
from sqlalchemy import create_engine, Column, String, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from .models import SessionState, LeadFields

DB_PATH = os.path.join(os.path.dirname(__file__), "state.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class SessionModel(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    language = Column(String)
    history = Column(Text)
    fields = Column(Text)
    complete = Column(Boolean)

def init_db():
    # Creates the tables if they don't exist
    Base.metadata.create_all(bind=engine)

def get_session(session_id: str) -> SessionState:
    db = SessionLocal()
    try:
        db_session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        if db_session:
            return SessionState(
                session_id=session_id,
                language=db_session.language,
                history=json.loads(db_session.history),
                fields=LeadFields.model_validate_json(db_session.fields),
                complete=db_session.complete
            )
        return SessionState(session_id=session_id)
    finally:
        db.close()

def save_session(state: SessionState):
    db = SessionLocal()
    try:
        db_session = db.query(SessionModel).filter(SessionModel.session_id == state.session_id).first()
        if db_session:
            db_session.language = state.language
            db_session.history = json.dumps(state.history)
            db_session.fields = state.fields.model_dump_json()
            db_session.complete = state.complete
        else:
            new_session = SessionModel(
                session_id=state.session_id,
                language=state.language,
                history=json.dumps(state.history),
                fields=state.fields.model_dump_json(),
                complete=state.complete
            )
            db.add(new_session)
        db.commit()
    finally:
        db.close()
