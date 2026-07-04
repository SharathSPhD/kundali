import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        night: {
          950: "#070912",
          900: "#0b0e1d",
          800: "#12162e",
          700: "#1a1f40",
          600: "#262c58",
          500: "#39406e",
        },
        gold: {
          200: "#f6ecc8",
          300: "#efdda2",
          400: "#e4c778",
          500: "#d4ab4a",
          600: "#b98f33",
          700: "#93702a",
        },
      },
      fontFamily: {
        display: ["Georgia", "Times New Roman", "serif"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(212, 171, 74, 0.12)",
      },
    },
  },
  plugins: [],
};

export default config;
