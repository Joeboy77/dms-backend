{
  "collections": [
    "userchannels",
    "activity_logs",
    "channels",
    "noticeboards",
    "project_areas",
    "committees",
    "course_registrations",
    "levels",
    "lecturers",
    "messages",
    "communications",
    "modules",
    "courses",
    "complaints",
    "deferments",
    "logins",
    "projects",
    "academic_years",
    "timetables",
    "exam_timetables",
    "categories",
    "fyps",
    "programs",
    "students",
    "non_teachings",
    "fypcheckins",
    "lecturer_project_areas",
    "class_groups",
    "program_courses",
    "chatusers"
  ]
}

polar-waters-58235
heroku container:push web --app polar-waters-58235
heroku container:release web --app polar-waters-58235
heroku logs --tail --app polar-waters-58235