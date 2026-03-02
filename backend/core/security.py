from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --------------------------------------------------
# PASSWORD HASHING
# --------------------------------------------------

def hash_password(password: str) -> str:
    """
    Hash password safely.
    Bcrypt supports max 72 bytes.
    """
    if not password:
        raise ValueError("Password cannot be empty")

    password = password[:72]  # bcrypt limitation
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password safely.
    """
    if not plain_password:
        return False

    plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)


# --------------------------------------------------
# JWT TOKEN CREATION
# --------------------------------------------------

def create_access_token(data: dict):
    """
    Create JWT access token.
    """
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY not configured")

    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)