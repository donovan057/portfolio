from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "sqlite:///app.db"

engine = create_engine(DATABASE_URL, echo=False)

def get_session():
    with Session(engine) as session:
        yield session
