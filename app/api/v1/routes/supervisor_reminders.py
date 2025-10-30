from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.core.authentication.auth_middleware import get_current_token, RoleBasedAccessControl, TokenData

router = APIRouter(tags=["Supervisor Reminders"])

require_supervisor = RoleBasedAccessControl(["projects_supervisor", "projects_coordinator"])


@router.get("/supervisor/reminders")
async def get_supervisor_reminders(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: TokenData = Depends(require_supervisor)
):
    """
    Get reminders for project supervisor dashboard.
    Returns upcoming reminders from deliverables deadlines that the supervisor has created.
    """
    try:
        from datetime import datetime, timedelta
        from bson import ObjectId

        supervisor_academic_id = current_user.email
        if not supervisor_academic_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing supervisor ID")
        
        supervisor = await db["lecturers"].find_one({"academicId": supervisor_academic_id})
        if not supervisor:
            raise HTTPException(status_code=404, detail="Supervisor not found")
        
        supervisor_id = supervisor["_id"]
        current_date = datetime.utcnow()
        
        # Debug: Log supervisor info
        print(f"[DEBUG Reminders] Supervisor ID: {supervisor_id}")
        print(f"[DEBUG Reminders] Current date: {current_date}")
        
        # Get all deliverables created by this supervisor
        # Note: Dates are stored as strings, so we'll filter in Python
        all_deliverables = await db["deliverables"].find(
            {"supervisor_id": supervisor_id},
            {"_id": 1, "name": 1, "end_date": 1, "instructions": 1}
        ).to_list(length=None)
        
        print(f"[DEBUG Reminders] Found {len(all_deliverables)} deliverables for supervisor")
        
        # Convert deliverables to reminder format and filter by date
        reminders_with_dates = []  # Store with datetime for sorting
        for deliverable in all_deliverables:
            try:
                end_date_str = deliverable.get("end_date")
                deliverable_name = deliverable.get("name", "Unnamed")
                
                print(f"[DEBUG Reminders] Processing deliverable: {deliverable_name}, end_date_str: {end_date_str}, type: {type(end_date_str)}")
                
                if not end_date_str:
                    print(f"[DEBUG Reminders] Skipping {deliverable_name} - no end_date")
                    continue
                
                # Parse date string - try multiple formats
                end_date = None
                if isinstance(end_date_str, datetime):
                    end_date = end_date_str
                    print(f"[DEBUG Reminders] {deliverable_name} - end_date is already datetime: {end_date}")
                elif isinstance(end_date_str, str):
                    # Try ISO format first
                    try:
                        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        print(f"[DEBUG Reminders] {deliverable_name} - Parsed ISO format: {end_date}")
                        # Convert to UTC if timezone-aware
                        if end_date.tzinfo:
                            end_date = end_date.replace(tzinfo=None) + (end_date.utcoffset() or timedelta(0))
                            print(f"[DEBUG Reminders] {deliverable_name} - Converted to UTC-naive: {end_date}")
                    except Exception as iso_error:
                        print(f"[DEBUG Reminders] {deliverable_name} - ISO parse failed: {iso_error}, trying other formats...")
                        # Try other formats (e.g., "2024-12-15T23:59:59", "2024-12-15")
                        try:
                            if 'T' in end_date_str:
                                date_part = end_date_str.split('T')[0]
                                end_date = datetime.strptime(date_part, "%Y-%m-%d")
                                print(f"[DEBUG Reminders] {deliverable_name} - Parsed date-only from datetime string: {end_date}")
                            else:
                                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                                print(f"[DEBUG Reminders] {deliverable_name} - Parsed date-only string: {end_date}")
                        except Exception as parse_error:
                            print(f"[DEBUG Reminders] Could not parse end_date for {deliverable_name}: {end_date_str}, error: {parse_error}")
                            continue
                else:
                    print(f"[DEBUG Reminders] {deliverable_name} - Unknown end_date type: {type(end_date_str)}, value: {end_date_str}")
                    continue
                
                if not end_date:
                    print(f"[DEBUG Reminders] Skipping {deliverable_name} - end_date is None after parsing")
                    continue
                
                # Normalize timezone - convert to UTC if timezone-aware
                if end_date.tzinfo:
                    end_date = end_date.replace(tzinfo=None) + (end_date.utcoffset() or timedelta(0))
                
                # Store original end_date for comparison logic
                original_end_date = end_date
                
                # Only include if deadline is in the future (with some buffer for end of day)
                # If end_date has no time component or is midnight, assume end of day (23:59:59)
                if end_date.hour == 0 and end_date.minute == 0 and end_date.second == 0:
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    print(f"[DEBUG Reminders] {deliverable_name} - Adjusted midnight to end of day: {end_date}")
                
                # Compare dates
                days_until_deadline = (end_date - current_date).days
                hours_until_deadline = (end_date - current_date).total_seconds() / 3600
                print(f"[DEBUG Reminders] {deliverable_name} - Deadline: {end_date}, Current: {current_date}, Days until: {days_until_deadline}, Hours until: {hours_until_deadline:.2f}")
                
                # Show reminders for deadlines that are upcoming (in the future) OR very recent (within last 7 days)
                # This helps supervisors see deadlines they might have just missed
                if end_date < current_date:
                    # If deadline passed less than 7 days ago, still show it (as overdue)
                    if days_until_deadline >= -7:
                        print(f"[DEBUG Reminders] Adding overdue reminder (within 7 days): {deliverable_name} - {end_date} (was {original_end_date}, {abs(days_until_deadline)} days overdue)")
                    else:
                        print(f"[DEBUG Reminders] Skipping old deadline: {deliverable_name} - {end_date} (was {original_end_date}, {abs(days_until_deadline)} days overdue)")
                        continue
                else:
                    print(f"[DEBUG Reminders] ✓ Adding upcoming reminder: {deliverable_name} - {end_date} (was {original_end_date})")
                
                date_str = end_date.strftime("%d %b").upper()  # "14 NOV"
                day_of_week = end_date.strftime("%A")  # "Tuesday"
                time_str = end_date.strftime("%I:%M %p").lower()  # "7:30 am"
                
                # Mark as overdue if deadline has passed
                is_overdue = end_date < current_date
                title_prefix = "Overdue: " if is_overdue else "Deadline: "
                
                reminders_with_dates.append({
                    "id": str(deliverable["_id"]),
                "date": date_str,
                    "date_iso": end_date.strftime("%Y-%m-%d"),  # Add ISO date for calendar
                    "title": f"{title_prefix}{deliverable.get('name', 'Untitled Deliverable')}",
                "day": day_of_week,
                "time": time_str,
                    "description": deliverable.get("instructions", "Submission deadline"),
                    "type": "deliverable_deadline",
                    "_sort_date": end_date  # Store for sorting
                })
            except Exception as e:
                print(f"[DEBUG] Error formatting deliverable reminder: {e}")
                continue
        
        # Sort by date (earliest first)
        reminders_with_dates.sort(key=lambda x: x.get("_sort_date", datetime.max))
        
        # Remove sort_date field and limit
        formatted_reminders = []
        for reminder in reminders_with_dates[:limit]:
            reminder_copy = {k: v for k, v in reminder.items() if k != "_sort_date"}
            formatted_reminders.append(reminder_copy)
        
        print(f"[DEBUG Reminders] Returning {len(formatted_reminders)} reminders")
        
        return {
            "reminders": formatted_reminders,
            "supervisor_info": {
                "academic_id": supervisor_academic_id,
                "name": f"{supervisor.get('surname', '')} {supervisor.get('otherNames', '')}".strip()
            },
            "pagination": {
                "current_page": 1,
                "per_page": limit,
                "total": len(formatted_reminders),
                "showing": f"1-{len(formatted_reminders)} of {len(formatted_reminders)}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching supervisor reminders: {str(e)}")
