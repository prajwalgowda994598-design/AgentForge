/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        forge: {
          // Backgrounds
          bg:       '#14171b',
          panel:    '#1b1f24',
          panel2:   '#20252b',
          // Borders
          border:   '#333a42',
          // Accents
          ember:    '#ff6a3d',
          'ember-dim': '#c94f2b',
          blue:     '#6fb3d9',
          // Text
          paper:    '#eae6dd',
          muted:    '#a9a49a',
          steel:    '#8b95a1',
          // Status
          success:  '#5fbf8f',
          warning:  '#e0b04a',
          alert:    '#e0625a',
        },
      },
      fontFamily: {
        display: ['"Big Shoulders Display"', 'system-ui', 'sans-serif'],
        sans:    ['"IBM Plex Sans"',         'system-ui', 'sans-serif'],
        mono:    ['"IBM Plex Mono"',          'ui-monospace', 'monospace'],
      },
      keyframes: {
        'ember-pulse': {
          '0%, 100%': { opacity: '1',   boxShadow: '0 0 6px 2px rgba(255,106,61,0.6)' },
          '50%':       { opacity: '0.5', boxShadow: '0 0 2px 1px rgba(255,106,61,0.25)' },
        },
        'rail-travel': {
          '0%':   { top: '-8%',   opacity: '0' },
          '8%':   { opacity: '1' },
          '92%':  { opacity: '1' },
          '100%': { top: '108%',  opacity: '0' },
        },
        'spin': {
          to: { transform: 'rotate(360deg)' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'ember-pulse': 'ember-pulse 1.8s ease-in-out infinite',
        'rail-travel': 'rail-travel 2.2s ease-in-out infinite',
        'spin':        'spin 0.8s linear infinite',
        'fade-up':     'fade-up 0.3s ease-out',
      },
    },
  },
  plugins: [],
}
