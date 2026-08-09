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
        sans: ['Noto Sans SC', 'Noto Sans TC', 'PingFang SC', 'Microsoft YaHei', 'system-ui', 'sans-serif'],
        serif: ['Noto Serif SC', 'Noto Serif TC', 'Songti SC', 'STSong', 'serif'],
        reading: ['Noto Serif SC', 'Noto Serif TC', 'Songti SC', 'STSong', 'serif'],
        mono: ['JetBrains Mono', 'SFMono-Regular', 'Consolas', 'monospace'],
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
