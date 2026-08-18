const assert = require('node:assert/strict');
const test = require('node:test');
const {
  FOUNDER_FIRST_RUN_VERSION,
  PRIMARY_ENTRY_STATUS_TEXT,
  openFounderWalkthroughOnFirstRun,
  reopenFounderWalkthrough
} = require('../out/firstRun');

class MemoryStorage {
  constructor(marker, failUpdates = false) {
    this.marker = marker;
    this.failUpdates = failUpdates;
    this.updates = [];
  }

  get() {
    return this.marker;
  }

  async update(marker) {
    this.updates.push(marker);
    if (this.failUpdates) throw new Error('storage unavailable');
    this.marker = marker;
  }
}

const at = value => () => new Date(value);

test('first activation in a workspace opens and persists the versioned marker', async () => {
  const storage = new MemoryStorage();
  let opens = 0;
  const result = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: true,
    storage,
    openSurface: async () => { opens += 1; },
    now: at('2026-08-14T12:00:00.000Z')
  });

  assert.equal(result, 'opened');
  assert.equal(opens, 1);
  assert.equal(storage.updates[0].status, 'opening');
  assert.deepEqual(storage.marker, {
    version: FOUNDER_FIRST_RUN_VERSION,
    status: 'opened',
    attemptedAt: '2026-08-14T12:00:00.000Z',
    openedAt: '2026-08-14T12:00:00.000Z'
  });
});

test('second activation does not reopen a successfully opened walkthrough', async () => {
  const storage = new MemoryStorage({
    version: FOUNDER_FIRST_RUN_VERSION,
    status: 'opened',
    attemptedAt: '2026-08-14T12:00:00.000Z',
    openedAt: '2026-08-14T12:00:00.000Z'
  });
  let opens = 0;
  const result = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: true,
    storage,
    openSurface: async () => { opens += 1; },
    now: at('2026-08-14T12:01:00.000Z')
  });

  assert.equal(result, 'already-opened');
  assert.equal(opens, 0);
  assert.equal(storage.updates.length, 0);
});

test('a marker from another onboarding version does not suppress this version', async () => {
  const storage = new MemoryStorage({
    version: '0.1.6-founder-proof-loop.0',
    status: 'opened',
    attemptedAt: '2026-08-14T12:00:00.000Z',
    openedAt: '2026-08-14T12:00:00.000Z'
  });
  let opens = 0;
  const result = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: true,
    storage,
    openSurface: async () => { opens += 1; },
    now: at('2026-08-14T12:01:00.000Z')
  });

  assert.equal(result, 'opened');
  assert.equal(opens, 1);
  assert.equal(storage.marker.version, FOUNDER_FIRST_RUN_VERSION);
});

test('manual reopen always opens and refreshes the marker', async () => {
  const storage = new MemoryStorage({
    version: FOUNDER_FIRST_RUN_VERSION,
    status: 'opened',
    attemptedAt: '2026-08-14T12:00:00.000Z',
    openedAt: '2026-08-14T12:00:00.000Z'
  });
  let opens = 0;
  const result = await reopenFounderWalkthrough(
    storage,
    async () => { opens += 1; },
    at('2026-08-14T12:02:00.000Z')
  );

  assert.equal(result, 'opened');
  assert.equal(opens, 1);
  assert.equal(storage.marker.openedAt, '2026-08-14T12:02:00.000Z');
});

test('a failed auto-open is marked failed and retried on the next activation', async () => {
  const storage = new MemoryStorage();
  let opens = 0;
  const failed = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: true,
    storage,
    openSurface: async () => {
      opens += 1;
      throw new Error('workbench command unavailable');
    },
    now: at('2026-08-14T12:00:00.000Z')
  });

  assert.equal(failed, 'failed');
  assert.equal(storage.marker.status, 'failed');

  const retried = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: true,
    storage,
    openSurface: async () => { opens += 1; },
    now: at('2026-08-14T12:00:10.000Z')
  });

  assert.equal(retried, 'opened');
  assert.equal(opens, 2);
  assert.equal(storage.marker.status, 'opened');
});

test('a recent opening marker suppresses duplicate windows but a stale marker retries', async () => {
  const storage = new MemoryStorage({
    version: FOUNDER_FIRST_RUN_VERSION,
    status: 'opening',
    attemptedAt: '2026-08-14T12:00:00.000Z'
  });
  let opens = 0;
  const concurrent = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: true,
    storage,
    openSurface: async () => { opens += 1; },
    now: at('2026-08-14T12:00:30.000Z')
  });
  assert.equal(concurrent, 'opening-in-another-window');
  assert.equal(opens, 0);

  const recovered = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: true,
    storage,
    openSurface: async () => { opens += 1; },
    now: at('2026-08-14T12:01:01.000Z')
  });
  assert.equal(recovered, 'opened');
  assert.equal(opens, 1);
});

test('empty-window activation leaves no marker so the next workspace activation can open', async () => {
  const storage = new MemoryStorage();
  let opens = 0;
  const skipped = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: false,
    storage,
    openSurface: async () => { opens += 1; }
  });
  assert.equal(skipped, 'skipped-no-workspace');
  assert.equal(storage.marker, undefined);

  const opened = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: true,
    storage,
    openSurface: async () => { opens += 1; },
    now: at('2026-08-14T12:00:00.000Z')
  });
  assert.equal(opened, 'opened');
  assert.equal(opens, 1);
});

test('marker persistence failure never blocks opening or rejects startup', async () => {
  const storage = new MemoryStorage(undefined, true);
  let opens = 0;
  const result = await openFounderWalkthroughOnFirstRun({
    hasWorkspace: true,
    storage,
    openSurface: async () => { opens += 1; },
    now: at('2026-08-14T12:00:00.000Z')
  });
  assert.equal(result, 'opened-unpersisted');
  assert.equal(opens, 1);
});

test('failed manual reopen preserves a prior opened marker', async () => {
  const openedMarker = {
    version: FOUNDER_FIRST_RUN_VERSION,
    status: 'opened',
    attemptedAt: '2026-08-14T12:00:00.000Z',
    openedAt: '2026-08-14T12:00:00.000Z'
  };
  const storage = new MemoryStorage(openedMarker);
  const result = await reopenFounderWalkthrough(
    storage,
    async () => { throw new Error('workbench command unavailable'); },
    at('2026-08-14T12:02:00.000Z')
  );
  assert.equal(result, 'failed');
  assert.equal(storage.marker, openedMarker);
  assert.equal(storage.updates.length, 0);
});

test('primary fallback status text is a direct first-user action', () => {
  assert.equal(PRIMARY_ENTRY_STATUS_TEXT, '$(play) AEG: Start here');
});
