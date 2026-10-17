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
          950: "#064e3b", // Deep botanical emerald
          900: "#065f46",
          800: "#047857",
          700: "#059669",
          600: "#10b981",
          500: "#10b981",
          400: "#34d399",
          300: "#6ee7b7",
          200: "#a7f3d0",
          100: "#d1fae5",
          50: "#ecfdf5",
        },
        terra: {
          base: "#f8fafc",      // Bright clean canvas (slate-50)
          dark: "#f1f5f9",      // Secondary container (slate-100)
          deep: "#f8fafc",      // Application main background
          surface: "#ffffff",   // Crisp elevated card (pure white)
          card: "#ffffff",      // Card background
          panel: "#ffffff",     // Panel surface
          forest: "#f1f5f9",    // Soft slate panel
          emerald: "#059669",   // Crisp primary emerald
          mint: "#10b981",      // Vibrant mint green
          cyan: "#0284c7",      // Sky blue data accent
          amber: "#d97706",     // Warm amber soil/warning
          rose: "#e11d48",      // Hazard/Exclusion coral rose
          ivory: "#0f172a",     // Ultra crisp dark text (slate-900)
          muted: "#334155",     // Secondary text (slate-700)
          slate: "#64748b",     // Labels and metadata (slate-500)
          charcoal: "#475569",  // Slate-600
          border: "#e2e8f0",    // Crisp border (slate-200)
          'border-subtle': "#f1f5f9",
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.45)',
        'glass-hover': '0 12px 40px 0 rgba(0, 0, 0, 0.60)',
        'emerald-glow': '0 0 20px -3px rgba(16, 185, 129, 0.35)',
        'mint-glow': '0 0 20px -3px rgba(52, 211, 153, 0.40)',
        'cyan-glow': '0 0 20px -3px rgba(56, 189, 248, 0.35)',
        'subtle': '0 2px 10px rgba(0, 0, 0, 0.3)',
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      }
    },
  },
  plugins: [],
}
