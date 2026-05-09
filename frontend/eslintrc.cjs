/** @type {import("eslint").Linter.Config} */
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: { jsx: true },
  },
  plugins: ["@typescript-eslint", "react-hooks"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  rules: {
    "@typescript-eslint/no-explicit-any":          "error",
    "@typescript-eslint/no-unused-vars":           ["error", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/no-non-null-assertion":    "warn",
    "@typescript-eslint/consistent-type-imports":  "error",
    "react-hooks/rules-of-hooks":  "error",
    "react-hooks/exhaustive-deps": "warn",
    "no-console":   ["warn", { allow: ["warn", "error"] }],
    "no-debugger":  "error",
    "eqeqeq":       ["error", "always"],
    "no-var":        "error",
    "prefer-const": "error",
  },
  ignorePatterns: ["dist/", "node_modules/", "*.config.ts", "*.config.js"],
};
