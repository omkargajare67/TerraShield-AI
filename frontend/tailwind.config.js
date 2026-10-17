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
          950: "#06100c",
          900: "#091812", // Deep black-green surface
          800: "#0c2119",
          700: "#0f2b20", // Forest Green Panel
          600: "#13382a",
          500: "#10b981", // Electric Emerald
          400: "#34d399", // Mint Accent
          300: "#6ee7b7",
          200: "#a7f3d0", // Soft Mint
          100: "#d1fae5",
          50: "#f0fdf4",
        },
        terra: {
          base: "#06100c",      // Deepest background
          dark: "#091812",      // Shell background
          deep: "#091812",
          surface: "#0c2119",   // Elevated surface
          card: "#0f2a20",      // Card background
          panel: "#123326",     // Panel surface
          forest: "#0f2b20",
          emerald: "#10b981",   // Electric Emerald Accent
          mint: "#34d399",      // Vibrant Mint
          cyan: "#38bdf8",      // Restrained Cyan Highlight
          amber: "#fbbf24",     // Insufficient Data / Warning
          rose: "#f43f5e",      // Excluded / Critical
          ivory: "#f8fafc",     // Crisp High-contrast Typography
          muted: "#94a3b8",     // Secondary text
          slate: "#64748b",     // Muted labels
          charcoal: "#16231d",
          border: "rgba(52, 211, 153, 0.16)",
          'border-subtle': "rgba(255, 255, 255, 0.08)",
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
