from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from routers import chat, pdf, user
from fastapi.middleware.cors import CORSMiddleware
from database import Session, initialize_db, logger
from fastapi.templating import Jinja2Templates

app = FastAPI()


templates = Jinja2Templates(directory="templates")

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_headers=["*"],
                   allow_methods=["*"], )

app.include_router(chat.router, prefix="/api/bot")
app.include_router(user.router, prefix="/api/users")
app.include_router(pdf.router, prefix="/api/pdf")


@app.get("/pdf-management", response_class=HTMLResponse)
async def admin_dashboard():
    return templates.TemplateResponse("admin_dashboard.html", {"request": {}})


@app.get("/chat", response_class=HTMLResponse)
async def chatbot_dashboard():
    return templates.TemplateResponse("chatbot.html", {"request": {}})


@app.get("/user-management", response_class=HTMLResponse)
async def user_dashboard():
    return templates.TemplateResponse("user_dashboard.html", {"request": {}})


@app.get("/health")
async def health():
    """Check the api is running"""
    return {"status": "😃"}


@app.get("/")
async def read_root():
    return RedirectResponse(url="/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return templates.TemplateResponse("login.html", {"request": {}})


@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    return templates.TemplateResponse("signup.html", {"request": {}})


@app.on_event("startup")
async def startup() -> None:
    logger.info("Starting up the application")
    await initialize_db()


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("Shutting down the application")
    session = Session()
    session.close()
