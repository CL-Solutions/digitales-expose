import type { Config } from 'tailwindcss';

export default {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'invenio-gold': 'var(--color-invenio-gold)',
        'invenio-gold-dark': 'var(--color-invenio-gold-dark)',
        'invenio-brown': 'var(--color-invenio-brown)',
        'invenio-beige': 'var(--color-invenio-beige)',
        'invenio-gray': 'var(--color-invenio-gray)',
      },
      fontFamily: {
        sans: 'var(--font-family-sans)',
        display: 'var(--font-family-display)',
      },
    },
  },
} satisfies Config;