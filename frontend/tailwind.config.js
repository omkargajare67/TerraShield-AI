/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        forest: {
          950: "#0b1713",
          900: "#10251D", // Deep Forest Green (Primary Shell / Dark background)
          800: "#16382b",
          700: "#1C4937", // Forest Green
          600: "#27624a",
          500: "#34795C", // Emerald Accent
          400: "#489574",
          300: "#70b999",
          200: "#A7E6C5", // Soft Mint
          100: "#DDE8DC", // Muted Sage
          50: "#F7F7F0",  // Warm Ivory
        },
        terra: {
          dark: "#10251D",
          forest: "#1C4937",
          emerald: "#34795C",
          mint: "#A7E6C5",
          ivory: "#F7F7F0",
          sage: "#DDE8DC",
          charcoal: "#202A25",
          slate: "#6B756F",
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(16, 37, 29, 0.12)',
        'glass-hover': '0 12px 40px 0 rgba(16, 37, 29, 0.20)',
        'subtle': '0 2px 10px rgba(0, 0, 0, 0.04)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      }
    },
  },
  plugins: [],
}
