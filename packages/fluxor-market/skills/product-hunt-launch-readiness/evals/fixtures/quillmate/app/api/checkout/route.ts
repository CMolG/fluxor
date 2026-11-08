import Stripe from "stripe";
import { sendVerificationEmail } from "@/lib/email";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(req: Request) {
  const form = await req.formData();
  const email = String(form.get("email"));
  await sendVerificationEmail(email);
  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    customer_email: email,
    line_items: [{ price: "price_pro_monthly", quantity: 1 }],
    subscription_data: { trial_period_days: 7 },
    success_url: `${process.env.NEXT_PUBLIC_SITE_URL}/welcome`,
    cancel_url: `${process.env.NEXT_PUBLIC_SITE_URL}/pricing`,
  });
  return Response.redirect(session.url!, 303);
}
