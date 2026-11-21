module.exports = {
  content: [
    "./templates/asistente/**/*.html",
    "./static/js/asistente.js",
  ],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        ink: "#071319",
        charcoal: "#2f4550",
        "charcoal-deep": "#1f2f38",
        slate: "#586f7c",
        mist: "#b8dbd9",
        paper: "#f4f4f9",
        harvest: "#f2a51a",
        danger: "#b85450",
        success: "#4f7a5c",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Cascadia Code", "Consolas", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 3px rgba(47,69,80,.07), 0 0 0 1px rgba(47,69,80,.04)",
        float: "0 18px 44px -20px rgba(7,19,25,.35)",
        composer: "0 6px 18px rgba(47,69,80,.07)",
      },
      borderRadius: {
        xl2: "14px",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "dot-pulse": {
          "0%, 80%, 100%": { opacity: ".25", transform: "scale(.8)" },
          "40%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "200% 0" },
          "100%": { backgroundPosition: "-200% 0" },
        },
      },
      animation: {
        "fade-up": "fade-up 220ms cubic-bezier(0.25, 1, 0.5, 1) both",
        "dot-pulse": "dot-pulse 1.1s ease-in-out infinite",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [],
};
