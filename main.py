import time
import uuid
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, Field

app = FastAPI()

# In-memory storage for submissions
submissions_db = {}


# --- 1. Custom Request Logging Middleware ---
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()

    response = await call_next(request)

    process_time = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id

    print(
        f"[LOG] ID: {request_id} | Method: {request.method} | Path: {request.url.path} | "
        f"Status: {response.status_code} | Time: {process_time}ms"
    )

    return response


# --- 2. Custom Error Response Handler ---
@app.exception_handler(RequestValidationError)
def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err["loc"] if loc != "body")
        errors.append({"field": field, "issue": err["msg"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed.",
                "details": errors,
            }
        },
    )


# --- 3. Pydantic Request Model ---
class SubmissionCreate(BaseModel):
    task_id: str = Field(..., min_length=1)
    deliverable_url: HttpUrl
    note: str = Field(..., max_length=500)
    status: Optional[str] = "submitted"


# --- 4. API Endpoints ---
@app.get("/")
def read_root():
    return {"status": "success", "message": "Backend API active"}


@app.post("/submissions", status_code=status.HTTP_201_CREATED)
def create_submission(payload: SubmissionCreate):
    submission_id = str(uuid.uuid4())
    data = payload.model_dump()
    data["deliverable_url"] = str(data["deliverable_url"])
    data["id"] = submission_id

    submissions_db[submission_id] = data
    return {"status": "success", "data": data}


@app.get("/submissions/{id}")
def get_submission(id: str):
    if id not in submissions_db:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Submission not found",
                    "details": None,
                }
            },
        )
    return {"status": "success", "data": submissions_db[id]}

