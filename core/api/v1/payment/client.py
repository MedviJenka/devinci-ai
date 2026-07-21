from dataclasses import dataclass
from stripe import Event, StripeClient
from stripe.checkout import Session as CheckoutSession
from core.api.v1.payment.schemas import PaidPlan
from core.database.users.client import Users
from core.settings import Config
from core.useful.log import Logger


log = Logger(name='payment-manager')


class CheckoutSessionError(Exception):
    pass


@dataclass
class StripeManager:

    def __post_init__(self) -> None:
        self.client = StripeClient(api_key=Config.STRIPE_API_KEY)
        self.users = Users()
        self._price_ids: dict[PaidPlan, str] = {
            'Pro':     Config.STRIPE_PRICE_ID_PRO,
            'Premium': Config.STRIPE_PRICE_ID_PREMIUM,
        }

    def create_checkout_session(self, user_id: str, plan: PaidPlan) -> tuple[str, str]:
        price_id = self._price_ids.get(plan)
        if not price_id:
            raise CheckoutSessionError(f'no price configured for plan "{plan}"')

        session = self.client.v1.checkout.sessions.create(params={
            'mode': 'subscription',
            'line_items': [{'price': price_id, 'quantity': 1}],
            'client_reference_id': user_id,
            'metadata': {'user_id': user_id, 'plan': plan},
            'success_url': f'{Config.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}',
            'cancel_url': f'{Config.FRONTEND_URL}/billing/cancel',
        })
        if not session.url:
            raise CheckoutSessionError('stripe did not return a checkout url')
        return session.url, session.id

    def construct_event(self, payload: bytes, sig_header: str) -> Event:
        return self.client.construct_event(payload, sig_header, Config.STRIPE_WEBHOOK_SECRET)

    def handle_event(self, event: Event) -> None:
        if event.type == 'checkout.session.completed':
            self._handle_checkout_completed(event.data.object)

    def _handle_checkout_completed(self, session: CheckoutSession) -> None:
        if session.payment_status != 'paid':
            return

        metadata = session.metadata or {}
        user_id = metadata.get('user_id') or session.client_reference_id
        plan = metadata.get('plan')

        if not user_id or plan not in ('Pro', 'Premium'):
            log.fire.error(f'checkout.session.completed {session.id} missing user_id/plan metadata')
            return

        self.users.update_to_paid(user_id, subscription=plan)
        log.fire.info(f'user {user_id} upgraded to {plan} via checkout session {session.id}')
