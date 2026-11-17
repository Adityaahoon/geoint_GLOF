/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#070b14",
          900: "#0b1220",
          800: "#111a2b",
          700: "#1a2638",
          600: "#26364f",
          500: "#3b506f",
        },
        glacier: {
          300: "#7dd3fc",
          400: "#5ec8e5",
          500: "#38bdf8",
          600: "#0284c7",
        },
        hazard: {
          low: "#4ade80",
          moderate: "#facc15",
          high: "#fb923c",
          veryhigh: "#ef4444",
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};
