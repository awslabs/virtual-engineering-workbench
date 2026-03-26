import js from '@eslint/js';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import cypress from 'eslint-plugin-cypress';
import stylistic from '@stylistic/eslint-plugin';

export default [
  {
    ignores: ['**/*.json', '**/*.svg', '**/*.css', '**/*.scss', '**/*.png', '**/*.cy.ts', 'dist/**', 'build/**', 'node_modules/**']
  },
  {
    linterOptions: {
      reportUnusedDisableDirectives: false
    }
  },
  js.configs.recommended,
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        project: './tsconfig.json'
      },
      globals: {
        fetch: 'readonly',
        JSX: 'readonly',
        document: 'readonly'
      }
    },
    plugins: {
      '@typescript-eslint': tseslint,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
      'cypress': cypress,
      '@stylistic': stylistic
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      ...cypress.configs.recommended.rules,
      '@typescript-eslint/no-explicit-any': 'off',
      camelcase: 'off',
      '@typescript-eslint/naming-convention': [
        'error',
        {
          selector: 'default',
          format: ['camelCase'],
          filter: {
            regex: '^[:].+$',
            match: false
          }
        },
        {
          selector: 'function',
          format: ['camelCase', 'PascalCase']
        },
        {
          selector: 'variable',
          format: ['camelCase', 'UPPER_CASE', 'PascalCase']
        },
        {
          selector: 'parameter',
          format: ['camelCase'],
          leadingUnderscore: 'allow'
        },
        {
          selector: 'memberLike',
          modifiers: ['private'],
          format: ['camelCase'],
          leadingUnderscore: 'require'
        },
        {
          selector: 'objectLiteralProperty',
          format: ['camelCase', 'snake_case', 'PascalCase', 'UPPER_CASE'],
          filter: {
            regex: '^[:].+$',
            match: false
          }
        },
        {
          selector: 'enumMember',
          format: ['PascalCase'],
        },
        {
          selector: 'typeLike',
          format: ['PascalCase']
        },
        {
          selector: 'import',
          format: ['camelCase', 'PascalCase']
        }
      ],
      'react-hooks/rules-of-hooks': 'warn',
      'react-hooks/exhaustive-deps': 'warn',
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/immutability': 'warn',
      'react-hooks/preserve-manual-memoization': 'warn',
      'react-refresh/only-export-components': 'warn',
      'no-useless-assignment': 'warn',
      'brace-style': 'off',
      '@stylistic/brace-style': ['error', '1tbs', { allowSingleLine: true }],
      'comma-spacing': 'off',
      '@stylistic/comma-spacing': ['error'],
      indent: 'off',
      '@stylistic/indent': ['error', 2],
      'default-param-last': 'off',
      '@typescript-eslint/default-param-last': ['error'],
      'no-unused-vars': ['off'],
      '@typescript-eslint/no-unused-vars': ['error', { vars: 'all', args: 'after-used', ignoreRestSiblings: false }],
      'init-declarations': 'off',
      '@typescript-eslint/init-declarations': ['error'],
      'keyword-spacing': 'off',
      '@stylistic/keyword-spacing': ['error'],
      'no-array-constructor': 'off',
      'no-dupe-class-members': 'off',
      '@typescript-eslint/no-dupe-class-members': ['error'],
      'no-duplicate-imports': ['error'],
      'no-empty-function': 'off',
      '@typescript-eslint/no-empty-function': ['error'],
      'no-extra-parens': 'off',
      '@stylistic/no-extra-parens': ['error'],
      'no-implied-eval': 'off',
      '@typescript-eslint/no-implied-eval': ['error'],
      'no-invalid-this': 'off',
      '@typescript-eslint/no-invalid-this': ['error'],
      'no-loop-func': 'off',
      '@typescript-eslint/no-loop-func': ['error'],
      'no-magic-numbers': 'off',
      '@typescript-eslint/no-magic-numbers': ['error', { ignoreArrayIndexes: true, enforceConst: true, detectObjects: true, ignoreEnums: true }],
      'no-redeclare': 'off',
      '@typescript-eslint/no-redeclare': ['error'],
      'no-throw-literal': ['error'],
      'no-unused-expressions': 'off',
      '@typescript-eslint/no-unused-expressions': ['error', { allowShortCircuit: false, allowTernary: false }],
      'no-use-before-define': 'off',
      '@typescript-eslint/no-use-before-define': ['error', { variables: true, functions: false, classes: false, enums: true, typedefs: true, ignoreTypeReferences: false }],
      'no-useless-constructor': 'off',
      '@typescript-eslint/no-useless-constructor': ['error'],
      'object-curly-spacing': 'off',
      '@stylistic/object-curly-spacing': ['error', 'always'],
      quotes: 'off',
      '@stylistic/quotes': ['error', 'single'],
      'require-await': 'off',
      '@typescript-eslint/require-await': ['error'],
      'no-return-await': 'off',
      '@typescript-eslint/return-await': ['error'],
      semi: 'off',
      '@stylistic/semi': ['error', 'always'],
      '@stylistic/member-delimiter-style': ['error', { multiline: { delimiter: 'comma', requireLast: true }, singleline: { delimiter: 'comma', requireLast: false } }],
      'space-infix-ops': 'off',
      '@stylistic/space-infix-ops': ['error', { int32Hint: false }],
      'dot-notation': 'off',
      '@typescript-eslint/dot-notation': ['error'],
      '@stylistic/space-before-blocks': ['error', 'always'],
      '@stylistic/space-in-parens': ['error', 'never'],
      '@stylistic/space-unary-ops': ['error', { words: true, nonwords: false }],
      '@stylistic/spaced-comment': ['error', 'always'],
      'constructor-super': ['error'],
      'no-const-assign': ['error'],
      'no-class-assign': ['error'],
      'no-this-before-super': ['error'],
      'no-useless-rename': ['error'],
      'no-delete-var': ['error'],
      'no-undef': ['off'],
      'no-undef-init': ['off'],
      '@stylistic/block-spacing': ['error', 'always'],
      'implicit-arrow-linebreak': 'off',
      '@stylistic/key-spacing': ['error', { afterColon: true }],
      '@stylistic/max-len': ['error', { code: 110 }],
      '@stylistic/no-mixed-spaces-and-tabs': ['error'],
      '@stylistic/no-trailing-spaces': ['error', { ignoreComments: true }],
      '@stylistic/no-whitespace-before-property': ['error'],
      '@stylistic/object-curly-newline': ['error', { multiline: true, consistent: true }],
      '@stylistic/quote-props': ['error', 'as-needed'],
      '@stylistic/semi-spacing': ['error', { before: false, after: true }],
      'no-async-promise-executor': ['error'],
      'no-await-in-loop': ['error'],
      'no-console': ['error'],
      'no-promise-executor-return': ['error'],
      'no-template-curly-in-string': ['error'],
      'no-unsafe-optional-chaining': ['error'],
      '@stylistic/linebreak-style': ['error', 'unix'],
      'accessor-pairs': ['error'],
      'array-callback-return': ['error'],
      'block-scoped-var': ['error'],
      'class-methods-use-this': ['off'],
      complexity: ['error', { max: 12 }],
      'consistent-return': ['error'],
      curly: ['error', 'all'],
      'default-case': ['off'],
      'default-case-last': ['error'],
      '@stylistic/dot-location': ['off'],
      eqeqeq: ['error'],
      'grouped-accessor-pairs': ['error'],
      'guard-for-in': ['error'],
      'max-classes-per-file': ['error', 1],
      'no-alert': ['error'],
      'no-caller': ['error'],
      'no-case-declarations': ['error'],
      'no-constructor-return': ['error'],
      'no-div-regex': ['error'],
      'no-else-return': ['error', { allowElseIf: true }],
      'no-empty-pattern': ['error'],
      'no-eq-null': ['error'],
      'no-eval': ['error'],
      'no-extend-native': ['error'],
      'no-extra-bind': ['error'],
      'no-extra-label': ['error'],
      'no-fallthrough': ['error'],
      '@stylistic/no-floating-decimal': ['error'],
      'no-global-assign': ['error'],
      'no-implicit-globals': ['error'],
      'no-implicit-coercion': ['off'],
      'no-iterator': ['error'],
      'no-labels': ['error'],
      'no-lone-blocks': ['error'],
      '@stylistic/no-multi-spaces': ['error'],
      'no-multi-str': ['error'],
      'no-new': ['off'],
      'no-new-func': ['error'],
      'no-new-wrappers': ['off'],
      'no-nonoctal-decimal-escape': ['error'],
      'no-octal': ['error'],
      'no-octal-escape': ['error'],
      'no-param-reassign': ['error'],
      'no-proto': ['error'],
      'no-return-assign': ['error'],
      'no-script-url': ['error'],
      'no-self-assign': ['error'],
      'no-self-compare': ['error'],
      'no-sequences': ['error'],
      'no-unmodified-loop-condition': ['error'],
      'no-unused-labels': ['error'],
      'no-useless-call': ['error'],
      'no-useless-catch': ['error'],
      'no-useless-concat': ['error'],
      'no-useless-escape': ['error'],
      'no-useless-return': ['error'],
      'no-void': ['error'],
      'no-warning-comments': ['error', { terms: ['fix'], location: 'start' }],
      'no-with': ['error'],
      'prefer-named-capture-group': ['error'],
      'prefer-promise-reject-errors': ['error', { allowEmptyReject: true }],
      'prefer-regex-literals': ['error'],
      radix: ['error'],
      'require-unicode-regexp': ['error'],
      'vars-on-top': ['error'],
      '@stylistic/wrap-iife': ['error'],
      yoda: ['error']
    }
  },
  {
    files: ['**/aws-exports.js'],
    rules: {
      '@stylistic/max-len': 'off'
    }
  }
];
