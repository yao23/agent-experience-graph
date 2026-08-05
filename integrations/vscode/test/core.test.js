const test = require('node:test');
const assert = require('node:assert/strict');
const {
  classifyFailure,
  estimateTokens,
  failureSignature,
  rankPlaybooks,
  redactSensitiveText
} = require('../out/core');
const {
  appendExperienceFeedback,
  generateRecoveryCapsule,
  loadVerifiedExperienceLibrary,
  rankVerifiedExperiences
} = require('../out/verifiedExperience');
const fs = require('node:fs');
const path = require('node:path');

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

const bundledLibrary = () => loadVerifiedExperienceLibrary(
  fs.readFileSync(path.resolve(__dirname, '..', 'verified-experiences', 'verified.json'), 'utf8')
);

test('packages the original 256px Marketplace icon', () => {
  const extensionRoot = path.resolve(__dirname, '..');
  const manifest = JSON.parse(fs.readFileSync(path.join(extensionRoot, 'package.json'), 'utf8'));
  assert.equal(manifest.icon, 'images/icon.png');
  const icon = fs.readFileSync(path.join(extensionRoot, manifest.icon));
  assert.deepEqual([...icon.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  assert.equal(icon.readUInt32BE(16), 256);
  assert.equal(icon.readUInt32BE(20), 256);
});

test('loads only the bundled verified library', () => {
  const loaded = bundledLibrary();
  assert.deepEqual(loaded.malformed, []);
  assert.equal(loaded.experiences.length, 2);
  assert.ok(loaded.experiences.every(experience => experience.verification.status === 'passed'));
  assert.ok(loaded.experiences.every(experience => !experience.id.includes('am-01')));
});

test('ranks verified experiences with explainable weighted evidence', () => {
  const matches = rankVerifiedExperiences(
    'A public wrapper control still uses stale resource ownership instead of delegating through its protocol',
    bundledLibrary().experiences
  );
  assert.equal(matches[0].experience.id, 'trace-2026-08-03-tr-04-tornado-nodelay');
  assert.ok(matches[0].score >= 0.05);
  assert.ok(matches[0].evidence.some(item => item.field === 'reuse.recommendedFor'));
  assert.ok(matches[0].evidence.every(item => item.queryPhrase && item.experiencePhrase && item.lexicalScore > 0));
});

test('bundled zero-cold-start challenge retrieves TR-04 above its frozen threshold', () => {
  const challenge = JSON.parse(fs.readFileSync(
    path.resolve(__dirname, '..', '..', '..', 'experiments', 'verified-experience-challenge', 'challenge.json'),
    'utf8'
  ));
  const matches = rankVerifiedExperiences(
    challenge.taskPrompt,
    bundledLibrary().experiences,
    challenge.retrievalThreshold
  );
  assert.equal(matches[0].experience.id, challenge.expectedVerifiedExperienceId);
  assert.ok(matches[0].score >= challenge.retrievalThreshold);
  assert.equal(challenge.classification, 'synthetic-transfer-demo');
  assert.equal(challenge.priorResult.outcomeChanged, false);
  assert.equal(challenge.priorResult.repairPathChanged, false);
});

test('generates a compact guarded recovery capsule', () => {
  const match = rankVerifiedExperiences('repair stale resource ownership behind a protocol', bundledLibrary().experiences)[0];
  const capsule = generateRecoveryCapsule(match);
  assert.match(capsule, /GUIDANCE, NOT A GUARANTEED ANSWER/);
  assert.match(capsule, /validate any repair with focused and regression tests/);
  assert.ok(capsule.length < 4000);
});

test('handles malformed libraries and no-match queries', () => {
  assert.deepEqual(loadVerifiedExperienceLibrary('{broken'), {experiences: [], malformed: ['library is not valid JSON']});
  const malformed = loadVerifiedExperienceLibrary('[{"id":"candidate-only"}]');
  assert.equal(malformed.experiences.length, 0);
  assert.equal(malformed.malformed.length, 1);
  assert.deepEqual(rankVerifiedExperiences('optimize watercolor pigment drying schedule', bundledLibrary().experiences), []);
});

test('appends local usefulness feedback and recovers from malformed feedback', () => {
  const feedback = {
    schemaVersion: '1.0.0',
    recordedAt: '2026-08-04T00:00:00Z',
    experienceId: 'trace-test',
    taskSummary: 'test task',
    rating: 'helpful',
    retrievalScore: 0.12,
    localOnly: true
  };
  assert.deepEqual(appendExperienceFeedback('', feedback), [feedback]);
  assert.deepEqual(appendExperienceFeedback('{broken', feedback), [feedback]);
});
