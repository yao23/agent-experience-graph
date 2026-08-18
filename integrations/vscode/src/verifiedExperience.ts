export type VerifiedOutcome = 'success' | 'partial' | 'failure';
export type ExperienceRating = 'helpful' | 'partially-helpful' | 'irrelevant' | 'harmful';

export interface VerifiedExperience {
  id: string;
  task: string;
  outcome: VerifiedOutcome;
  lessons: string[];
  subtasks?: Array<{
    description: string;
    lessons: string[];
  }>;
  constraints: string[];
  limitations: string[];
  reuse: {
    retrievalTags: string[];
    recommendedFor: string[];
  };
  verification: {
    status: 'passed' | 'partial' | 'failed';
  };
  provenance: {
    publicSource: {
      repository: string;
      buggyCommitSha: string;
      fixedCommitSha: string;
      license: string;
      benchmark: string;
    };
    experimentEvidence: {
      artifact: string;
    };
    publication: {
      pullRequest: string;
    };
  };
}

export interface MatchEvidence {
  field: 'task' | 'reuse.retrievalTags' | 'reuse.recommendedFor' | 'lessons' | 'subtasks.description' | 'subtasks.lessons';
  queryPhrase: string;
  experiencePhrase: string;
  lexicalScore: number;
  weightedContribution: number;
}

export interface VerifiedExperienceMatch {
  experience: VerifiedExperience;
  score: number;
  evidence: MatchEvidence[];
}

export interface LibraryLoadResult {
  experiences: VerifiedExperience[];
  malformed: string[];
}

export interface ExperienceFeedback {
  schemaVersion: '1.1.0';
  recordedAt: string;
  proofLoopSessionId: string;
  experienceId: string;
  experienceTask: string;
  taskSummary: string;
  rating: ExperienceRating;
  validationOutcome: 'passed' | 'partially-passed' | 'failed' | 'not-applied';
  retrievalScore: number;
  localOnly: true;
}

export interface VerifiedTaskFamily {
  id: string;
  label: string;
  description: string;
  experienceIds: string[];
}

export interface VerifiedLibraryCoverage {
  verifiedRecordCount: number;
  families: Array<VerifiedTaskFamily & {recordCount: number}>;
  uncoveredExperienceIds: string[];
}

export const VERIFIED_TASK_FAMILIES: VerifiedTaskFamily[] = [
  {
    id: 'agent-evaluation-integrity',
    label: 'Agent evaluation and telemetry integrity',
    description: 'Auditable repair experiments, event accounting, paired trials, and release validation.',
    experienceIds: ['trace-2026-08-03-repair-lab-ci-v0.1.3']
  },
  {
    id: 'delegation-api-contracts',
    label: 'Delegation and API contract repair',
    description: 'Stale resource ownership, thin proxy delegation, and focused public-surface contract tests.',
    experienceIds: ['trace-2026-08-03-tr-04-tornado-nodelay']
  }
];

const STOPWORDS = new Set(['a', 'an', 'and', 'build', 'create', 'for', 'from', 'in', 'into', 'of', 'or', 'run', 'the', 'to', 'while', 'with']);
const GENERIC_REPAIR_TERMS = new Set(['agent', 'failure', 'repair', 'test', 'verification']);
const OUTCOME_WEIGHT: Record<VerifiedOutcome, number> = {success: 1, partial: 0.75, failure: 0.35};
export const VERIFIED_EXPERIENCE_RETRIEVAL_THRESHOLD = 0.05;
export const SUPPLEMENTAL_EVIDENCE_CONTRIBUTION_CAP = 0.03;
export const VERIFIED_EXPERIENCE_FIELD_WEIGHT = {
  task: 0.27,
  'reuse.retrievalTags': 0.15,
  'reuse.recommendedFor': 0.18,
  lessons: 0.1,
  'subtasks.description': 0.08,
  'subtasks.lessons': 0.12
} as const;

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function stringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.length > 0 && value.every(item => typeof item === 'string' && item.trim().length > 0);
}

function validSubtasks(value: unknown): boolean {
  return value === undefined || (
    Array.isArray(value)
    && value.every(subtask => isObject(subtask)
      && typeof subtask.description === 'string'
      && subtask.description.trim().length > 0
      && stringArray(subtask.lessons))
  );
}

