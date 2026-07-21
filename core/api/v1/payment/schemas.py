from typing import Literal
from pydantic import BaseModel, Field


type PaidPlan = Literal['Pro', 'Premium']


class CheckoutSessionRequest(BaseModel):
    plan: PaidPlan = Field(..., description='subscription tier to purchase')


class CheckoutSessionResponse(BaseModel):
    checkout_url: str = Field(..., description='Stripe-hosted checkout page URL')
    session_id:   str = Field(..., description='Stripe checkout session id')
