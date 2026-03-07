// eslint.config.mjs — ESLint flat config (v9+)
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";

/** @type {import('eslint').Linter.FlatConfig[]} */
export default [
  {
    // Ignore generated files, build artifacts, and vendored code
    ignores: [
      "**/node_modules/**",
      "**/generated/**",
      "**/.next/**",
      "**/dist/**",
      "**/build/**",
      "*.config.*",
    ],
  },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
    },
    rules: {
      // Start with a minimal rule set; tighten as the codebase matures
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
];
