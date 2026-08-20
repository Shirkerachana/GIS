/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        glow: "0 0 0 1px rgba(125, 211, 252, 0.22), 0 12px 40px rgba(15, 23, 42, 0.45)",
      },
      colors: {
        ink: {
          950: "#07111f",
          900: "#0b1629",
          850: "#10223d",
          800: "#173055",
        },
        geo: {
          100: "#d9f3ff",
          300: "#89dcff",
          400: "#55c7ff",
          500: "#1ca7e2",
          600: "#0a7fb2",
          700: "#0c5f87",
        },
        sand: {
          100: "#f7f1e3",
          200: "#ebdfc1",
        },
      },
      fontFamily: {
        sans: ["Avenir Next", "Segoe UI", "Trebuchet MS", "sans-serif"],
        display: ["Avenir Next Condensed", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

