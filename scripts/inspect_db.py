from sqlmodel import Session, select, create_engine
from src.database import CallLog  # Importamos tu modelo

# Conectar a la DB
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url)

def show_logs():
    with Session(engine) as session:
        # Consulta SQL: "SELECT * FROM calllog"
        statement = select(CallLog)
        results = session.exec(statement).all()
        
        print(f"\n📊 TOTAL DE REGISTROS: {len(results)}")
        print("="*60)
        print(f"{'ID':<5} | {'ROL':<10} | {'MENSAJE'}")
        print("-" * 60)
        
        for log in results:
            # Cortamos el mensaje si es muy largo para que se vea bien
            msg = (log.content[:50] + '..') if len(log.content) > 50 else log.content
            print(f"{log.id:<5} | {log.role:<10} | {msg}")
        print("="*60 + "\n")

if __name__ == "__main__":
    show_logs()