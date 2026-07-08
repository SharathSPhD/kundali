import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy — Kundali",
};

/**
 * Store-submission requirement: both Google Play and the Apple App Store
 * require a publicly reachable privacy policy URL. Keep this page honest
 * and in sync with actual behavior (Supabase-hosted data, RLS, BYOK keys,
 * GB10 inference path).
 */
export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12 text-slate-300">
      <h1 className="font-display text-3xl font-bold text-gold-300">
        Privacy Policy
      </h1>
      <p className="mt-2 text-sm text-slate-500">Last updated: 8 July 2026</p>

      <section className="mt-8 space-y-6 text-sm leading-relaxed">
        <div>
          <h2 className="mb-2 font-semibold text-slate-100">What we collect</h2>
          <p>
            Kundali stores the data you enter to compute charts: birth
            profiles (date, time, place, coordinates, optional life events),
            your account email, and any chat questions you ask. Nothing else
            is collected; there is no advertising, tracking or analytics SDK
            in the app.
          </p>
        </div>
        <div>
          <h2 className="mb-2 font-semibold text-slate-100">Where it lives</h2>
          <p>
            Your data is stored in our Supabase (PostgreSQL) database with
            row-level security: every profile, reading and chat message is
            readable and writable only by the account that created it. In
            local mode (no account), profiles stay in your browser and never
            leave your device.
          </p>
        </div>
        <div>
          <h2 className="mb-2 font-semibold text-slate-100">AI processing</h2>
          <p>
            Deterministic answers are computed by our own engine and involve
            no third party. If your account tier includes AI chat, your
            chart facts and question are processed by a model we host
            ourselves. If you bring your own API key (Anthropic, OpenAI,
            Gemini or Ollama), your chart facts and question are sent to
            that provider under your key and their terms; your key is stored
            in your account row, readable only by you.
          </p>
        </div>
        <div>
          <h2 className="mb-2 font-semibold text-slate-100">Sharing & selling</h2>
          <p>
            We do not sell, rent or share your data with anyone. Data leaves
            the system only when you use a bring-your-own-key AI provider, as
            described above.
          </p>
        </div>
        <div>
          <h2 className="mb-2 font-semibold text-slate-100">Deletion</h2>
          <p>
            Deleting a profile removes it and its readings, events and chat
            messages immediately. To delete your whole account and all data,
            contact us at the address below.
          </p>
        </div>
        <div>
          <h2 className="mb-2 font-semibold text-slate-100">Nature of the service</h2>
          <p>
            Kundali provides computed Vedic astrology information for
            reflection and study. It is not medical, financial, legal or
            psychological advice, and no outcome is guaranteed.
          </p>
        </div>
        <div>
          <h2 className="mb-2 font-semibold text-slate-100">Contact</h2>
          <p>sharath.ai.colab@gmail.com</p>
        </div>
      </section>
    </main>
  );
}
