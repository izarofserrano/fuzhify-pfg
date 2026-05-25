/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        accent: {
          DEFAULT: '#F97316',
          hover:   '#EA6B08',
          dim:     'rgba(249,115,22,0.15)',
        },
        surface: {
          base:     '#080A0F',
          card:     '#0E1117',
          elevated: '#161B24',
        },
        border: {
          DEFAULT: '#1E2736',
          accent:  'rgba(249,115,22,0.35)',
        },
      },
      fontFamily: {
        display: ['Syne', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
}
