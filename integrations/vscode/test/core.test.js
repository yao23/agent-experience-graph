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
  SUPPLEMENTAL_EVIDENCE_CONTRIBUTION_CAP,
  VERIFIED_EXPERIENCE_FIELD_WEIGHT,
  VERIFIED_EXPERIENCE_RETRIEVAL_THRESHOLD,
  appendExperienceFeedback,
  describeBelowThresholdMatch,
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
  assert.deepEqual(
    loaded.experiences.map(experience => experience.id).sort(),
    ['trace-2026-08-03-repair-lab-ci-v0.1.3', 'trace-2026-08-03-tr-04-tornado-nodelay']
  );
  assert.ok(loaded.experiences.every(experience => experience.verification.status === 'passed'));
  assert.deepEqual(
    JSON.parse(fs.readFileSync(path.resolve(__dirname, '..', 'verified-experiences', 'verified.json'), 'utf8')),
    JSON.parse(fs.readFileSync(path.resolve(__dirname, '..', '..', '..', 'experiences', 'verified.json'), 'utf8'))
  );
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
  assert.ok(matches[0].evidence.every(item => item.queryPhrase !== 'A public wrapper control still uses stale resource ownership instead of delegating through its protocol'));
});

const verificationQueries = [
  {
    task: 'A public wrapper method still references an old stream after ownership moved behind a protocol object. Trace the delegation path and restore the API behavior.',
    expectedId: 'trace-2026-08-03-tr-04-tornado-nodelay'
  },
  {
    task: 'The complete test suite passes, but the repair may target the wrong API surface. Add a focused contract test beginning at the public caller.',
    expectedId: 'trace-2026-08-03-tr-04-tornado-nodelay'
  },
  {
    task: 'Our agent telemetry counts both command-started and command-completed events, causing duplicated command metrics in JSONL results.',
    expectedId: 'trace-2026-08-03-repair-lab-ci-v0.1.3'
  },
  {
    task: 'Design a repeatable A/B benchmark comparing a baseline coding agent with an experience-assisted agent while reporting both improvements and regressions.',
    expectedId: 'trace-2026-08-03-repair-lab-ci-v0.1.3'
  }
];

test('retrieves the expected verified experience for all four applicable verification queries', () => {
  const experiences = bundledLibrary().experiences;
  for (const scenario of verificationQueries) {
    const matches = rankVerifiedExperiences(scenario.task, experiences);
    assert.equal(matches[0]?.experience.id, scenario.expectedId, scenario.task);
    assert.ok(matches[0].score >= VERIFIED_EXPERIENCE_RETRIEVAL_THRESHOLD);
  }
});

test('abstains at score zero for the unrelated website navigation query', () => {
  const task = 'Change the website navigation background from white to blue and increase the logo size.';
  assert.deepEqual(rankVerifiedExperiences(task, bundledLibrary().experiences), []);
  assert.ok(rankVerifiedExperiences(task, bundledLibrary().experiences, 0).every(match => match.score === 0));
});

test('produces deterministic rankings and evidence for repeated executions', () => {
  const experiences = bundledLibrary().experiences;
  for (const scenario of verificationQueries) {
    const expected = rankVerifiedExperiences(scenario.task, experiences, 0);
    for (let attempt = 0; attempt < 10; attempt += 1) {
      assert.deepEqual(rankVerifiedExperiences(scenario.task, experiences, 0), expected);
    }
  }
});

test('uses only the single best capped lesson or subtask contribution', () => {
  assert.deepEqual(VERIFIED_EXPERIENCE_FIELD_WEIGHT, {
    task: 0.27,
    'reuse.retrievalTags': 0.15,
    'reuse.recommendedFor': 0.18,
    lessons: 0.1,
    'subtasks.description': 0.08,
    'subtasks.lessons': 0.12
  });
  assert.equal(SUPPLEMENTAL_EVIDENCE_CONTRIBUTION_CAP, 0.03);
  const experiences = bundledLibrary().experiences;
  const scenario = verificationQueries[1];
  const original = rankVerifiedExperiences(scenario.task, experiences, 0)[0];
  const duplicated = structuredClone(experiences);
  const target = duplicated.find(experience => experience.id === scenario.expectedId);
  target.lessons = Array(100).fill(target.lessons).flat();
  target.subtasks = Array(100).fill(target.subtasks).flat();
  const repeated = rankVerifiedExperiences(scenario.task, duplicated, 0)[0];
  assert.equal(repeated.score, original.score);
  const supplemental = repeated.evidence.filter(item => item.field === 'lessons' || item.field.startsWith('subtasks.'));
  assert.equal(supplemental.length, 1);
  assert.ok(supplemental[0].weightedContribution <= SUPPLEMENTAL_EVIDENCE_CONTRIBUTION_CAP);
});

test('generic repair vocabulary cannot cross the retrieval threshold by itself', () => {
  const experiences = bundledLibrary().experiences;
  const queries = [
    'test failure agent repair verification',
    'test the agent',
    'repair the failure',
    'run verification'
  ];
  for (const task of queries) {
    assert.deepEqual(rankVerifiedExperiences(task, experiences), [], task);
  }
});

test('unrelated technical queries reliably abstain', () => {
  const experiences = bundledLibrary().experiences;
  const queries = [
    'Change CSS navigation colors from white to blue.',
    'Optimize a PostgreSQL database index for a slow multi-column query.',
    'Implement mobile authentication with biometric login and refresh tokens.',
    'Resize uploaded images while preserving aspect ratio and EXIF orientation.'
  ];
  for (const task of queries) {
    assert.deepEqual(rankVerifiedExperiences(task, experiences), [], task);
  }
});

test('describes a nonzero near-match without recommending it', () => {
  const task = 'Document public provenance for an example.';
  const nearMatch = rankVerifiedExperiences(task, bundledLibrary().experiences, Number.EPSILON, 1)[0];
  assert.ok(nearMatch.score > 0 && nearMatch.score < VERIFIED_EXPERIENCE_RETRIEVAL_THRESHOLD);
  const description = describeBelowThresholdMatch(nearMatch);
  assert.match(description, /Best verified record:/);
  assert.match(description, /score \d\.\d{4}; threshold 0\.0500/);
  assert.match(description, /Strongest evidence:/);
  assert.match(description, /Below retrieval threshold—not recommended/);
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
