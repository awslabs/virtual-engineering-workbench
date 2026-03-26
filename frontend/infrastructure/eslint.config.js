const {
    defineConfig,
    globalIgnores,
} = require("eslint/config");

const globals = require("globals");
const tsParser = require("@typescript-eslint/parser");
const typescriptEslint = require("@typescript-eslint/eslint-plugin");
const jest = require("eslint-plugin-jest");
const js = require("@eslint/js");
const stylistic = require('@stylistic/eslint-plugin');

const {
    FlatCompat,
} = require("@eslint/eslintrc");

const compat = new FlatCompat({
    baseDirectory: __dirname,
    recommendedConfig: js.configs.recommended,
    allConfig: js.configs.all
});

module.exports = defineConfig([{
    languageOptions: {
        globals: {
            ...globals.node,
            ...jest.environments.globals.globals,
        },

        parser: tsParser,
        ecmaVersion: 12,
        sourceType: "module",

        parserOptions: {
            project: "./tsconfig.eslint.json",
        },
    },

    extends: compat.extends(
        "eslint:recommended",
        "plugin:@typescript-eslint/recommended",
        "plugin:jest/recommended",
    ),

    plugins: {
        "@typescript-eslint": typescriptEslint,
        '@stylistic': stylistic,
        jest,
    },

    rules: {
        camelcase: "off",

        "@typescript-eslint/naming-convention": ["error", {
            selector: "default",
            format: ["camelCase"],
        }, {
            selector: "variable",
            format: ["camelCase", "UPPER_CASE"],
        }, {
            selector: "parameter",
            format: ["camelCase"],
            leadingUnderscore: "allow",
        }, {
            selector: "memberLike",
            modifiers: ["private"],
            format: ["camelCase"],
            leadingUnderscore: "require",
        }, {
            selector: "objectLiteralProperty",
            format: ["camelCase", "snake_case", "PascalCase"],
        }, {
            selector: "enumMember",
            format: ["PascalCase"],
        }, {
            selector: "typeLike",
            format: ["PascalCase"],
        }],

        "jest/expect-expect": ["error", {
            assertFunctionNames: ["expect", "expectCDK"],
        }],

        "brace-style": "off",

        "@stylistic/brace-style": ["error", "1tbs", {
            allowSingleLine: true,
        }],

        "comma-spacing": "off",
        "@stylistic/comma-spacing": ["error"],
        indent: "off",
        "@stylistic/indent": ["error", 2],
        "default-param-last": "off",
        "@typescript-eslint/default-param-last": ["error"],
        "no-unused-vars": ["off"],

        "@typescript-eslint/no-unused-vars": ["warn", {
            vars: "all",
            args: "after-used",
            ignoreRestSiblings: false,
        }],

        "init-declarations": "off",
        "@typescript-eslint/init-declarations": ["error"],
        "keyword-spacing": "off",
        "@stylistic/keyword-spacing": ["error"],
        "no-array-constructor": "off",
        "no-dupe-class-members": "off",
        "@typescript-eslint/no-dupe-class-members": ["error"],
        "no-duplicate-imports": "off",
        "no-duplicate-imports": ["error"],
        "no-empty-function": "off",
        "@typescript-eslint/no-empty-function": ["error"],
        "no-extra-parens": "off",
        "@stylistic/no-extra-parens": ["warn"],
        "no-implied-eval": "off",
        "@typescript-eslint/no-implied-eval": ["error"],
        "no-invalid-this": "off",
        "@typescript-eslint/no-invalid-this": ["error"],
        "no-loop-func": "off",
        "@typescript-eslint/no-loop-func": ["error"],
        "no-magic-numbers": "off",
        "@typescript-eslint/no-magic-numbers": "off",
        "no-redeclare": "off",
        "@typescript-eslint/no-redeclare": ["error"],
        "no-throw-literal": "off",
        "@typescript-eslint/only-throw-error": ["error"],
        "no-unused-expressions": "off",

        "@typescript-eslint/no-unused-expressions": ["error", {
            allowShortCircuit: false,
            allowTernary: false,
        }],

        "no-use-before-define": "off",

        "@typescript-eslint/no-use-before-define": ["error", {
            variables: true,
            functions: false,
            classes: false,
            enums: true,
            typedefs: true,
            ignoreTypeReferences: false,
        }],

        "no-useless-constructor": "off",
        "@typescript-eslint/no-useless-constructor": ["error"],
        "object-curly-spacing": "off",
        "@stylistic/object-curly-spacing": ["error", "always"],
        quotes: "off",
        "@stylistic/quotes": ["error", "single"],
        "require-await": "off",
        "@typescript-eslint/require-await": ["error"],
        "no-return-await": "off",
        "@typescript-eslint/return-await": ["error"],
        semi: "off",
        "@stylistic/semi": ["error", "always"],

        "@stylistic/member-delimiter-style": ["error", {
            multiline: {
                delimiter: "comma",
                requireLast: true,
            },

            singleline: {
                delimiter: "comma",
                requireLast: false,
            },
        }],

        "space-infix-ops": "off",

        "@stylistic/space-infix-ops": ["error", {
            int32Hint: false,
        }],

        "dot-notation": "off",
        "@typescript-eslint/dot-notation": ["error"],
        "space-before-blocks": ["error", "always"],
        "space-in-parens": ["error", "never"],

        "space-unary-ops": ["error", {
            words: true,
            nonwords: false,
        }],

        "spaced-comment": ["error", "always"],
        "constructor-super": ["error"],
        "no-const-assign": ["error"],
        "no-class-assign": ["error"],
        "no-this-before-super": ["error"],
        "no-useless-rename": ["error"],
        "no-delete-var": ["error"],
        "no-undef": ["warn"],
        "no-undef-init": ["warn"],
        "block-spacing": ["error", "always"],
        "implicit-arrow-linebreak": ["warn", "beside"],

        "key-spacing": ["warn", {
            afterColon: true,
        }],

        "max-len": ["warn", {
            code: 110,
        }],

        "no-mixed-spaces-and-tabs": ["error"],

        "no-trailing-spaces": ["error", {
            ignoreComments: true,
        }],

        "no-whitespace-before-property": ["error"],

        "object-curly-newline": ["error", {
            multiline: true,
            consistent: true,
        }],

        "quote-props": ["error", "as-needed"],

        "semi-spacing": ["error", {
            before: false,
            after: true,
        }],

        "no-async-promise-executor": ["warn"],
        "no-await-in-loop": ["warn"],
        "no-console": ["error"],
        "no-promise-executor-return": ["warn"],
        "no-template-curly-in-string": ["error"],
        "no-unsafe-optional-chaining": ["error"],
        "linebreak-style": ["error", "unix"],
        "accessor-pairs": ["error"],
        "array-callback-return": ["error"],
        "block-scoped-var": ["error"],
        "class-methods-use-this": ["warn"],

        complexity: ["error", {
            max: 6,
        }],

        "consistent-return": ["error"],
        curly: ["error", "all"],
        "default-case": ["off"],
        "default-case-last": ["error"],
        "dot-location": ["off"],
        eqeqeq: ["error"],
        "grouped-accessor-pairs": ["error"],
        "guard-for-in": ["warn"],
        "max-classes-per-file": ["error", 1],
        "no-alert": ["error"],
        "no-caller": ["error"],
        "no-case-declarations": ["error"],
        "no-constructor-return": ["error"],
        "no-div-regex": ["error"],

        "no-else-return": ["error", {
            allowElseIf: true,
        }],

        "no-empty-pattern": ["error"],
        "no-eq-null": ["error"],
        "no-eval": ["error"],
        "no-extend-native": ["error"],
        "no-extra-bind": ["error"],
        "no-extra-label": ["error"],
        "no-fallthrough": ["error"],
        "no-floating-decimal": ["error"],
        "no-global-assign": ["error"],
        "no-implicit-globals": ["error"],
        "no-implicit-coercion": ["off"],
        "no-iterator": ["error"],
        "no-labels": ["error"],
        "no-lone-blocks": ["error"],
        "no-multi-spaces": ["error"],
        "no-multi-str": ["error"],
        "no-new": ["off"],
        "no-new-func": ["error"],
        "no-new-wrappers": ["off"],
        "no-nonoctal-decimal-escape": ["error"],
        "no-octal": ["error"],
        "no-octal-escape": ["error"],
        "no-param-reassign": ["error"],
        "no-proto": ["error"],
        "no-return-assign": ["error"],
        "no-script-url": ["error"],
        "no-self-assign": ["error"],
        "no-self-compare": ["error"],
        "no-sequences": ["error"],
        "no-unmodified-loop-condition": ["warn"],
        "no-unused-labels": ["error"],
        "no-useless-call": ["error"],
        "no-useless-catch": ["error"],
        "no-useless-concat": ["error"],
        "no-useless-escape": ["error"],
        "no-useless-return": ["error"],
        "no-void": ["error"],

        "no-warning-comments": ["warn", {
            terms: ["todo", "fix"],
            location: "start",
        }],

        "no-with": ["error"],
        "prefer-named-capture-group": ["error"],

        "prefer-promise-reject-errors": ["error", {
            allowEmptyReject: true,
        }],

        "prefer-regex-literals": ["error"],
        radix: ["warn"],
        "require-unicode-regexp": ["error"],
        "vars-on-top": ["error"],
        "wrap-iife": ["error"],
        yoda: ["error"],
    },
}, globalIgnores(["cdk.out/**/*"])]);