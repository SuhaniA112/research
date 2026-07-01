/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#fdf2f8",
          100: "#fce7f3",
          200: "#fbcfe8",
          300: "#f9a8d4",
          400: "#f472b6",
          500: "#c026d3",
          600: "#a21caf",
          700: "#882d60",
          800: "#701a4f",
          900: "#581c3d",
        },
        surface: {
          sidebar: "#f3f4f6",
          muted: "#f9fafb",
          card: "#f3f4f6",
        },
        metric: {
          green: "#16a34a",
          "green-light": "#dcfce7",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
