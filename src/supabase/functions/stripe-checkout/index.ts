// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { withSupabase } from "jsr:@supabase/server@^1";
import Stripe from "npm:stripe";

const stripe = new Stripe(Deno.env.get("STRIPE_API_KEY")!);

const PRICE_IDS: Record<string, string | undefined> = {
  Pro: Deno.env.get("STRIPE_PRICE_ID_PRO"),
  Premium: Deno.env.get("STRIPE_PRICE_ID_PREMIUM"),
};

const FRONTEND_URL = Deno.env.get("FRONTEND_URL") ?? "http://localhost:3000";

export default {
  fetch: withSupabase({ auth: "user" }, async (req, ctx) => {
    const userId = ctx.userClaims?.sub;
    if (!userId) {
      return Response.json({ error: "invalid or expired token" }, { status: 401 });
    }

    let plan: string;
    try {
      ({ plan } = await req.json());
    } catch {
      return Response.json({ error: "invalid request body" }, { status: 400 });
    }

    const priceId = PRICE_IDS[plan];
    if (!priceId) {
      return Response.json({ error: `no price configured for plan "${plan}"` }, { status: 422 });
    }

    let session: Stripe.Checkout.Session;
    try {
      session = await stripe.checkout.sessions.create({
        mode: "subscription",
        line_items: [{ price: priceId, quantity: 1 }],
        client_reference_id: userId,
        metadata: { user_id: userId, plan },
        success_url: `${FRONTEND_URL}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: `${FRONTEND_URL}/billing/cancel`,
      });
    } catch (exc) {
      console.error(`stripe checkout session creation failed: ${exc}`);
      return Response.json({ error: "failed to create checkout session" }, { status: 502 });
    }

    if (!session.url) {
      return Response.json({ error: "stripe did not return a checkout url" }, { status: 502 });
    }

    return Response.json({ checkout_url: session.url, session_id: session.id });
  }),
};
