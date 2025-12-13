# Database Setup Instructions

## Your Supabase Connection Details

**Project URL:** https://zgbsuijwhzotswbyiqea.supabase.co

**Project Reference:** zgbsuijwhzotswbyiqea

## Step 1: Get Your Database Password

1. Go to: https://supabase.com/dashboard/project/zgbsuijwhzotswbyiqea/settings/database
2. Find the **"Database password"** section
3. If you haven't set one, click **"Reset database password"** and save it
4. Copy your database password

## Step 2: Create `.env` File

Create a file named `.env` in your project root (`C:\Users\akhil\OneDrive\Desktop\projects\TTApp\`) with this content:

```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD_HERE@db.zgbsuijwhzotswbyiqea.supabase.co:5432/postgres
SECRET_KEY=dev-secret-key-change-in-production-ttapp-2024
```

**Replace `YOUR_PASSWORD_HERE` with your actual Supabase database password.**

## Step 3: Test the Connection

After creating the `.env` file, run:

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (if not already done)
uv pip install -e .

# Test database connection
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('✅ Database connection successful! Tables created.')"
```

## Step 4: Run the Application

```powershell
python app.py
```

Then open: http://localhost:5000

---

## Quick Reference

**Connection String Format:**
```
postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

**Your Connection String:**
```
postgresql://postgres:[YOUR-PASSWORD]@db.zgbsuijwhzotswbyiqea.supabase.co:5432/postgres
```

**Where to find password:**
- Supabase Dashboard → Your Project → Settings → Database → Database password

