export default function Footer() {
  return (
    <footer className="border-t border-night-600/30 bg-night-900/50 px-4 py-12 sm:px-6">
      <div className="mx-auto max-w-5xl">
        <div className="grid gap-12 sm:grid-cols-3">
          {/* Brand */}
          <div>
            <h3 className="font-display text-xl font-bold text-slate-100">
              Kundali
            </h3>
            <p className="mt-2 text-sm text-slate-500">
              Rigorous Vedic astrology. Deterministic. Traceable. Private.
            </p>
          </div>

          {/* Product */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gold-400">
              Product
            </p>
            <ul className="mt-4 space-y-2">
              <li>
                <a
                  href="/dashboard"
                  className="text-sm text-slate-400 transition hover:text-gold-300"
                >
                  Dashboard
                </a>
              </li>
              <li>
                <a
                  href="/login"
                  className="text-sm text-slate-400 transition hover:text-gold-300"
                >
                  Sign In
                </a>
              </li>
            </ul>
          </div>

          {/* Legal & Fine Print */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gold-400">
              Disclaimers
            </p>
            <p className="mt-4 text-xs leading-relaxed text-slate-500">
              Vedic astrology is a traditional knowledge system. Kundali's
              predictions and guidance are for educational and entertainment
              purposes only — not medical, financial, or legal advice. Always
              consult qualified professionals for important decisions.
            </p>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-12 border-t border-night-600/20 pt-6 text-center text-xs text-slate-600">
          <p>
            Built with rigor. Validated against NASA JPL Horizons. Formal proofs
            in Lean 4.
          </p>
          <p className="mt-2">
            Lahiri ayanamsa · whole-sign houses · Vimshottari 365.25d —
            configurable.
          </p>
        </div>
      </div>
    </footer>
  );
}
