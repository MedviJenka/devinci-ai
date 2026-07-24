// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { withSupabase } from "jsr:@supabase/server@^1";
import Stripe from "npm:stripe";

const stripe = new Stripe(Deno.env.get("STRIPE_API_KEY")!);

export default {
  fetch: withSupabase({ auth: "none" }, async (req, ctx) => {
    const body = await req.text();
    const sig = req.headers.get("stripe-signature")!;

    let event: Stripe.Event;
    try {
      event = await stripe.webhooks.constructEventAsync(
        body,
        sig,
        Deno.env.get("STRIPE_WEBHOOK_SECRET")!,
      );
    } catch {
      return Response.json({ error: "Invalid signature" }, { status: 401 });
    }

    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        if (session.payment_status !== "paid") break;

        const metadata = session.metadata ?? {};
        const userId = metadata.user_id || session.client_reference_id;
        const plan = metadata.plan;

        if (!userId || (plan !== "Pro" && plan !== "Premium")) {
          console.error(`checkout.session.completed ${session.id} missing user_id/plan metadata`);
          break;
        }

        const { error } = await ctx.supabaseAdmin
          .from("users")
          .update({ subscription: plan })
          .eq("id", userId);

        if (error) {
          console.error(`failed to upgrade user ${userId} to ${plan}: ${error.message}`);
          return Response.json({ error: "failed to process event" }, { status: 500 });
        }

        console.log(`user ${userId} upgraded to ${plan} via checkout session ${session.id}`);
        break;
      }
    }

    console.log(`🔔 Event received: ${event.id}`);
    return Response.json({ received: true });
  }),
};
