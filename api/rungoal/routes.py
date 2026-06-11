from fastapi import APIRouter

from rungoal import auth, crud
from rungoal.deps import DepDb
from rungoal.models import Authorization, GoogleApiAuthCode

api = APIRouter(prefix="/api")


@api.post("/auth/callback/", tags=["Auth"])
def google_auth(auth_code: GoogleApiAuthCode, db: DepDb) -> Authorization:
    google_user = auth.get_google_user(auth_code)
    user = crud.get_user_by_email(db, google_user.email) or crud.create_user(db, google_user)
    return auth.generate_token_pair(user.email)
