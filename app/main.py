from fastapi import FastAPI, responses
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import (
    auth,
    logins,
    activity_logs,
    database,
    deliverables,
    fypcheckins,
    fyps,
    groups,
    health,
    lecturer_project_areas,
    lecturers,
    models,
    programs,
    project_areas,
    recent_activities,
    reminders,
    students,
    submissions,
    supervisors,
    complaints,
    academic_years,
    communications,
)
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_TITLE)

origins = ["http://localhost:3000", "http://localhost:3001"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(models.router, prefix=settings.API_V1_STR)
app.include_router(academic_years.router, prefix=settings.API_V1_STR)
app.include_router(database.router, prefix=settings.API_V1_STR)
app.include_router(students.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(logins.router, prefix=settings.API_V1_STR)
app.include_router(activity_logs.router, prefix=settings.API_V1_STR)
app.include_router(recent_activities.router, prefix=settings.API_V1_STR)
app.include_router(reminders.router, prefix=settings.API_V1_STR)
app.include_router(fypcheckins.router, prefix=settings.API_V1_STR)
app.include_router(project_areas.router, prefix=settings.API_V1_STR)
app.include_router(fyps.router, prefix=settings.API_V1_STR)
app.include_router(programs.router, prefix=settings.API_V1_STR)
app.include_router(deliverables.router, prefix=settings.API_V1_STR)
app.include_router(submissions.router, prefix=settings.API_V1_STR)
app.include_router(groups.router, prefix=settings.API_V1_STR)
app.include_router(lecturer_project_areas.router, prefix=settings.API_V1_STR)
app.include_router(lecturers.router, prefix=settings.API_V1_STR)
app.include_router(complaints.router, prefix=settings.API_V1_STR)
app.include_router(supervisors.router, prefix=settings.API_V1_STR)
app.include_router(communications.router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root():
    return responses.RedirectResponse(url="/docs")
# heroku container:push web -a polar-waters-58235