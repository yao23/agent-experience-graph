const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const Ajv2020 = require('ajv/dist/2020');

const experimentRoot = path.resolve(
  __dirname,
  '..',
  '..',
  '..',
  'experiments',
  'v0.1.6-product-proof'
);
const readJson = name => JSON.parse(fs.readFileSync(path.join(experimentRoot, name), 'utf8'));
const validator = schema => new Ajv2020({allErrors: true, strict: false}).compile(schema);
const sha = character => character.repeat(64);

function armResult(arm) {
  return {
    arm,
    success: true,
    attempts: 1,
    commands: {completed: 4, sanitized: ['inspect focused failure', 'run focused check']},
    tests: {
      executions: 2,
      focused: {commandSha256: sha('1'), status: 'passed'},
      regression: {commandSha256: sha('2'), status: 'passed'}
    },
    nonCachedTokens: 1200,
    durationMs: 42000,
    files: {inspected: ['src/example.py'], changed: ['src/example.py']},
    patchHash: sha('3'),
    settings: {
      model: 'frozen-model',
      settingsSha256: sha('4'),
      promptTemplateSha256: sha('5'),
      budgetSha256: sha('6'),
      oracleSha256: sha('7')
    },
    protocolDeviation: null
  };
}

function completedResult() {
  return {
    schemaVersion: '1.0.0',
    protocolId: 'aeg-v0.1.6-product-proof',
    taskId: 'public-task-01',
    recordedAt: '2026-08-12T00:00:00Z',
    outcome: 'completed',
    sourceExperience: {
      id: 'trace-example',
      recordedAt: '2026-08-01T00:00:00Z',
      predatesTarget: true,
      librarySha256: sha('8'),
      capsuleSha256: sha('9')
    },
    retrieval: {
      decision: 'top-1',
      score: 0.12,
      threshold: 0.05,
      matchedFields: ['task', 'reuse.recommendedFor']
    },
    armResults: [armResult('baseline'), armResult('fixed-generic'), armResult('aeg-top-1')],
    decision: 'neutral',
    limitations: ['One task and one run per arm cannot support a generalized causal claim.'],
    privacy: {
      containsCode: false,
      containsPrompts: false,
      containsTaskText: false,
      containsRawLogs: false,
      containsRatings: false,
      containsReceipts: false,
      containsPrivateData: false
    }
  };
}

test('prepared protocol validates and remains explicitly non-executable', () => {
  const protocol = readJson('protocol.json');
  const validate = validator(readJson('protocol.schema.json'));
  assert.equal(validate(protocol), true, JSON.stringify(validate.errors));
  assert.equal(protocol.status, 'prepared-not-frozen');
  assert.equal(protocol.executionAuthorized, false);
  assert.equal(protocol.execution.executeInThisRelease, false);
  assert.deepEqual(protocol.arms.map(arm => arm.id), ['baseline', 'fixed-generic', 'aeg-top-1']);
  assert.equal(protocol.arms[0].aegLibraryAccess, false);
  assert.equal(protocol.arms[1].aegLibraryAccess, false);
  assert.ok(Object.values(protocol.freeze.target).every(value => value === null));
  const advice = fs.readFileSync(path.join(experimentRoot, 'generic-advice.txt'));
  assert.equal(
    crypto.createHash('sha256').update(advice).digest('hex'),
    protocol.freeze.controls.genericAdviceSha256
  );
});

test('result schema accepts an exact three-arm completed result', () => {
  const validate = validator(readJson('result.schema.json'));
  const result = completedResult();
  assert.equal(validate(result), true, JSON.stringify(validate.errors));
});

test('result schema rejects missing measurements and arm-order changes', () => {
  const validate = validator(readJson('result.schema.json'));
  const missingCommands = completedResult();
  delete missingCommands.armResults[0].commands;
  assert.equal(validate(missingCommands), false);

  const wrongOrder = completedResult();
  wrongOrder.armResults.reverse();
  assert.equal(validate(wrongOrder), false);
});

test('result schema accepts abstention with no executed arms and rejects post-abstention arms', () => {
  const validate = validator(readJson('result.schema.json'));
  const result = completedResult();
  result.outcome = 'retrieval-abstention';
  result.sourceExperience = null;
  result.retrieval = {decision: 'abstain', score: 0.02, threshold: 0.05, matchedFields: ['lessons']};
  result.armResults = [];
  result.decision = 'abstention';
  assert.equal(validate(result), true, JSON.stringify(validate.errors));
  result.armResults = [armResult('baseline')];
  assert.equal(validate(result), false);
});
