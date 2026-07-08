import { Calculator, Grid3x3, Moon, Telescope, Lock, MessageCircle } from "lucide-react";
import Hero from "@/components/landing/Hero";
import StarField from "@/components/landing/StarField";
import FeatureSection from "@/components/landing/FeatureSection";
import DerivationShowcase from "@/components/landing/DerivationShowcase";
import ComparisonSection from "@/components/landing/ComparisonSection";
import Footer from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <main className="bg-night-950">
      {/* Hero */}
      <Hero />

      {/* Divider with subtle accent */}
      <div className="border-b border-night-600/20" />

      {/* Feature 1: Deterministic Engine */}
      <FeatureSection
        index={0}
        icon={Calculator}
        title="Rigorous Calculations"
        description="Every position, aspect, and dignity is computed using Swiss Ephemeris and validated against NASA JPL Horizons. No approximations. No guessing."
        points={[
          "Lahiri ayanamsa (sidereal zodiac) with multiple options",
          "Whole-sign houses for precise house placement",
          "Arcsecond accuracy — within NASA standards",
          "15,807 real charts crash-tested and verified",
        ]}
        visual={<StarField />}
      />

      {/* Feature 2: All 16 Vargas */}
      <FeatureSection
        index={1}
        icon={Grid3x3}
        title="Complete Divisional Charts"
        description="All 16 shodasha vargas per BPHS — not just the rashi chart. Each varga reveals a different layer of your destiny."
        points={[
          "Navamsha for marriage, dharma, and hidden nature",
          "Dashamsha for career and public life",
          "Dwadasamsha, Trimshamsha, and 12 more — fully computed",
          "Integrated varga corroboration for predictions",
        ]}
        visual={null}
      />

      {/* Feature 3: Dasha Systems */}
      <FeatureSection
        index={2}
        icon={Moon}
        title="Dashas & Transits"
        description="Vimshottari and Chara dashas with minute-level precision, plus live transit tracking with Sade Sati and Jupiter–Saturn double transit detection."
        points={[
          "Full dasha tree: maha → antar → pratyantar with exact dates",
          "Chara dasha for predictive timing",
          "Gochara (transit) engine with Sade Sati phases",
          "K.N. Rao's Jupiter–Saturn double-transit rules",
        ]}
        visual={null}
      />

      {/* Feature 4: Privacy & Control */}
      <FeatureSection
        index={3}
        icon={Lock}
        title="Private by Design"
        description="Your birth data never leaves your account. BYOK (bring your own key) for AI, or run fully deterministic with zero external APIs."
        points={[
          "Supabase RLS — only you see your data",
          "No third-party data brokers",
          "Deterministic mode: all answers computed locally",
          "Optional AI with claim verification and flagging",
        ]}
        visual={null}
      />

      {/* Divider */}
      <div className="border-b border-night-600/20" />

      {/* Derivation Showcase */}
      <DerivationShowcase />

      {/* Divider */}
      <div className="border-b border-night-600/20" />

      {/* Comparison Section */}
      <ComparisonSection />

      {/* Divider */}
      <div className="border-b border-night-600/20" />

      {/* Footer */}
      <Footer />
    </main>
  );
}
