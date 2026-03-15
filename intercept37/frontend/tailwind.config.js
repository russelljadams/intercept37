/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        alien: {
          black: '#0a0a0f',
          dark: '#0d0d14',
          panel: '#11111a',
          border: '#1a1a2e',
          green: '#00ff41',
          'green-dim': '#00cc33',
          cyan: '#00e5ff',
          red: '#ff3131',
          orange: '#ff8c00',
          yellow: '#ffd700',
          blue: '#4488ff',
          gray: '#666680',
          text: '#c0c0d0',
          'text-dim': '#888898',
        },
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Fira Code', 'Consolas', 'monospace'],
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
        'scan-line': 'scan-line 4s linear infinite',
        'flicker': 'flicker 3s ease-in-out infinite',
        'slide-in': 'slide-in 0.3s ease-out',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 5px rgba(0, 255, 65, 0.3), inset 0 0 5px rgba(0, 255, 65, 0.1)' },
          '50%': { boxShadow: '0 0 15px rgba(0, 255, 65, 0.5), inset 0 0 10px rgba(0, 255, 65, 0.2)' },
        },
        'scan-line': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'flicker': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.8' },
        },
        'slide-in': {
          '0%': { transform: 'translateX(20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
      },
      boxShadow: {
        'alien': '0 0 10px rgba(0, 255, 65, 0.3)',
        'alien-lg': '0 0 20px rgba(0, 255, 65, 0.4)',
        'cyan': '0 0 10px rgba(0, 229, 255, 0.3)',
        'red': '0 0 10px rgba(255, 49, 49, 0.3)',
      },
    },
  },
  plugins: [],
}
