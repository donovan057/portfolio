from sqlmodel import SQLModel, Field
from datetime import datetime

class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str
    message: str
    date: str = datetime.now().strftime("%d/%m/%Y %H:%M")

class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str
    link: str | None = None

class Admin(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    password: str
