import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

export async function sendVerificationEmail(to: string) {
  await resend.emails.send({
    from: "Quillmate <hello@quillmate.app>",
    to,
    subject: "Verify your email",
    html: "<p>Click the link to verify your Quillmate account.</p>",
  });
}
