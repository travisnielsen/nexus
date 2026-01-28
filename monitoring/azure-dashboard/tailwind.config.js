/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'vscode': {
          'bg': '#1e1e1e',
          'sidebar': '#252526',
          'border': '#333',
          'hover': '#2a2d2e',
          'selected': '#094771',
          'accent': '#0078d4',
          'text': '#d4d4d4',
          'muted': '#888',
        }
      }
    },
  },
  plugins: [],
}
