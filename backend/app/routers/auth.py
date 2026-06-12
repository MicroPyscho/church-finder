"""
Auth router — registration, login, JWT tokens.
Uses bcrypt for password hashing, JWT for stateless auth.
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.database import get_db
from app.models import User, UserFavourite
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
ALGORITHM   = "HS256"
TOKEN_HOURS = 24 * 30  # 30 days


# ── Schemas ───────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:    EmailStr
    name:     str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user:         dict

class UserOut(BaseModel):
    id:    int
    email: str
    name:  str


# ── Helpers ───────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)

def create_token(user_id: int, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_HOURS)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "exp": expire},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", 0))
        user = await db.get(User, user_id)
        return user if user and user.is_active else None
    except (JWTError, ValueError):
        return None

async def require_user(
    user: User | None = Depends(get_current_user),
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to continue",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=LoginResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check email not taken
    existing = (await db.execute(
        select(User).where(User.email == req.email.lower())
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=req.email.lower(),
        name=req.name,
        hashed_pw=hash_password(req.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_token(user.id, user.email)
    logger.info("New user registered: %s", user.email)
    return LoginResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "name": user.name},
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db:   AsyncSession = Depends(get_db),
):
    user = (await db.execute(
        select(User).where(User.email == form.username.lower())
    )).scalar_one_or_none()

    if not user or not verify_password(form.password, user.hashed_pw):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user.id, user.email)
    return LoginResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "name": user.name},
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(require_user)):
    return UserOut(id=user.id, email=user.email, name=user.name)


# ── Persistent favourites ─────────────────────────────────────────────────

@router.get("/favourites")
async def get_favourites(
    user: User = Depends(require_user),
    db:   AsyncSession = Depends(get_db),
):
    from app.models import Listing
    favs = (await db.execute(
        select(UserFavourite).where(UserFavourite.user_id == user.id)
    )).scalars().all()
    listing_ids = [f.listing_id for f in favs]
    if not listing_ids:
        return []
    listings = (await db.execute(
        select(Listing).where(Listing.id.in_(listing_ids))
    )).scalars().all()
    import json
    return [{"id": l.id, "title": l.title, "price": l.price,
             "location": l.location, "source": l.source,
             "images": json.loads(l.images) if l.images else []} for l in listings]


@router.post("/favourites/{listing_id}")
async def add_favourite(
    listing_id: str,
    user: User = Depends(require_user),
    db:   AsyncSession = Depends(get_db),
):
    existing = (await db.execute(
        select(UserFavourite).where(
            UserFavourite.user_id == user.id,
            UserFavourite.listing_id == listing_id,
        )
    )).scalar_one_or_none()
    if not existing:
        db.add(UserFavourite(user_id=user.id, listing_id=listing_id))
        await db.commit()
    return {"saved": True}


@router.delete("/favourites/{listing_id}")
async def remove_favourite(
    listing_id: str,
    user: User = Depends(require_user),
    db:   AsyncSession = Depends(get_db),
):
    fav = (await db.execute(
        select(UserFavourite).where(
            UserFavourite.user_id == user.id,
            UserFavourite.listing_id == listing_id,
        )
    )).scalar_one_or_none()
    if fav:
        await db.delete(fav)
        await db.commit()
    return {"saved": False}
