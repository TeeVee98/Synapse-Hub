const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    baseUrl: 'https://staging-shop.example.com',
    specPattern: 'cypress/e2e/**/*.cy.js',
    supportFile: false,
    viewportWidth: 1920,
    viewportHeight: 1080,
    video: false,
    screenshotOnRunFailure: true,
  },
});
