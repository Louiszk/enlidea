module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs', 'src/api/generated/*'],
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  settings: { react: { version: '18.2' } },
  plugins: ['react-refresh', '@typescript-eslint'],
  rules: {
    'react/jsx-no-target-blank': 'off',
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    'react/prop-types': 'off',
    'no-unused-vars': 'off',
    '@typescript-eslint/no-unused-vars': ['error', { 
      'varsIgnorePattern': '^React$|^_',
      'argsIgnorePattern': '^_',
      'caughtErrorsIgnorePattern': '^_'
    }],
    '@typescript-eslint/no-explicit-any': 'error',
    'react/no-unescaped-entities': 'off',
    'react-hooks/exhaustive-deps': 'warn',
    'react/display-name': 'off',
    'no-useless-catch': 'off',
    'no-extra-semi': 'off',
  },
  overrides: [
    {
      files: ['src/contexts/*.jsx', 'src/contexts/*.tsx'],
      rules: {
        'react-refresh/only-export-components': 'off',
      },
    },
  ],
}
