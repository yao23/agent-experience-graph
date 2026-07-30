export type OutcomeStatus = 'unknown' | 'resolved' | 'unresolved';

export interface RecoveryPlaybook {
  id: string;
  name: string;
  summary: string;
  signals: string[];
  steps: string[];
}

export interface RankedPlaybook {
  playbook: RecoveryPlaybook;
  confidence: number;
  matchedSignals: string[];
}

export interface ExperienceReceipt {
  schemaVersion: '0.1.1';
  id: string;
  recordedAt: string;
  intent: {
    summary: string;
  };
  context: {
    framework: 'playwright';
    workspace: string;
    source: 'selection' | 'active-file' | 'artifact' | 'pasted';
    platform: string;
    repository?: string;
    branch?: string;
    artifactPath?: string;
  };
  steps: Array<{
    at: string;
    action: string;
    detail?: string;
  }>;
  skills: Array<{
    id: string;
    name: string;
    version: string;
    confidence: number;
  }>;
  artifacts: Array<{
    kind: string;
    path?: string;
    redacted: boolean;
  }>;
  failures: Array<{
    category: string;
    signature: string;
    message: string;
  }>;
  recovery: Array<{
    playbookId: string;
    steps: string[];
    status: 'suggested' | 'attempted' | 'completed';
  }>;
  outcome: {
    status: OutcomeStatus;
    verification?: string;
    completedAt?: string;
  };
  cost: {
    estimatedTokens: number;
    durationMs: number;
    retries: number;
  };
  privacy: {
    localOnly: true;
    containsRawCode: false;
    shared: false;
  };
}

export const PLAYWRIGHT_PLAYBOOKS: RecoveryPlaybook[] = [
  {
    id: 'playwright.timeout',
    name: 'Diagnose Playwright timeouts',
    summary: 'Separate slow application behavior, missing readiness signals, and an incorrect wait condition.',
    signals: ['timeout', 'timed out', 'exceeded', 'waiting for', 'slow', '30000ms', 'locator.waitfor'],
    steps: [
      'Open the Playwright trace and identify the last successful action.',
      'Confirm the application readiness signal instead of increasing the timeout first.',
      'Replace fixed sleeps with a web-first assertion or a precise response/UI condition.',
      'Re-run the single test with tracing enabled and compare the failing step.'
    ]
  },
  {
    id: 'playwright.selector',
    name: 'Repair unstable selectors',
    summary: 'Replace ambiguous, generated, or implementation-coupled selectors with resilient user-facing locators.',
    signals: ['locator', 'selector', 'strict mode', 'resolved to', 'element not found', 'getbyrole', 'getbytestid', 'visible'],
    steps: [
      'Inspect the target in the trace or locator picker.',
      'Prefer getByRole, getByLabel, or another user-facing locator.',
      'Remove nth(), generated classes, or broad text matches when a stable contract exists.',
      'Add a focused assertion and re-run the test at least three times.'
    ]
  },
  {
    id: 'playwright.auth',
    name: 'Recover authentication and session state',
    summary: 'Validate storage state, cookies, redirects, and environment-specific authentication setup.',
    signals: ['login', 'auth', 'unauthorized', 'forbidden', '401', '403', 'storage state', 'cookie', 'redirect'],
    steps: [
      'Check whether the expected storageState file exists and matches the current environment.',
      'Inspect redirects and cookie domains in the trace.',
      'Regenerate authentication state through a dedicated setup project.',
      'Avoid sharing user-specific state across parallel workers.'
    ]
  },
  {
    id: 'playwright.network',
    name: 'Diagnose network and API mocking failures',
    summary: 'Find unmatched routes, stale fixtures, response timing issues, and backend dependencies.',
    signals: ['route', 'request', 'response', 'api', 'network', 'fetch', 'xhr', '500', '502', 'mock'],
    steps: [
      'Inspect failed and pending requests in the trace.',
      'Verify route patterns and register mocks before navigation.',
      'Check fixture shape and status codes against the application contract.',
      'Wait on the specific response or UI effect, then re-run.'
    ]
  },
  {
    id: 'playwright.flaky',
    name: 'Isolate a flaky Playwright test',
    summary: 'Distinguish shared state, timing, ordering, and parallelism failures using repeatable evidence.',
    signals: ['flaky', 'retry', 'intermittent', 'sometimes', 'parallel', 'race', 'repeat-each', 'workers'],
    steps: [
      'Re-run the test with --repeat-each and one worker.',
      'Compare traces from a passing and failing attempt.',
      'Remove shared mutable data and make setup/cleanup test-scoped.',
      'Record the smallest condition that changes the outcome.'
    ]
  },
  {
    id: 'playwright.browser',
    name: 'Investigate browser-specific behavior',
    summary: 'Compare rendering, permissions, events, and browser engine behavior without masking the difference.',
    signals: ['chromium', 'firefox', 'webkit', 'browser', 'safari', 'permission', 'viewport', 'mobile'],
    steps: [
      'Run the same test in one browser project at a time.',
      'Compare screenshots, console errors, and network behavior.',
      'Check browser-specific permissions, input events, and viewport assumptions.',
      'Keep a targeted compatibility guard only when behavior is intentionally different.'
    ]
  },
  {
    id: 'playwright.test-data',
    name: 'Repair test-data isolation',
    summary: 'Remove collisions and stale state by making test data unique, scoped, and cleanly disposable.',
    signals: ['duplicate', 'already exists', 'data', 'database', 'cleanup', 'seed', 'conflict', 'unique'],
    steps: [
      'Identify data shared by parallel tests or previous runs.',
      'Generate unique identifiers per test and worker.',
      'Create data through a stable API or fixture and clean it deterministically.',
      'Re-run in parallel to verify isolation.'
    ]
  },
  {
    id: 'playwright.ci',
    name: 'Resolve CI-only Playwright failures',
    summary: 'Compare runtime, dependencies, resources, URLs, and environment values between CI and local runs.',
    signals: ['ci', 'github actions', 'jenkins', 'headless', 'container', 'linux', 'pipeline', 'only fails'],
    steps: [
      'Record Playwright, browser, Node, OS, and dependency versions in CI.',
      'Compare environment variables, baseURL, resource limits, and service readiness.',
      'Upload trace, screenshot, video, and console output for the failed retry.',
      'Reproduce with the same container and command before changing timeouts.'
    ]
  },
  {
    id: 'playwright.trace',
    name: 'Read Playwright traces and artifacts',
    summary: 'Turn screenshots, traces, videos, console messages, and error context into a minimal failure signature.',
    signals: ['trace.zip', 'error-context', 'screenshot', 'video', 'console', 'artifact', 'snapshot'],
    steps: [
      'Open trace.zip with the Playwright trace viewer.',
      'Find the first action whose observed state differs from the expected state.',
      'Capture the error, locator, URL, console, and relevant network evidence.',
      'Use that minimal signature to select a more specific recovery playbook.'
    ]
  },
  {
    id: 'playwright.accessibility',
    name: 'Repair accessibility test failures',
    summary: 'Fix the accessible contract instead of weakening role, label, or automated accessibility assertions.',
    signals: ['accessibility', 'aria', 'axe', 'role', 'label', 'accessible name', 'wcag'],
    steps: [
      'Inspect the reported rule and affected DOM node.',
      'Fix the semantic element, role, label, focus order, or contrast at the source.',
      'Keep role/name locators aligned with the corrected accessible contract.',
      'Re-run both the focused assertion and the accessibility scan.'
    ]
  }
];

