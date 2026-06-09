module.exports = {
  enlidea: {
    input: {
      target: 'http://localhost:8000/api/schema/',
    },
    output: {
      mode: 'single',
      target: 'src/api/generated/api.ts',
      client: 'react-query',
      mock: false,
      override: {
        useTypeOverInterfaces: true,
        mutator: {
          path: './src/api/mutator/custom-instance.js',
          name: 'customInstance',
        },
      },
    },
  },
};
