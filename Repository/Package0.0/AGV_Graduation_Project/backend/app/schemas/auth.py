from pydantic import BaseModel


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class PersonalRegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str | None = None


class EnterpriseRegisterRequest(BaseModel):
    company_name: str
    contact_name: str
    contact_email: str
    username: str
    password: str


class EnterpriseApplicationReviewRequest(BaseModel):
    review_note: str | None = None


class UserSuspendRequest(BaseModel):
    reason: str
    note: str | None = None
    duration_days: int | None = None
    permanent: bool = False


class UserDeactivateRequest(BaseModel):
    reason: str | None = None
    note: str | None = None
