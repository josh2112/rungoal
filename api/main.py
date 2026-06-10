from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scopes = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
]


class GoogleApiAuthCode(BaseModel):
    code: str


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/api/auth/callback")
def read_item(auth: GoogleApiAuthCode):
    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes,
        redirect_uri="postmessage",
    )

    flow.fetch_token(code=auth.code)

    service = build(
        "oauth2",
        "v2",
        credentials=Credentials(flow.credentials.token, flow.credentials.refresh_token),
    )

    user_info = service.userinfo().get().execute()

    return {
        "email": user_info.get("email"),
        "profile_pic": user_info.get("picture"),
        "name": user_info.get("name"),
    }