function isVerifiedExperience(value: unknown): value is VerifiedExperience {
  if (!isObject(value)) return false;
  const reuse = value.reuse;
  const verification = value.verification;
  const provenance = value.provenance;
  if (!isObject(reuse) || !isObject(verification) || !isObject(provenance)) return false;
  const publicSource = provenance.publicSource;
  const experimentEvidence = provenance.experimentEvidence;
  const publication = provenance.publication;
  return typeof value.id === 'string'
    && value.id.startsWith('trace-')
    && typeof value.task === 'string'
    && value.task.trim().length > 0
    && (value.outcome === 'success' || value.outcome === 'partial' || value.outcome === 'failure')
    && stringArray(value.lessons)
    && validSubtasks(value.subtasks)
    && stringArray(value.constraints)
    && stringArray(value.limitations)
    && stringArray(reuse.retrievalTags)
    && stringArray(reuse.recommendedFor)
    && (verification.status === 'passed' || verification.status === 'partial' || verification.status === 'failed')
    && isObject(publicSource)
    && typeof publicSource.repository === 'string'
    && typeof publicSource.buggyCommitSha === 'string'
    && typeof publicSource.fixedCommitSha === 'string'
    && typeof publicSource.license === 'string'
    && typeof publicSource.benchmark === 'string'
    && isObject(experimentEvidence)
    && typeof experimentEvidence.artifact === 'string'
    && isObject(publication)
    && typeof publication.pullRequest === 'string';
}

export function loadVerifiedExperienceLibrary(raw: string): LibraryLoadResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return {experiences: [], malformed: ['library is not valid JSON']};
  }
  if (!Array.isArray(parsed)) return {experiences: [], malformed: ['library root must be an array']};
  const experiences: VerifiedExperience[] = [];
  const malformed: string[] = [];
  const ids = new Set<string>();
  parsed.forEach((record, index) => {
    if (!isVerifiedExperience(record)) {
      malformed.push(`record ${index + 1} is malformed`);
      return;
    }
    if (ids.has(record.id)) {
      malformed.push(`record ${index + 1} duplicates ${record.id}`);
      return;
    }
    ids.add(record.id);
    experiences.push(record);
  });
  return {experiences, malformed};
}

export function summarizeVerifiedLibraryCoverage(
  experiences: VerifiedExperience[]
): VerifiedLibraryCoverage {
  const availableIds = new Set(experiences.map(experience => experience.id));
  const coveredIds = new Set<string>();
  const families = VERIFIED_TASK_FAMILIES
    .map(family => {
      const experienceIds = family.experienceIds.filter(id => availableIds.has(id));
      experienceIds.forEach(id => coveredIds.add(id));
      return {...family, experienceIds, recordCount: experienceIds.length};
    })
    .filter(family => family.recordCount > 0);
  return {
    verifiedRecordCount: experiences.length,
    families,
    uncoveredExperienceIds: experiences
      .map(experience => experience.id)
      .filter(id => !coveredIds.has(id))
      .sort()
  };
}

function tokenValues(value: string): string[] {
  const tokens = value.toLowerCase().match(/[a-z0-9_:+.-]+/g) ?? [];
  return tokens.filter(token => !STOPWORDS.has(token));
}

function tokenize(value: string): Set<string> {
  return new Set(tokenValues(value));
}

function similarity(left: string, right: string): number {
  const leftTokens = tokenize(left);
  const rightTokens = tokenize(right);
  if (!leftTokens.size || !rightTokens.size) return 0;
  let intersection = 0;
  let meaningfulIntersection = 0;
  for (const token of leftTokens) {
    if (!rightTokens.has(token)) continue;
    intersection += 1;
    if (!GENERIC_REPAIR_TERMS.has(token)) meaningfulIntersection += 1;
  }
  if (!meaningfulIntersection) return 0;
  return intersection / new Set([...leftTokens, ...rightTokens]).size;
}

function bestPhrase(query: string, phrases: string[]): {phrase: string; score: number} {
  return phrases.reduce(
    (best, phrase) => {
      const score = similarity(query, phrase);
      return score > best.score ? {phrase, score} : best;
    },
    {phrase: '', score: 0}
  );
}

function overlappingQueryPhrase(query: string, experiencePhrase: string): string {
  const experienceTokens = tokenize(experiencePhrase);
  return [...new Set(tokenValues(query).filter(token => experienceTokens.has(token)))].join(' ');
}

function evidence(
  field: MatchEvidence['field'],
  queryPhrase: string,
  experiencePhrase: string,
  score: number,
  outcomeWeight: number
): MatchEvidence {
  return {
    field,
    queryPhrase,
    experiencePhrase,
    lexicalScore: Number(score.toFixed(4)),
    weightedContribution: Number((VERIFIED_EXPERIENCE_FIELD_WEIGHT[field] * score * outcomeWeight).toFixed(4))
  };
}

