from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import User
import os


# ======================================================
# JWT CONFIGURATION
# ======================================================
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_key_change_this")
ALGORITHM = "HS256"

# IMPORTANT:
# This must match your login route path exactly
# If login route is @router.post("/login")
# Then use tokenUrl="login"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ======================================================
# GET CURRENT USER FROM JWT TOKEN
# ======================================================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Fetch user from DB
    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise credentials_exception

    return user


# ======================================================
# ROLE CHECK FUNCTIONS
# ======================================================
def require_student(user: User = Depends(get_current_user)):

    if user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access only"
        )

    return user


def require_faculty(user: User = Depends(get_current_user)):

    if user.role != "faculty":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty access only"
        )

    return user