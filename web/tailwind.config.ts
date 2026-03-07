import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0a0c10',
        surface: '#111318',
        'surface-hover': '#181c24',
        border: '#1e2330',
        'border-active': '#3d4f6e',
        accent: '#4f8ef7',
        green: '#2dd4a0',
        amber: '#f5a623',
        purple: '#9b87f5',
      },
    },
  },
  plugins: [],
}
export default config
