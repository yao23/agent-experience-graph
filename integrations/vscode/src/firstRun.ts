export const FOUNDER_FIRST_RUN_MARKER_KEY = 'aeg.firstRun.founderProofWalkthrough';
export const FOUNDER_FIRST_RUN_VERSION = '0.1.6-founder-proof-loop.1';
export const FOUNDER_WALKTHROUGH_ID =
  'AgentExperienceGraph.agent-experience-graph#aegFounderProofLoop';
export const PRIMARY_ENTRY_STATUS_TEXT = '$(play) AEG: Start here';

const OPENING_MARKER_STALE_AFTER_MS = 60_000;

export type FounderFirstRunStatus = 'opening' | 'opened' | 'failed';

export interface FounderFirstRunMarker {
  version: string;
  status: FounderFirstRunStatus;
  attemptedAt: string;
  openedAt?: string;
}

export interface FounderFirstRunStorage {
  get(): unknown;
  update(marker: FounderFirstRunMarker): Thenable<void>;
}

export type FounderFirstRunResult =
  | 'skipped-no-workspace'
  | 'already-opened'
  | 'opening-in-another-window'
  | 'opened'
  | 'opened-unpersisted'
  | 'failed';

interface FounderFirstRunOptions {
  hasWorkspace: boolean;
  storage: FounderFirstRunStorage;
  openSurface: () => Thenable<unknown>;
  now?: () => Date;
}

function markerFor(value: unknown): FounderFirstRunMarker | undefined {
  if (!value || typeof value !== 'object') return undefined;
  const marker = value as Partial<FounderFirstRunMarker>;
  if (
    marker.version !== FOUNDER_FIRST_RUN_VERSION ||
    (marker.status !== 'opening' && marker.status !== 'opened' && marker.status !== 'failed') ||
    typeof marker.attemptedAt !== 'string'
  ) {
    return undefined;
  }
  return marker as FounderFirstRunMarker;
}

function isRecentOpening(marker: FounderFirstRunMarker, now: Date): boolean {
  if (marker.status !== 'opening') return false;
  const attemptedAt = Date.parse(marker.attemptedAt);
  const age = now.getTime() - attemptedAt;
  return Number.isFinite(attemptedAt) && age >= 0 && age < OPENING_MARKER_STALE_AFTER_MS;
}

async function persistBestEffort(
  storage: FounderFirstRunStorage,
  marker: FounderFirstRunMarker
): Promise<boolean> {
  try {
    await storage.update(marker);
    return true;
  } catch {
    return false;
  }
}

export async function openFounderWalkthroughOnFirstRun(
  options: FounderFirstRunOptions
): Promise<FounderFirstRunResult> {
  if (!options.hasWorkspace) return 'skipped-no-workspace';

  const now = options.now?.() ?? new Date();
  let marker: FounderFirstRunMarker | undefined;
  try {
    marker = markerFor(options.storage.get());
  } catch {
    // A failed read is treated as missing state so onboarding remains recoverable.
  }

  if (marker?.status === 'opened') return 'already-opened';
  if (marker && isRecentOpening(marker, now)) return 'opening-in-another-window';

  const attemptedAt = now.toISOString();
  await persistBestEffort(options.storage, {
    version: FOUNDER_FIRST_RUN_VERSION,
    status: 'opening',
    attemptedAt
  });

  try {
    await options.openSurface();
  } catch {
    await persistBestEffort(options.storage, {
      version: FOUNDER_FIRST_RUN_VERSION,
      status: 'failed',
      attemptedAt
    });
    return 'failed';
  }

  const persisted = await persistBestEffort(options.storage, {
    version: FOUNDER_FIRST_RUN_VERSION,
    status: 'opened',
    attemptedAt,
    openedAt: (options.now?.() ?? new Date()).toISOString()
  });
  return persisted ? 'opened' : 'opened-unpersisted';
}

export async function reopenFounderWalkthrough(
  storage: FounderFirstRunStorage,
  openSurface: () => Thenable<unknown>,
  now: () => Date = () => new Date()
): Promise<FounderFirstRunResult> {
  const attemptedAt = now().toISOString();
  try {
    await openSurface();
  } catch {
    // Preserve any prior opened marker. Manual failure must not re-arm auto-open.
    return 'failed';
  }

  const persisted = await persistBestEffort(storage, {
    version: FOUNDER_FIRST_RUN_VERSION,
    status: 'opened',
    attemptedAt,
    openedAt: now().toISOString()
  });
  return persisted ? 'opened' : 'opened-unpersisted';
}
