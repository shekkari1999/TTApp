# TTApp - Application Overview

## Table of Contents
1. [What is TTApp?](#what-is-ttapp)
2. [Tech Stack](#tech-stack)
3. [Features Implemented](#features-implemented)
4. [Database Schema](#database-schema)
5. [API Endpoints](#api-endpoints)
6. [Schedule Generation Logic](#schedule-generation-logic)
7. [Missing & Incomplete Features](#missing--incomplete-features)
8. [Known Limitations](#known-limitations)
9. [Security Considerations](#security-considerations)

---

## What is TTApp?

TTApp is a **full-stack school timetable management system** designed specifically for Indian schools. It handles:
- Automated timetable generation with grade-specific rules
- Teacher schedule management
- Absence tracking and substitute teacher suggestions
- User authentication with admin approval workflow

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3.0.0+ (Python) |
| Database | PostgreSQL (Supabase) |
| ORM | SQLAlchemy |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Authentication | Session-based with password hashing |
| Package Manager | uv |

---

## Features Implemented

### 1. User Authentication & Authorization

| Feature | Status |
|---------|--------|
| User registration (self-signup) | Done |
| Admin approval/rejection workflow | Done |
| Session-based login | Done |
| Password hashing | Done |
| Role-based access (Admin vs Teacher) | Done |
| Admin-created teacher accounts | Done |

**User Roles:**
- **Admin**: Full access to manage teachers, subjects, classes, schedules, and user approvals
- **Teacher**: Can view personal timetable and submit update requests
- **Pending User**: Awaiting admin approval

### 2. Teacher Management

| Feature | Status |
|---------|--------|
| Create/Edit/Delete teachers | Done |
| Assign subjects to teachers | Done |
| Assign class teachers | Done |
| Link teacher to user account | Done |
| Teacher update request workflow | Done |

### 3. Subject Management

| Feature | Status |
|---------|--------|
| Create/Edit/Delete subjects | Done |
| Link subjects to teachers | Done |
| Subject validation in scheduling | Done |

### 4. Class Management

| Feature | Status |
|---------|--------|
| Create/Edit/Delete classes | Done |
| Assign grade levels (6-10) | Done |
| Assign class teachers | Done |
| Grade-specific scheduling rules | Done |

### 5. Schedule Generation

| Feature | Status |
|---------|--------|
| Automated schedule generation | Done |
| Grade 6-7 specific rules | Done |
| Grade 8-9 specific rules | Done |
| Grade 10 specific rules | Done |
| Teacher conflict detection | Done |
| Validation & error reporting | Done |
| Placeholder teacher assignment | Done |

### 6. Absence & Substitution Management

| Feature | Status |
|---------|--------|
| Mark teacher as absent | Done |
| View absent teachers by date | Done |
| Substitute teacher suggestions | Done |
| Availability-based substitution | Done |

### 7. Timetable Viewing

| Feature | Status |
|---------|--------|
| Teacher can view their timetable | Done |
| View timetable by date | Done |
| Day name display | Done |
| Weekend handling | Done |

### 8. Admin Dashboard

| Feature | Status |
|---------|--------|
| Unified request management | Done |
| Teacher/Subject/Class CRUD | Done |
| User account management | Done |
| Class teacher assignments | Done |
| Teacher subject assignments | Done |

---

## Database Schema

### Models (7 total)

```
User
├── id (PK)
├── username (unique)
├── email (optional)
├── password_hash
├── is_admin
├── teacher_id (FK → Teacher)
├── status (pending/approved/rejected)
└── created_at

Teacher
├── id (PK)
├── name
├── is_class_teacher
├── is_leisure (unused)
├── created_at
└── subjects (many-to-many → Subject)

Subject
├── id (PK)
├── name (unique)
└── created_at

Class
├── id (PK)
├── name (unique)
├── grade (6-10)
├── class_teacher_id (FK → Teacher)
└── created_at

Schedule
├── id (PK)
├── teacher_id (FK → Teacher)
├── class_id (FK → Class)
├── subject_id (FK → Subject)
├── day (0-6)
├── period (1-8)
├── date (optional)
└── created_at

Absence
├── id (PK)
├── teacher_id (FK → Teacher)
├── date
├── is_substituted
├── substitute_teacher_id (FK → Teacher)
└── created_at

TeacherUpdateRequest
├── id (PK)
├── teacher_id (FK → Teacher)
├── requested_subject_ids (JSON)
├── requested_class_ids (JSON)
├── status (pending/approved/rejected)
├── admin_notes
├── created_at
└── updated_at
```

---

## API Endpoints

### Authentication (4 endpoints)
- `GET/POST /login` - User login
- `GET/POST /signup` - User registration
- `GET /logout` - Logout
- `GET /api/auth/check` - Check authentication status

### User Management (5 endpoints)
- `GET /api/pending-users` - List pending registrations
- `POST /api/users/<id>/approve` - Approve user
- `POST /api/users/<id>/reject` - Reject user
- `GET /api/users` - List all users
- `DELETE /api/users/<id>` - Delete user

### Teacher Management (6 endpoints)
- `GET /api/teachers` - List all teachers
- `POST /api/teachers` - Create teacher
- `PUT /api/teachers/<id>` - Update teacher
- `DELETE /api/teachers/<id>` - Delete teacher
- `POST /api/teachers/reset` - Reset teachers table
- `GET/PUT /api/teachers/<id>/subjects` - Manage teacher subjects

### Subject Management (5 endpoints)
- `GET /api/subjects` - List all subjects
- `POST /api/subjects` - Create subject
- `PUT /api/subjects/<id>` - Update subject
- `DELETE /api/subjects/<id>` - Delete subject
- `POST /api/subjects/reset` - Reset subjects table

### Class Management (6 endpoints)
- `GET /api/classes` - List all classes
- `POST /api/classes` - Create class
- `PUT /api/classes/<id>` - Update class
- `DELETE /api/classes/<id>` - Delete class
- `POST /api/classes/reset` - Reset classes table
- `GET /api/class-schedules` - Get all class schedules

### Schedule & Timetable (4 endpoints)
- `POST /api/generate-schedule` - Generate schedule
- `GET /api/my-timetable` - Get logged-in teacher's timetable
- `GET /api/teacher-timetable/<id>` - Get specific teacher's timetable
- `GET/POST /api/absent-teachers` - Manage absences

### Teacher Update Requests (4 endpoints)
- `POST /api/teacher-update-request` - Submit request
- `GET /api/teacher-update-requests` - List requests
- `POST /api/teacher-update-requests/<id>/approve` - Approve request
- `POST /api/teacher-update-requests/<id>/reject` - Reject request

---

## Schedule Generation Logic

### Grade 6 & 7 Classes
- **8 periods per day**
- 6 unique subjects (no repeats)
- Periods 7-8: Library and Games
- Physical Science + Bio Science → combined "Science"
- Class teacher teaches first period (Monday only)

### Grade 8 & 9 Classes
- **8 periods per day**
- 7 unique subjects (no repeats)
- Period 8: Alternating Library/Games
  - Mon/Wed/Fri: Library
  - Tue/Thu: Games
- Class teacher teaches first period (Monday only)

### Grade 10 Classes
- **8 periods per day**
- Maths at Period 1 AND Period 8 (only repeating subject)
- 6 other unique subjects in periods 2-7
- No Library or Games
- Class teacher teaches first period (Monday only)

### General Rules
- No teacher overlaps (one teacher per period)
- Sunday = Holiday
- Monday-Friday only (days 0-4)
- Same teacher teaches same subject for a class all week

---

## Missing & Incomplete Features

### Definitely Incomplete

| Feature | Details |
|---------|---------|
| **Configuration inputs unused** | Number of classes, subjects, periods inputs exist in UI but are not used in schedule generation |
| **`is_leisure` field unused** | Field exists in Teacher model but always set to False |
| **Manual schedule editing** | No way to edit individual schedule entries after generation |
| **Class timetable viewing** | API endpoint exists (`/api/class-schedules`) but no UI to display class schedules |

### Not Implemented

| Feature | Priority | Description |
|---------|----------|-------------|
| **Schedule Export** | High | No PDF/Excel export functionality |
| **Reports & Analytics** | Medium | No reporting dashboard, attendance reports, or teacher load analysis |
| **Multi-day Absence** | Medium | Only single-date absences supported |
| **Teacher Unavailability Calendar** | Medium | No way to mark planned time-off |
| **Conflict Detection Validator** | Low | No separate endpoint to validate schedules for conflicts |
| **Holiday Configuration** | Low | Hardcoded weekends/holidays |
| **Semester/Term Support** | Low | Only week-based scheduling |
| **Email Notifications** | Low | No email alerts for approvals, schedule changes |
| **Bulk Import** | Low | No CSV/Excel import for teachers, classes, subjects |
| **Audit Logging** | Low | No history of changes made |

---

## Known Limitations

### Functional Limitations
1. **Schedule regeneration required** - Cannot edit individual periods; must regenerate entire schedule
2. **Single class per teacher per period** - No support for split classes or lab sections
3. **Week-only scheduling** - No semester, term, or academic year concepts
4. **No special periods** - No support for exam schedules, events, assemblies

### Technical Limitations
1. **No real-time updates** - Must refresh page to see changes
2. **No mobile-responsive design** - Admin dashboard optimized for desktop
3. **No offline support** - Requires constant internet connection
4. **No backup/restore** - No built-in database backup functionality

### Data Limitations
1. **Hardcoded grade rules** - Grades 6-10 only with specific period allocations
2. **Hardcoded holidays** - Sunday is always holiday
3. **No custom period times** - Only period numbers, no start/end times

---

## Security Considerations

### Implemented
- Password hashing (werkzeug.security)
- Session-based authentication
- Admin-only endpoint protection
- SQL injection prevention (SQLAlchemy ORM)

### Concerns
- **Hardcoded admin credentials** at app startup (`ravi` / `School@143`)
- **No rate limiting** on login attempts
- **No CSRF protection** visible
- **No password complexity requirements**
- **No session timeout** configuration

---

## Application Statistics

| Metric | Count |
|--------|-------|
| API Endpoints | 32 |
| Page Routes | 5 |
| Database Models | 7 |
| HTML Templates | 5 |
| CSS Lines | ~930 |
| JavaScript Lines | ~1,938 |
| Python Lines | ~2,683 |
| **Total Lines of Code** | **~8,000** |

---

## Conclusion

TTApp is a **functional school timetable management system** with sophisticated grade-specific scheduling logic. The core features (scheduling, teacher management, absences, authentication) are fully implemented.

**Ready for use:**
- Schedule generation with Indian school rules
- Teacher and user management
- Absence tracking and substitution suggestions
- Admin dashboard for all operations

**Needs work:**
- Manual schedule editing
- Export functionality
- Class timetable viewing UI
- Configuration system for flexible scheduling
- Mobile-responsive design

---

*Document generated: January 2026*
