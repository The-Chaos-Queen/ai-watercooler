/*  hurtig.ai — Shared Tailwind Configuration
    Single source of truth for all pages.
    Colors named for the brand: kiln, cream, sage, amber, ink, clay.
*/
tailwind.config = {
  theme: {
    extend: {
      colors: {
        kiln:  { DEFAULT: "#a03f28", light: "#c0573e", dark: "#812914", 50: "#ffdad2", 100: "#ffb4a3" },
        cream: { DEFAULT: "#fff8ef", 100: "#faf3e6", 200: "#f4ede1", 300: "#eee7db", 400: "#e9e2d6", 500: "#e0d9cd" },
        sage:  { DEFAULT: "#506354", light: "#d0e5d2", dark: "#394b3d" },
        amber: { DEFAULT: "#6f583c", light: "#fdddb9", container: "#897052" },
        ink:   { DEFAULT: "#1e1b14", light: "#56423d", muted: "#8a726c" },
        clay:  { DEFAULT: "#ddc0ba", dark: "#8a726c" },
      },
      fontFamily: {
        headline: ['"Newsreader"', "serif"],
        body:     ['"Manrope"', "sans-serif"],
      },
      animation: {
        "grain": "grain 8s steps(10) infinite",
      },
      keyframes: {
        grain: {
          "0%, 100%": { transform: "translate(0, 0)" },
          "10%":  { transform: "translate(-5%, -10%)" },
          "30%":  { transform: "translate(7%, -25%)" },
          "50%":  { transform: "translate(-15%, 10%)" },
          "70%":  { transform: "translate(0%, 15%)" },
          "90%":  { transform: "translate(-10%, 10%)" },
        },
      },
    },
  },
};
