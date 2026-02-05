from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from sqlmodel import SQLModel, select, Session
from app.database import engine, get_session
from app.models import Message, Project, Admin

import hashlib
import os


# =========================================================
# 🔧 CONFIGURATION DE L’APPLICATION
# =========================================================

app = FastAPI()

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "fallback_secret_key_change_me")
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")
templates_admin = Jinja2Templates(directory="app/admin")


# =========================================================
# 🔐 UTILITAIRES
# =========================================================

def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


# =========================================================
# 🗄️ INITIALISATION DE LA BASE + ADMIN PAR DÉFAUT
# =========================================================

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        admin = session.exec(select(Admin)).first()

        if not admin:
            default_pwd = os.getenv("ADMIN_PASSWORD", "admin")
            admin = Admin(password=hash_password(default_pwd))
            session.add(admin)
            session.commit()


# =========================================================
# 🌍 ROUTES PUBLIQUES
# =========================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/services", response_class=HTMLResponse)
async def services(request: Request):
    return templates.TemplateResponse("services.html", {"request": request})


@app.get("/projets", response_class=HTMLResponse)
async def projets(request: Request, session=Depends(get_session)):
    projects = session.exec(select(Project)).all()
    return templates.TemplateResponse("projets.html", {
        "request": request,
        "projects": projects
    })

@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@app.post("/contact")
async def submit_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    session=Depends(get_session)
):
    new_msg = Message(name=name, email=email, message=message)
    session.add(new_msg)
    session.commit()

    return templates.TemplateResponse("contact.html", {
        "request": request,
        "success": True
    })


@app.get("/apropos", response_class=HTMLResponse)
async def a_propos(request: Request):
    return templates.TemplateResponse("apropos.html", {"request": request})


# =========================================================
# 📄 PAGES LÉGALES
# =========================================================

@app.get("/mentions-legales", response_class=HTMLResponse)
async def mentions_legales(request: Request):
    return templates.TemplateResponse("mentions-legales.html", {"request": request})


@app.get("/cgu", response_class=HTMLResponse)
async def cgu(request: Request):
    return templates.TemplateResponse("cgu.html", {"request": request})


@app.get("/politique-confidentialite", response_class=HTMLResponse)
async def politique_confidentialite(request: Request):
    return templates.TemplateResponse("politique-confidentialite.html", {"request": request})


# =========================================================
# 🔑 LOGIN ADMIN
# =========================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates_admin.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session=Depends(get_session)
):
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin = session.exec(select(Admin)).first()

    if not admin:
        return templates_admin.TemplateResponse("login.html", {
            "request": request,
            "error": True
        })

    if username == admin_username and admin.password == hash_password(password):
        request.session["admin"] = True
        return RedirectResponse("/admin", status_code=302)

    return templates_admin.TemplateResponse("login.html", {
        "request": request,
        "error": True
    })


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)


# =========================================================
# 🖥️ DASHBOARD ADMIN
# =========================================================

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not request.session.get("admin"):
        return RedirectResponse("/login", status_code=302)

    return templates_admin.TemplateResponse("admin.html", {
        "request": request,
        "active": "dashboard",
        "last_login": "Aujourd’hui"
    })


# =========================================================
# ✉️ MESSAGES — LISTE + SUPPRESSION
# =========================================================

@app.get("/admin/messages", response_class=HTMLResponse)
async def admin_messages(request: Request, session=Depends(get_session)):
    if not request.session.get("admin"):
        return RedirectResponse("/login", status_code=302)

    messages = session.exec(select(Message)).all()

    return templates_admin.TemplateResponse("admin-messages.html", {
        "request": request,
        "messages": messages,
        "active": "messages"
    })


@app.post("/admin/messages/delete/{msg_id}")
async def delete_message(msg_id: int, request: Request, session=Depends(get_session)):
    if not request.session.get("admin"):
        return RedirectResponse("/login", status_code=302)

    msg = session.get(Message, msg_id)
    if msg:
        session.delete(msg)
        session.commit()

    return RedirectResponse("/admin/messages", status_code=302)


# =========================================================
# 📁 PROJETS — CRUD COMPLET
# =========================================================

@app.get("/admin/projects", response_class=HTMLResponse)
async def admin_projects(request: Request, session=Depends(get_session)):
    if not request.session.get("admin"):
        return RedirectResponse("/login", status_code=302)

    projects = session.exec(select(Project)).all()

    return templates_admin.TemplateResponse("admin-projects.html", {
        "request": request,
        "projects": projects,
        "active": "projects"
    })


@app.post("/admin/projects/add")
async def add_project(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    link: str = Form(None),
    session=Depends(get_session)
):
    if not request.session.get("admin"):
        return RedirectResponse("/login", status_code=302)

    project = Project(title=title, description=description, link=link)
    session.add(project)
    session.commit()

    return RedirectResponse("/admin/projects", status_code=302)


@app.post("/admin/projects/edit/{project_id}")
async def edit_project(
    project_id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    link: str = Form(None),
    session=Depends(get_session)
):
    if not request.session.get("admin"):
        return RedirectResponse("/login", status_code=302)

    project = session.get(Project, project_id)
    if project:
        project.title = title
        project.description = description
        project.link = link
        session.add(project)
        session.commit()

    return RedirectResponse("/admin/projects", status_code=302)


@app.post("/admin/projects/delete/{project_id}")
async def delete_project(project_id: int, request: Request, session=Depends(get_session)):
    if not request.session.get("admin"):
        return RedirectResponse("/login", status_code=302)

    project = session.get(Project, project_id)
    if project:
        session.delete(project)
        session.commit()

    return RedirectResponse("/admin/projects", status_code=302)


# =========================================================
# ⚙️ PARAMÈTRES — CHANGER MOT DE PASSE
# =========================================================

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    if not request.session.get("admin"):
        return RedirectResponse("/login", status_code=302)

    return templates_admin.TemplateResponse("admin-settings.html", {
        "request": request,
        "active": "settings"
    })


@app.post("/admin/settings")
async def update_password(
    request: Request,
    old_password: str = Form(...),
    new_password: str = Form(...),
    session=Depends(get_session)
):
    if not request.session.get("admin"):
        return RedirectResponse("/login", status_code=302)

    admin = session.exec(select(Admin)).first()

    if admin.password != hash_password(old_password):
        return templates_admin.TemplateResponse("admin-settings.html", {
            "request": request,
            "error": True,
            "active": "settings"
        })

    admin.password = hash_password(new_password)
    session.add(admin)
    session.commit()

    return templates_admin.TemplateResponse("admin-settings.html", {
        "request": request,
        "success": True,
        "active": "settings"
    })
