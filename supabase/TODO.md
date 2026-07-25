# Supabase TODO

## Stripe integration (deployed 2026-07-25, test mode)

Done:
- `stripe-checkout` and `stripe-webhook` deployed via `supabase functions deploy`
- Test-mode Price IDs created and set as secrets (STRIPE_PRICE_ID_PRO, STRIPE_PRICE_ID_PREMIUM)
- Webhook endpoint registered in Stripe, signing secret set as STRIPE_WEBHOOK_SECRET
- `stripe-webhook` deployed with `--no-verify-jwt` (Stripe can't send a Supabase JWT)
- `stripe-checkout` keeps platform JWT verification (requires a logged-in user)

Still missing:
- No frontend UI calls `stripe-checkout` — no "Upgrade to Pro/Premium" button exists yet in `frontend/src`
- `FRONTEND_URL` secret is `http://localhost:3000` — must be updated to the real deployed URL before going live, otherwise Stripe checkout success/cancel redirects will point at localhost
- Price IDs and webhook secret are test-mode — need to be recreated in live mode (with a live `STRIPE_API_KEY`) before accepting real payments
- No local/CI test coverage for the checkout or webhook Deno functions

## Redeploying

```
npx supabase functions deploy stripe-checkout
npx supabase functions deploy stripe-webhook --no-verify-jwt
```

Secrets: `npx supabase secrets set KEY=value ...` (see `.env` Payment/Webhooks sections for current values).
