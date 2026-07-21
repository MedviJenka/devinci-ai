from core.settings import Config
from typing import AsyncGenerator
from core.useful.log import Logger
from contextlib import asynccontextmanager
from stripe import SignatureVerificationError
from core.useful.auth import get_current_user_id
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from core.api.v1.payment.client import CheckoutSessionError, StripeManager
from core.api.v1.payment.schemas import CheckoutSessionRequest, CheckoutSessionResponse


log = Logger(name='payment-service')


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} started successfully')
    yield
    log.fire.info(f'{log.name} stopped successfully')


router = APIRouter(prefix=f'/api/{Config.API_VERSION}/payment', lifespan=lifespan, dependencies=[Depends(get_current_user_id)])
stripe_manager = StripeManager()


@router.post('/checkout')
async def create_checkout_session(req: CheckoutSessionRequest) -> CheckoutSessionResponse:
    try:
        checkout_url, session_id = stripe_manager.create_checkout_session(get_current_user_id(), req.plan)
        log.fire.info(f'url:{checkout_url}, session_id:{session_id} | success')
    except CheckoutSessionError as exc:
        log.fire.error(f'{HTTPException(status_code=422, detail=str(exc))}')
        raise
    response = CheckoutSessionResponse(checkout_url=checkout_url, session_id=session_id)
    log.fire.info(f'{response}')
    return response


@router.post('/webhook')
async def stripe_webhook(request: Request) -> dict[str, bool]:

    payload = await request.body()
    sig_header = request.headers.get('stripe-signature', '')

    try:
        event = stripe_manager.construct_event(payload, sig_header)
    except (ValueError, SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail='invalid webhook payload or signature') from exc

    try:
        stripe_manager.handle_event(event)
    except Exception as exc:
        log.fire.error(f'failed to process webhook event {event.id}: {exc}')
        raise HTTPException(status_code=500, detail='failed to process event') from exc

    return {'received': True}