const SECRET_PATTERNS: Array<[RegExp, string]> = [
  [/(authorization\s*[:=]\s*)(bearer\s+)?[^\s"'`]+/gi, '$1[REDACTED]'],
  [/(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*["']?[^"'\s,}]+/gi, '$1=[REDACTED]'],
  [/https?:\/\/[^@\s]+@/gi, 'https://[REDACTED]@']
];

export function redactSensitiveText(value: string, maxLength = 8000): string {
  let redacted = value.slice(0, maxLength);
  for (const [pattern, replacement] of SECRET_PATTERNS) {
    redacted = redacted.replace(pattern, replacement);
  }
  return redacted;
}

export function classifyFailure(value: string): string {
  const ranked = rankPlaybooks(value);
  return ranked[0]?.playbook.id.replace('playwright.', '') ?? 'unknown';
}

export function rankPlaybooks(value: string): RankedPlaybook[] {
  const normalized = value.toLowerCase();
  return PLAYWRIGHT_PLAYBOOKS
    .map(playbook => {
      const matchedSignals = playbook.signals.filter(signal => normalized.includes(signal.toLowerCase()));
      const confidence = Math.min(0.98, matchedSignals.length === 0 ? 0.08 : 0.3 + (matchedSignals.length * 0.14));
      return {playbook, confidence, matchedSignals};
    })
    .sort((a, b) => b.confidence - a.confidence || a.playbook.name.localeCompare(b.playbook.name));
}

export function failureSignature(value: string): string {
  return redactSensitiveText(value, 480)
    .replace(/\d{2,}/g, '#')
    .replace(/\s+/g, ' ')
    .trim();
}

export function estimateTokens(value: string): number {
  return Math.max(1, Math.ceil(value.length / 4));
}
