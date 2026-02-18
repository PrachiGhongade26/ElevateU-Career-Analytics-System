from fastapi import APIRouter, HTTPException, Depends
from schemas import UserCreate, UserResponse, UserLogin
from database import get_connection
from passlib.context import CryptContext
from auth import create_access_token, get_current_user

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ========================
# CREATE USER
# ========================
@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute(
            "SELECT * FROM Users WHERE email = ?",
            (user.email,)
        )
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Clean & hash password
        clean_password = user.password.strip()
        safe_password = clean_password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
        hashed_password = pwd_context.hash(safe_password)

        # Insert new user
        cursor.execute(
            "INSERT INTO Users (name, email, password) VALUES (?, ?, ?)",
            (user.name, user.email, hashed_password)
        )
        conn.commit()

        # Fetch created user
        cursor.execute(
            "SELECT user_id, name, email FROM Users WHERE email = ?",
            (user.email,)
        )
        new_user = cursor.fetchone()

        # 🔥 Automatically create DashboardStats row
        cursor.execute(
            "INSERT INTO DashboardStats (user_id) VALUES (?)",
            (new_user[0],)
        )
        conn.commit()

        conn.close()

        return {
            "id": new_user[0],
            "name": new_user[1],
            "email": new_user[2]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# GET ALL USERS
# ========================
@router.get("/users", response_model=list[UserResponse])
def get_users():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, name, email FROM Users")
        rows = cursor.fetchall()
        conn.close()

        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "name": row[1],
                "email": row[2]
            })

        return users

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# LOGIN USER
# ========================
@router.post("/login")
def login(user: UserLogin):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_id, name, email, password FROM Users WHERE email = ?",
            (user.email,)
        )
        existing_user = cursor.fetchone()

        if not existing_user:
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid email or password")

        stored_password = existing_user[3]

        clean_password = user.password.strip()
        safe_password = clean_password.encode("utf-8")[:72].decode("utf-8", errors="ignore")

        if not pwd_context.verify(safe_password, stored_password):
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token(
            {
                "user_id": existing_user[0],
                "email": existing_user[2]
            }
        )

        conn.close()

        return {
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========================
# GET PROFILE (PROTECTED)
# ========================
@router.get("/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "message": "Profile fetched successfully",
        "user": current_user
    }


# ========================
# DASHBOARD (PROTECTED - DATABASE DRIVEN)
# ========================
@router.get("/dashboard")
def get_dashboard(current_user: dict = Depends(get_current_user)):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT level, points, progress FROM DashboardStats WHERE user_id = ?",
            (current_user["user_id"],)
        )
        stats = cursor.fetchone()

        conn.close()

        if not stats:
            raise HTTPException(status_code=404, detail="Dashboard stats not found")

        return {
            "message": f"Welcome {current_user['name']} to ElevateU Dashboard 🚀",
            "user": current_user,
            "stats": {
                "level": stats[0],
                "points": stats[1],
                "progress": stats[2]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ========================
# ADD POINTS (PROTECTED)
# ========================
@router.post("/add-points")
def add_points(points: int, current_user: dict = Depends(get_current_user)):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get current points
        cursor.execute(
            "SELECT points FROM DashboardStats WHERE user_id = ?",
            (current_user["user_id"],)
        )
        result = cursor.fetchone()

        if not result:
            conn.close()
            raise HTTPException(status_code=404, detail="Dashboard stats not found")

        current_points = result[0]
        new_points = current_points + points

        # Determine level
        if new_points < 100:
            level = "Beginner"
            progress = int((new_points / 100) * 100)

        elif new_points < 300:
            level = "Intermediate"
            progress = int(((new_points - 100) / 200) * 100)

        else:
            level = "Advanced"
            progress = int(((new_points - 300) / 500) * 100)
            if progress > 100:
                progress = 100

        # Update database
        cursor.execute(
            "UPDATE DashboardStats SET points = ?, level = ?, progress = ? WHERE user_id = ?",
            (new_points, level, progress, current_user["user_id"])
        )
        conn.commit()
        conn.close()

        return {
            "message": "Points added successfully 🚀",
            "new_stats": {
                "level": level,
                "points": new_points,
                "progress": progress
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ========================
# LEADERBOARD (PUBLIC)
# ========================
@router.get("/leaderboard")
def get_leaderboard():
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TOP 5 u.name, d.points, d.level
            FROM Users u
            JOIN DashboardStats d ON u.user_id = d.user_id
            ORDER BY d.points DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        leaderboard = []
        rank = 1

        for row in rows:
            leaderboard.append({
                "rank": rank,
                "name": row[0],
                "points": row[1],
                "level": row[2]
            })
            rank += 1

        return {
            "leaderboard": leaderboard
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