function bestSupplementalEvidence(
  query: string,
  experience: VerifiedExperience,
  outcomeWeight: number
): MatchEvidence | undefined {
  const candidates: Array<{field: MatchEvidence['field']; phrases: string[]}> = [
    {field: 'lessons', phrases: experience.lessons},
    {field: 'subtasks.description', phrases: experience.subtasks?.map(subtask => subtask.description) ?? []},
    {field: 'subtasks.lessons', phrases: experience.subtasks?.flatMap(subtask => subtask.lessons) ?? []}
  ];
  let best: MatchEvidence | undefined;
  for (const candidate of candidates) {
    const match = bestPhrase(query, candidate.phrases);
    if (match.score <= 0) continue;
    const item = evidence(
      candidate.field,
      overlappingQueryPhrase(query, match.phrase),
      match.phrase,
      match.score,
      outcomeWeight
    );
    if (!best || item.weightedContribution > best.weightedContribution) best = item;
  }
  if (best) {
    best.weightedContribution = Math.min(best.weightedContribution, SUPPLEMENTAL_EVIDENCE_CONTRIBUTION_CAP);
  }
  return best;
}

export function rankVerifiedExperiences(
  task: string,
  experiences: VerifiedExperience[],
  minScore = VERIFIED_EXPERIENCE_RETRIEVAL_THRESHOLD,
  limit = 3
): VerifiedExperienceMatch[] {
  const query = task.trim();
  if (!query) return [];
  return experiences
    .map(experience => {
      const outcomeWeight = OUTCOME_WEIGHT[experience.outcome];
      const taskScore = similarity(query, experience.task);
      const tag = bestPhrase(query, experience.reuse.retrievalTags);
      const recommended = bestPhrase(query, experience.reuse.recommendedFor);
      const supplemental = bestSupplementalEvidence(query, experience, outcomeWeight);
      const score = outcomeWeight * (
        VERIFIED_EXPERIENCE_FIELD_WEIGHT.task * taskScore
        + VERIFIED_EXPERIENCE_FIELD_WEIGHT['reuse.retrievalTags'] * tag.score
        + VERIFIED_EXPERIENCE_FIELD_WEIGHT['reuse.recommendedFor'] * recommended.score
      ) + (supplemental?.weightedContribution ?? 0);
      const matched: MatchEvidence[] = [];
      if (taskScore > 0) matched.push(evidence('task', overlappingQueryPhrase(query, experience.task), experience.task, taskScore, outcomeWeight));
      if (tag.score > 0) matched.push(evidence('reuse.retrievalTags', overlappingQueryPhrase(query, tag.phrase), tag.phrase, tag.score, outcomeWeight));
      if (recommended.score > 0) matched.push(evidence('reuse.recommendedFor', overlappingQueryPhrase(query, recommended.phrase), recommended.phrase, recommended.score, outcomeWeight));
      if (supplemental) matched.push(supplemental);
      return {
        experience,
        score: Number(score.toFixed(4)),
        evidence: matched.sort((left, right) => right.weightedContribution - left.weightedContribution)
      };
    })
    .filter(match => match.score >= minScore)
    .sort((left, right) => right.score - left.score || left.experience.id.localeCompare(right.experience.id))
    .slice(0, limit);
}

export function describeBelowThresholdMatch(
  match: VerifiedExperienceMatch,
  threshold = VERIFIED_EXPERIENCE_RETRIEVAL_THRESHOLD
): string {
  const strongest = match.evidence[0];
  return `AEG abstained. Best verified record: “${match.experience.task}” `
    + `(score ${match.score.toFixed(4)}; threshold ${threshold.toFixed(4)}). `
    + `Strongest evidence: ${strongest.field} matched query terms “${strongest.queryPhrase}” `
    + `to “${strongest.experiencePhrase}”. Below retrieval threshold—not recommended. `
    + 'No candidate or fallback guidance was injected.';
}

export function generateRecoveryCapsule(match: VerifiedExperienceMatch): string {
  const experience = match.experience;
  const source = experience.provenance.publicSource;
  const lines = [
    'AEG VERIFIED EXPERIENCE — GUIDANCE, NOT A GUARANTEED ANSWER',
    `Applicable context: ${experience.task}`,
    `Validated outcome: ${experience.outcome}; verification ${experience.verification.status}.`,
    'Reusable lessons:',
    ...experience.lessons.slice(0, 4).map(lesson => `- ${lesson}`),
    'Recommended use cases:',
    ...experience.reuse.recommendedFor.slice(0, 3).map(item => `- ${item}`),
    'Constraints and limitations:',
    ...[...experience.constraints.slice(0, 2), ...experience.limitations.slice(0, 2)].map(item => `- ${item}`),
    `Public provenance: ${source.repository} (${source.license}; ${source.benchmark})`,
    'Instruction: Use this experience only as a hypothesis. Inspect the local code, reproduce the failure, and validate any repair with focused and regression tests.'
  ];
  return lines.join('\n');
}

export function appendExperienceFeedback(raw: string, feedback: ExperienceFeedback): ExperienceFeedback[] {
  let existing: unknown = [];
  try {
    existing = raw.trim() ? JSON.parse(raw) : [];
  } catch {
    existing = [];
  }
  const rows = Array.isArray(existing) ? existing.filter(isObject) as unknown as ExperienceFeedback[] : [];
  return [...rows, feedback];
}
