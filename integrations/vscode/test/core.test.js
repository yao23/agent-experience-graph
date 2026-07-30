const test = require('node:test');
const assert = require('node:assert/strict');
const {
  classifyFailure,
  estimateTokens,
  failureSignature,
  rankPlaybooks,
  redactSensitiveText
} = require('../out/core');

test('ranks timeout recovery for a Playwright timeout', () => {
  const ranked = rankPlaybooks(
    'Timeout 30000ms exceeded while waiting for getByRole("button", { name: "Submit" })'
  );
  assert.equal(ranked[0].playbook.id, 'playwright.timeout');
  assert.ok(ranked[0].confidence > 0.4);
});

test('ranks selector recovery for strict locator errors', () => {
  const ranked = rankPlaybooks(
    'locator.click: Error: strict mode violation: locator("button") resolved to 3 elements'
  );
  assert.equal(ranked[0].playbook.id, 'playwright.selector');
});

test('classifies CI-only failures', () => {
  assert.equal(
    classifyFailure('The Playwright test only fails headless in GitHub Actions on Linux CI'),
    'ci'
  );
});

test('redacts common secrets before creating signatures', () => {
  const value = 'Authorization: Bearer abc123 token=secret-value password=hunter2';
  const redacted = redactSensitiveText(value);
  assert.doesNotMatch(redacted, /abc123|secret-value|hunter2/);
  assert.match(redacted, /\[REDACTED\]/);
});

test('normalizes changing numbers in a failure signature', () => {
  const signature = failureSignature('Timeout 30000ms exceeded after 12345 milliseconds');
  assert.equal(signature, 'Timeout #ms exceeded after # milliseconds');
});

test('estimates non-zero tokens', () => {
  assert.equal(estimateTokens('abcd'), 1);
  assert.equal(estimateTokens('abcdefgh'), 2);
});
