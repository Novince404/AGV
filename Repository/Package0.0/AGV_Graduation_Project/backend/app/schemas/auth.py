from pydantic import BaseModel


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class EnterpriseRegisterRequest(BaseModel):
    company_name: str
    contact_name: str
    contact_email: str
    username: str
    password: str


class EnterpriseApplicationReviewRequest(BaseModel):
    review_note: str | None = None
