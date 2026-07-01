/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "var(--brand-subtle)",
          100: "var(--brand-subtle)",
          200: "var(--brand-light)",
          300: "var(--brand-light)",
          500: "var(--brand-accent)",
          600: "var(--brand-accent)",
          700: "var(--brand)",
          800: "var(--brand)",
        },
        gray: {
          50: "var(--bg-subtle)",
          100: "var(--bg-subtle)",
          200: "var(--border)",
          300: "var(--border)",
          400: "var(--fg-muted)",
          500: "var(--fg-muted)",
          600: "var(--fg-muted)",
          700: "var(--fg-secondary)",
          800: "var(--fg)",
          900: "var(--fg)",
        },
        surface: {
          sidebar: "var(--bg-subtle)",
          muted: "var(--bg-subtle)",
          card: "var(--bg-subtle)",
        },
        metrics: {
          DEFAULT: "var(--metrics)",
          bg: "var(--metrics-bg)",
        },
      },
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
