/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brandDark: "#4b3b36",
        brandTop: "#6a544d",
        brandBottom: "#4b3b36",
        brandCard: "#e8dfda",
        brandTextSoft: "#f3ebe7",
        brandMuted: "#d6c8c2",
        brandGreen: "#6b8e6b",
        brandRed: "#a96a6a",
      },
    },
  },
  plugins: [],
}