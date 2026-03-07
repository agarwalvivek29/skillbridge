// @ts-check
import js from '@eslint/js'

export default [
  {
    ignores: [
      'packages/schema/generated/**',
      '**/node_modules/**',
      '**/dist/**',
      '**/.next/**',
    ],
  },
  {
    ...js.configs.recommended,
    files: ['**/*.{js,mjs,cjs,jsx,ts,tsx}'],
  },
]
