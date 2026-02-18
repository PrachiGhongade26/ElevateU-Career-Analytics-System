from fastapi import FastAPI
from routers import user
from fastapi.security import HTTPBearer


app = FastAPI()

security = HTTPBearer()


@app.get("/")
def root():
    return {"message": "ElevateU API is running 🚀"}

@app.get("/health")
def health_check():
    return {"status": "Backend is healthy"}

# Include user routes
app.include_router(user.router)
