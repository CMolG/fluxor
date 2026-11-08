import Link from "next/link";
import { ProductHuntBanner } from "./components/ProductHuntBanner";

export default function Home() {
  return (
    <main>
      <ProductHuntBanner />
      <section className="hero">
        <h1>The Ultimate Revolutionary AI Note-Taking Experience 🚀</h1>
        <p>Quillmate joins your Zoom, Google Meet and Teams calls, writes the notes, and sends action items to Slack.</p>
        <Link href="/signup">Start your free trial</Link>
      </section>
      <section>
        <h2>Why Quillmate?</h2>
        <ul>
          <li>Accurate transcripts in 30+ languages</li>
          <li>Summaries and action items in under a minute</li>
          <li>Search every meeting you have ever had</li>
        </ul>
      </section>
      <footer>
        <a href="#">Privacy</a> · <a href="#">Terms</a> · <a href="mailto:hello@quillmate.app">Contact</a>
      </footer>
    </main>
  );
}
