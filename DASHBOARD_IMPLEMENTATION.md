# FYP Dashboard Implementation Guide

## Dashboard Overview

The dashboard displays comprehensive project information for a student, including:
1. **Project Supervisor Information** - Name, area of interest
2. **Project Area & Topic** - Project area details and topic
3. **Project Overview** - Visual progress stepper showing stages (Proposal → Chapter 1-5 → Final Doc)
4. **Project Progress Table** - List of deliverables with deadlines and status
5. **Calendar** - Highlighted dates from reminders and deadlines
6. **Reminders** - Upcoming events and deadlines

## Data Flow

```
Student ID (academicId or ObjectId)
    ↓
1. Get FYP by Student ID
    ├─→ FYP contains: student, supervisor, projectArea, checkin
    ↓
2. Populate Related Data
    ├─→ Supervisor (from lecturers collection)
    ├─→ Project Area (from project_areas collection)
    ├─→ Student Details (from students collection)
    ↓
3. Get Deliverables for Student
    ├─→ Query deliverables by supervisor_id
    ├─→ Filter by student_ids containing this student
    ├─→ Get submission status for each deliverable
    ↓
4. Calculate Project Progress
    ├─→ Map deliverables to stages (Proposal, Chapter 1-5, Final Doc)
    ├─→ Determine status: Completed, In Progress, Not Started
    ├─→ Calculate completion percentage
    ├─→ Find next submission deadline
    ↓
5. Get Reminders & Calendar Events
    ├─→ Get upcoming reminders
    ├─→ Extract dates from deliverables (deadlines)
    ├─→ Combine for calendar view
    ↓
6. Return Aggregated Dashboard Data
```

## Implementation Steps

### Step 1: Create Dashboard Schema
- Define response model with all dashboard sections
- Include nested models for supervisor, project area, deliverables, reminders

### Step 2: Add Dashboard Method to FypController
- Create `get_dashboard_by_student()` method
- Aggregate data from multiple collections
- Calculate progress metrics

### Step 3: Create Dashboard Route
- Add `/fyps/dashboard/{student_id}` endpoint
- Return structured dashboard data

### Step 4: Status Calculation Logic
- **Completed**: Submission exists and deliverable end_date has passed
- **In Progress**: Submission exists but end_date hasn't passed, OR no submission but current date is between start_date and end_date
- **Not Started**: No submission and current date is before start_date

### Step 5: Progress Calculation
- Count completed deliverables
- Map to project stages
- Calculate percentage: (completed_stages / total_stages) * 100

## Data Relationships

```
FYP
├─ student (ObjectId → students)
├─ supervisor (ObjectId → lecturers)
├─ projectArea (ObjectId → project_areas)
└─ checkin (ObjectId → fypcheckins)

Deliverables
├─ supervisor_id (ObjectId → supervisors → lecturers)
├─ student_ids (Array[ObjectId] → students)
├─ start_date, end_date
└─ name (e.g., "Project Proposal", "Chapter 1")

Submissions
├─ deliverable_id (ObjectId → deliverables)
├─ student_id (ObjectId → students)
└─ submitted_at

Reminders
├─ title
├─ date_time
└─ (potentially linked to student_id or fyp_id)
```

## Key Implementation Details

### 1. Deliverable Status Mapping
Map deliverable names to project stages:
- "Project Proposal" → Proposal stage
- "Chapter 1", "Submission of Chapter 1" → Chapter 1
- "Chapter 2", "Submission of Chapter 2" → Chapter 2
- etc.

### 2. Next Deadline Calculation
Find the earliest upcoming deadline from:
- Deliverables with end_date > current_date and status != "Completed"
- Reminders with date_time > current_date

### 3. Calendar Dates
Extract dates from:
- Deliverable deadlines (end_date)
- Reminder dates (date_time)
- Highlight based on proximity to current date

### 4. Project Completion Percentage
Formula:
```
completed_stages = count of stages with "Completed" status
total_stages = 7 (Proposal + 5 Chapters + Final Doc)
completion = (completed_stages / total_stages) * 100
```

## API Endpoint Structure

```
GET /api/v1/fyps/dashboard/{student_id}

Response:
{
  "supervisor": {
    "name": "Dr. Mark Atta-Mensah",
    "academicId": "...",
    "areaOfInterest": "Software Engineering",
    "email": "..."
  },
  "projectArea": {
    "title": "Data Science & Big Data Analytics",
    "description": "...",
    "topic": "Eye Sensor"  // This might need to be added to FYP model
  },
  "projectOverview": {
    "stages": [
      {
        "name": "Proposal",
        "status": "completed",
        "completed": true
      },
      {
        "name": "Chapter 1",
        "status": "in_progress",
        "completed": false
      },
      // ... more stages
    ],
    "completionPercentage": 14.3,
    "nextDeadline": "2023-11-23T00:00:00"
  },
  "projectProgress": [
    {
      "name": "Project Proposal",
      "deadline": "2023-11-20T00:00:00",
      "status": "Completed"
    },
    // ... more deliverables
  ],
  "calendar": {
    "highlightedDates": ["2023-11-03", "2023-11-14", ...],
    "month": 11,
    "year": 2023
  },
  "reminders": [
    {
      "title": "Preview Chapter 1 Before Deadline",
      "date": "2023-11-14T07:30:00",
      "formatted": "14 NOV: Preview Chapter 1 Before Deadline, Tuesday, 7:30 am"
    },
    // ... more reminders
  ]
}
```

