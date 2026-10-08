/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        flood: {
          safe: "#10b981",       // 0-5 cm (emerald)
          minor: "#84cc16",      // 5-15 cm (lime)
          moderate: "#f59e0b",   // 15-30 cm (amber)
          severe: "#ef4444",     // 30-50 cm (red)
          critical: "#d946ef",   // >50 cm (fuchsia/magenta)
        },
        slate: {
          850: "#172033",
          950: "#0b0f19",
        }
      },
      animation: {
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ripple': 'ripple 1.5s linear infinite',
      },
      screens: {
        'xs': '480px',
      },
      keyframes: {
        ripple: {
          '0%': { transform: 'scale(0.8)', opacity: '1' },
          '100%': { transform: 'scale(2.4)', opacity: '0' },
        }
      }
    },
  },
  plugins: [],
}
