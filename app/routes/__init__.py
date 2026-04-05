from app.routes.auth import router as auth_router
from app.routes.attendances import router as attendances_router
from app.routes.companies import router as companies_router
from app.routes.exams import router as exams_router
from app.routes.reports import router as reports_router

__all__ = [
    "auth_router",
    "attendances_router",
    "companies_router",
    "exams_router",
    "reports_router",
]
