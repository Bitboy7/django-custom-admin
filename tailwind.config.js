module.exports = {
  content: [
    "./templates/**/*.html",
    "./app/templates/**/*.html",
    "./auditoria/templates/**/*.html",
    "./catalogo/templates/**/*.html",
    "./gastos/templates/**/*.html",
    "./ventas/templates/**/*.html",
    "./capital_inversiones/templates/**/*.html",
    "./reportes/templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // Brand colors
        primary: {
          50: "#f0fdf4",
          100: "#dcfce7",
          200: "#bbf7d0",
          300: "#86efac",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          800: "#166534",
          900: "#145231",
        },
        secondary: {
          50: "#faf5ff",
          100: "#f3e8ff",
          200: "#e9d5ff",
          300: "#d8b4fe",
          400: "#c084fc",
          500: "#a855f7",
          600: "#9333ea",
          700: "#7e22ce",
          800: "#6b21a8",
          900: "#581c87",
        },
      },
      fontFamily: {
        playfair: ["Playfair Display", "serif"],
        jakarta: ["Plus Jakarta Sans", "sans-serif"],
        jetbrains: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [require("flowbite/plugin")],
  safelist: [
    // Dinámicas para dinero
    "text-green-600",
    "text-red-600",
    "text-yellow-600",
    "bg-green-50",
    "bg-red-50",
    "bg-yellow-50",
  ],
};
