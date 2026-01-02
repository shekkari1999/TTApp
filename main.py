from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="TTApp - Timetable Management System")

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")


# ==================== WEB PAGES ====================

@app.get("/")
async def home():
    """Home page"""
    return {"message": "Welcome to TTApp - Timetable Management System"}


@app.get("/class-timetable")
async def class_timetable_page(request: Request):
    """Render the class timetable viewing page"""
    return templates.TemplateResponse("class_timetable.html", {"request": request})


# ==================== API ENDPOINTS ====================

@app.get("/api/classes")
async def get_classes():
    """
    Get list of all classes
    TODO: Replace with actual database query
    """
    # Sample data - replace with your database query
    classes = [
        {"id": "1", "name": "Class 10A"},
        {"id": "2", "name": "Class 10B"},
        {"id": "3", "name": "Class 9A"},
        {"id": "4", "name": "Class 9B"},
        {"id": "5", "name": "Class 8A"},
    ]
    return JSONResponse(content=classes)


@app.get("/api/class-schedules")
async def get_class_schedules(classId: str):
    """
    Get timetable schedule for a specific class
    TODO: Replace with actual database query
    """
    # Sample data - replace with your database query
    # This represents a weekly timetable
    schedule = {
        "classId": classId,
        "className": f"Class {classId}",
        "periods": [1, 2, 3, 4, 5, 6],  # Number of periods per day
        "slots": [
            # Monday
            {"day": "Monday", "period": 1, "subject": "Mathematics", "teacher": "Mr. Ram Kumar"},
            {"day": "Monday", "period": 2, "subject": "English", "teacher": "Ms. Sita Sharma"},
            {"day": "Monday", "period": 3, "subject": "Science", "teacher": "Mr. Raj Patel"},
            {"day": "Monday", "period": 4, "subject": "Social Studies", "teacher": "Ms. Priya Singh"},
            {"day": "Monday", "period": 5, "subject": "Hindi", "teacher": "Mr. Jay Mehta"},
            {"day": "Monday", "period": 6, "subject": "Physical Education", "teacher": "Mr. Arjun Das"},
            
            # Tuesday
            {"day": "Tuesday", "period": 1, "subject": "Hindi", "teacher": "Mr. Jay Mehta"},
            {"day": "Tuesday", "period": 2, "subject": "Mathematics", "teacher": "Mr. Ram Kumar"},
            {"day": "Tuesday", "period": 3, "subject": "English", "teacher": "Ms. Sita Sharma"},
            {"day": "Tuesday", "period": 4, "subject": "Computer Science", "teacher": "Ms. Neha Gupta"},
            {"day": "Tuesday", "period": 5, "subject": "Science", "teacher": "Mr. Raj Patel"},
            {"day": "Tuesday", "period": 6, "subject": "Art", "teacher": "Ms. Kavita Joshi"},
            
            # Wednesday
            {"day": "Wednesday", "period": 1, "subject": "Science", "teacher": "Mr. Raj Patel"},
            {"day": "Wednesday", "period": 2, "subject": "Social Studies", "teacher": "Ms. Priya Singh"},
            {"day": "Wednesday", "period": 3, "subject": "Mathematics", "teacher": "Mr. Ram Kumar"},
            {"day": "Wednesday", "period": 4, "subject": "English", "teacher": "Ms. Sita Sharma"},
            {"day": "Wednesday", "period": 5, "subject": "Hindi", "teacher": "Mr. Jay Mehta"},
            {"day": "Wednesday", "period": 6, "subject": "Music", "teacher": "Mr. Amit Roy"},
            
            # Thursday
            {"day": "Thursday", "period": 1, "subject": "English", "teacher": "Ms. Sita Sharma"},
            {"day": "Thursday", "period": 2, "subject": "Hindi", "teacher": "Mr. Jay Mehta"},
            {"day": "Thursday", "period": 3, "subject": "Social Studies", "teacher": "Ms. Priya Singh"},
            {"day": "Thursday", "period": 4, "subject": "Mathematics", "teacher": "Mr. Ram Kumar"},
            {"day": "Thursday", "period": 5, "subject": "Computer Science", "teacher": "Ms. Neha Gupta"},
            {"day": "Thursday", "period": 6, "subject": "Science", "teacher": "Mr. Raj Patel"},
            
            # Friday
            {"day": "Friday", "period": 1, "subject": "Mathematics", "teacher": "Mr. Ram Kumar"},
            {"day": "Friday", "period": 2, "subject": "Science", "teacher": "Mr. Raj Patel"},
            {"day": "Friday", "period": 3, "subject": "Hindi", "teacher": "Mr. Jay Mehta"},
            {"day": "Friday", "period": 4, "subject": "English", "teacher": "Ms. Sita Sharma"},
            {"day": "Friday", "period": 5, "subject": "Social Studies", "teacher": "Ms. Priya Singh"},
            {"day": "Friday", "period": 6, "subject": "Physical Education", "teacher": "Mr. Arjun Das"},
        ]
    }
    return JSONResponse(content=schedule)


# ==================== MAIN ====================

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes (disable in production)
    )