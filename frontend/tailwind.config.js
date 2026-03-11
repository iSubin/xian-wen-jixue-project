/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#3b82f6', // Blue 500
        secondary: '#2563eb', // Blue 600
        bg: '#f9fafb', // Gray 50
      },
      fontFamily: {
        sans: ['Microsoft YaHei', 'Segoe UI', 'Consolas', 'sans-serif'],
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
