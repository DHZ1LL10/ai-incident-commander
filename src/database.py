from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
from datetime import datetime

# Definicion del modelo de datos (Tabla)
class CallLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    call_id: str = Field(index=True)
    role: str  # "user", "ai" o "ai_tool"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Configuracion de SQLite
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# check_same_thread=False es necesario para SQLite con FastAPI
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    """Inicializa las tablas en la base de datos."""
    SQLModel.metadata.create_all(engine)

def save_log(call_id: str, role: str, content: str):
    """Guarda una entrada en el historial de llamadas."""
    with Session(engine) as session:
        log = CallLog(call_id=call_id, role=role, content=content)
        session.add(log)
        session.commit()
        # Log en consola para depuracion
        print(f"[BASE DE DATOS] Guardado registro: [{role}]")