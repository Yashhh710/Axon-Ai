/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        axon: {
          bg: '#0f1115',
          sidebar: '#17191e',
          input: '#1e2229',
          primary: '#6366f1',
          border: 'rgba(255, 255, 255, 0.08)',
          text: '#f1f5f9',
          muted: '#94a3b8'
        }
      }
    },
  },
  plugins: [],
}
