module.exports = {
  enlidea: {
    input: {
      target: './openapi.yml',
    },
    output: {
      mode: 'single',
      target: 'src/api/generated/api.ts',
      client: 'react-query',
      mock: false,
      override: {
        useTypeOverInterfaces: true,
        useNativeEnums: true,
        header: () => `// @ts-nocheck\n/* eslint-disable */\n`,
        mutator: {
          path: './src/api/mutator/custom-instance.ts',
          name: 'customInstance',
        },
      },
    },
  },
};
