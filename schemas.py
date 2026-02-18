from pydantic import BaseModel, EmailStr, Field


# Used when registering a new user
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=50)


# Used when logging in
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Used when sending user data in response
class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr

    class Config:
        orm_mode = True
