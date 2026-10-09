/**
 * Design tokens — "Clinical Ledger" system.
 * Palette named, not templated: cool paper background (not cream), deep
 * teal-navy anchor, sage for verified/normal, muted brick for attention,
 * and a distinct violet-blue reserved ONLY for "AI-generated" content
 * markers — so extracted facts and AI interpretation are always visually
 * distinguishable at a glance, per the product's core trust requirement.
 */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F6F8F7",
        ink: "#16241F",
        surface: {
          DEFAULT: "#FFFFFF",
          dark: "#101B19",
        },
        brand: {
          50: "#EAF2F1",
          100: "#CFE3E1",
          300: "#7FADA9",
          500: "#1E5C5F",
          700: "#0E3A3D",
          900: "#062223",
        },
        verified: {
          50: "#EAF6EF",
          400: "#4FAE7C",
          600: "#2F8F6B",
          700: "#256E53",
        },
        attention: {
          50: "#FBEEE9",
          400: "#DB7A5D",
          600: "#C0503A",
          700: "#9B3E2C",
        },
        unknown: {
          50: "#F1F2F0",
          400: "#9CA39E",
          600: "#6C736E",
        },
        ai: {
          50: "#EEEEF7",
          400: "#8A8DC7",
          600: "#5B5FA6",
          700: "#454789",
        },
        border: "#E2E8E4",
        borderDark: "#22322E",
      },
      fontFamily: {
        display: ["'IBM Plex Serif'", "serif"],
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      borderRadius: {
        card: "1rem",
        pill: "999px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(14, 58, 61, 0.06), 0 8px 24px -12px rgba(14, 58, 61, 0.12)",
        cardHover: "0 4px 12px rgba(14, 58, 61, 0.10), 0 16px 32px -16px rgba(14, 58, 61, 0.18)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.4s ease-out both",
      },
    },
  },
  plugins: [],
};
