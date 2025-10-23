from fastapi import FastAPI, responses
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import (
    auth,
    # logins,
    activity_logs,
    coordinator_stats,
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
    student_interests,
    submissions,
    supervisors,
    complaints,
    academic_years,
    communications,
    enhanced_supervisor_interests,
)
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_TITLE)

origins = [
    "http://localhost:3000", 
    "http://localhost:3001",
    "https://your-frontend-domain.onrender.com",  # Add your frontend URL here
    "https://your-app-name.onrender.com"  # Add your backend URL here
]
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
app.include_router(student_interests.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
# app.include_router(logins.router, prefix=settings.API_V1_STR)
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
app.include_router(enhanced_supervisor_interests.router, prefix=settings.API_V1_STR)
app.include_router(coordinator_stats.router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
async def root():
    return responses.RedirectResponse(url="/docs")
# heroku container:push web -a polar-waters-58235