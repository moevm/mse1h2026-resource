import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import { defineConfig, globalIgnores } from "eslint/config";
import prettierConfig from "eslint-config-prettier";
import reactPlugin from "eslint-plugin-react";
import jsxA11y from "eslint-plugin-jsx-a11y";

export default defineConfig([
  globalIgnores(["dist", "node_modules"]),

  jsxA11y.flatConfigs.recommended,

  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommendedTypeChecked,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      prettierConfig,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      react: reactPlugin,
    },
    settings: {
      react: {
        version: "detect",
      },
    },
    rules: {
      // Type-import consistency
      "@typescript-eslint/consistent-type-imports": [
        "error",
        { prefer: "type-imports", fixStyle: "inline-type-imports" },
      ],
      "@typescript-eslint/consistent-type-exports": "error",
      "@typescript-eslint/no-import-type-side-effects": "error",

      // Nullish / optional
      "@typescript-eslint/prefer-nullish-coalescing": [
        "error",
        { ignorePrimitives: { boolean: true } },
      ],
      "@typescript-eslint/prefer-optional-chain": "error",

      // Prevent accidental any leakage
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-unsafe-assignment": "warn",
      "@typescript-eslint/no-unsafe-member-access": "warn",
      "@typescript-eslint/no-unsafe-call": "warn",
      "@typescript-eslint/no-unsafe-return": "warn",
      "@typescript-eslint/no-unsafe-argument": "warn",

      // Floating promises
      "@typescript-eslint/no-floating-promises": "error",
      "@typescript-eslint/no-misused-promises": "error",

      // TypeScript quality from reference
      "@typescript-eslint/switch-exhaustiveness-check": "error",
      "@typescript-eslint/no-empty-object-type": "error",

      // React rules
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      "react/self-closing-comp": "warn",
      "react/jsx-no-useless-fragment": "warn",

      // JSX a11y
      "jsx-a11y/anchor-is-valid": ["error", { specialLink: ["to"] }],

      // General quality
      eqeqeq: ["error", "always", { null: "ignore" }],
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-param-reassign": "error",
      "prefer-const": "error",
      "no-var": "error",

      // Turn off base rule, use TS version
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
]);
