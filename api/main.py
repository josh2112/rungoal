from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApiTokenRequest(BaseModel):
    code: str


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/api/auth/callback")
def read_item(req: ApiTokenRequest):
    return {"result": "got the code!", "code": req.code}
