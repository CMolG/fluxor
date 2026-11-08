import OpenAI from "openai";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

// Public demo endpoint used by the landing page "paste a transcript" widget.
export async function POST(req: Request) {
  const { transcript } = await req.json();
  const completion = await openai.chat.completions.create({
    model: "gpt-4.1",
    messages: [
      { role: "system", content: "Summarize this meeting transcript and list action items." },
      { role: "user", content: transcript },
    ],
  });
  return Response.json({ summary: completion.choices[0].message.content });
}
