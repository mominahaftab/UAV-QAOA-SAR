/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0b0c',
        cream: '#F7F5EF',
        cloud: '#e2dedd',
        navy: {
          900: '#070b12',
          800: '#0c121e',
          700: '#141e30',
          600: '#1d2c44',
        },
      },
      fontFamily: {
        exo: ['"Exo 2"', 'sans-serif'],
        sans: ['"Public Sans"', 'system-ui', 'sans-serif'],
      },
      textShadow: {
        headline: '0 4px 16px rgba(0, 0, 0, 0.55)',
      },
    },
  },
  plugins: [],
}

