function conditionCount(expression) {
  if (!expression) {
    return 0;
  }
  if (expression.type === 'LogicalExpression') {
    return conditionCount(expression.left) + conditionCount(expression.right);
  }
  if (expression.type === 'UnaryExpression') {
    return conditionCount(expression.argument);
  }
  return 1;
}

const reviewRules = {
  'simple-conditions': {
    meta: { schema: [] },
    create(context) {
      function check(node) {
        if (conditionCount(node.test) > 3) {
          context.report({
            node: node.test,
            message: 'Extract conditions into named checks; use at most three conditions.',
          });
        }
      }
      return {
        IfStatement: check,
        ForStatement: check,
        WhileStatement: check,
        DoWhileStatement: check,
        ConditionalExpression: check,
      };
    },
  },
  'no-nested-conditional': {
    meta: { schema: [] },
    create(context) {
      return {
        ConditionalExpression(node) {
          let parent = node.parent;
          while (parent) {
            if (
              ['FunctionDeclaration', 'FunctionExpression', 'ArrowFunctionExpression'].includes(
                parent.type,
              )
            ) {
              break;
            }
            if (parent.type === 'ConditionalExpression') {
              context.report({
                node,
                message: 'Extract the nested conditional into a named helper or statement.',
              });
              break;
            }
            parent = parent.parent;
          }
        },
      };
    },
  },
};

export default [
  {
    files: ['**/*.js', '**/*.mjs'],
    languageOptions: { ecmaVersion: 2022, sourceType: 'module' },
    plugins: { review: { rules: reviewRules } },
    rules: {
      curly: ['error', 'all'],
      'one-var': ['error', 'never'],
      'keyword-spacing': ['error', { before: true, after: true }],
      'space-before-blocks': ['error', 'always'],
      'space-infix-ops': 'error',
      'comma-spacing': 'error',
      'key-spacing': 'error',
      'max-statements-per-line': ['error', { max: 1 }],
      'no-nested-ternary': 'error',
      'review/no-nested-conditional': 'error',
      'review/simple-conditions': 'error',
    },
  },
  {
    files: ['**/static/*.js'],
    languageOptions: {
      globals: {
        document: 'readonly',
        window: 'readonly',
        location: 'readonly',
        history: 'readonly',
        navigator: 'readonly',
        URL: 'readonly',
        fetch: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
      },
    },
    rules: {
      'max-lines': ['error', { max: 400, skipBlankLines: false, skipComments: false }],
      'no-undef': 'error',
      'no-unused-vars': 'error',
    },
  },
];
