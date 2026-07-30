/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        coral: {
          DEFAULT: "#FF6B6B",
          hover: "#FF5252",
        },
        warmorange: {
          DEFAULT: "#FFB347",
          hover: "#FFA62E",
        },
        warmwhite: "#FFF9F5",
        userbubble: "#F0F0F0",
      },
      borderRadius: {
        button: "12px",
        input: "12px",
        card: "16px",
        bubble: "16px",
      },
      animation: {
        "message-in": "messageIn 0.2s ease-out forwards",
      },
      keyframes: {
        messageIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
}
