"use client";
import { loadStripe } from "@stripe/stripe-js";

export default function Signup() {
  return (
    <main>
      <h1>Start your 7-day trial</h1>
      <form action="/api/checkout" method="post">
        <input name="fullName" placeholder="Full name" required />
        <input name="email" type="email" placeholder="Work email" required />
        <input name="password" type="password" placeholder="Password" required />
        <input name="company" placeholder="Company" required />
        <input name="role" placeholder="Job title" required />
        <select name="teamSize" required><option>1-10</option><option>11-50</option><option>51+</option></select>
        <input name="phone" type="tel" placeholder="Phone number" required />
        <p>Enter your card details to start the trial. You won't be charged until day 8.</p>
        <button type="submit">Continue to payment</button>
      </form>
    </main>
  );
}
