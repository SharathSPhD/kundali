// Public (publishable) Supabase values — safe to commit. Used as fallbacks
// when NEXT_PUBLIC_* env vars are not set at build time (e.g. CLI deploys
// where .env.production is not uploaded). Secrets never go in this file.

export const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL ||
  "https://mcnknhbtipvclirawhxw.supabase.co";

export const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1jbmtuaGJ0aXB2Y2xpcmF3aHh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMwOTkzNDUsImV4cCI6MjA5ODY3NTM0NX0.mnkJTXA6zXWIB70DXb8vpLO4SdBDs2soxrKLlcDA1fo";

// Escape hatch: set NEXT_PUBLIC_FORCE_LOCAL_MODE=1 to run without Supabase.
export const FORCE_LOCAL_MODE =
  process.env.NEXT_PUBLIC_FORCE_LOCAL_MODE === "1";
