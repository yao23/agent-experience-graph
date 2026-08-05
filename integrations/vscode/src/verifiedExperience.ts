export type VerifiedOutcome = 'success' | 'partial' | 'failure';
export type ExperienceRating = 'helpful' | 'partially-helpful' | 'irrelevant' | 'harmful';

export interface VerifiedExperience {
  id: string;
  task: string;
  outcome: VerifiedOutcome;
  lessons: string[];
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
  field: 'task' | 'reuse.retrievalTags' | 'reuse.recommendedFor';
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
  schemaVersion: '1.0.0';
  recordedAt: string;
  experienceId: string;
  taskSummary: string;
  rating: ExperienceRating;
  retrievalScore: number;
  localOnly: true;
}

const STOPWORDS = new Set(['a', 'an', 'and', 'build', 'create', 'for', 'from', 'in', 'into', 'of', 'or', 'the', 'to', 'with']);
const OUTCOME_WEIGHT: Record<VerifiedOutcome, number> = {success: 1, partial: 0.75, failure: 0.35};
const FIELD_WEIGHT = {
  task: 0.27,
  'reuse.retrievalTags': 0.15,
  'reuse.recommendedFor': 0.18
} as const;

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function stringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.length > 0 && value.every(item => typeof item === 'string' && item.trim().length > 0);
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

function tokenize(value: string): Set<string> {
  const tokens = value.toLowerCase().match(/[a-z0-9_:+.-]+/g) ?? [];
  return new Set(tokens.filter(token => !STOPWORDS.has(token)));
}

function similarity(left: string, right: string): number {
  const leftTokens = tokenize(left);
  const rightTokens = tokenize(right);
  if (!leftTokens.size || !rightTokens.size) return 0;
  let intersection = 0;
  for (const token of leftTokens) if (rightTokens.has(token)) intersection += 1;
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
    weightedContribution: Number((FIELD_WEIGHT[field] * score * outcomeWeight).toFixed(4))
  };
}

export function rankVerifiedExperiences(
  task: string,
  experiences: VerifiedExperience[],
  minScore = 0.05,
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
      const score = outcomeWeight * (
        FIELD_WEIGHT.task * taskScore
        + FIELD_WEIGHT['reuse.retrievalTags'] * tag.score
        + FIELD_WEIGHT['reuse.recommendedFor'] * recommended.score
      );
      const matched: MatchEvidence[] = [];
      if (taskScore > 0) matched.push(evidence('task', query, experience.task, taskScore, outcomeWeight));
      if (tag.score > 0) matched.push(evidence('reuse.retrievalTags', query, tag.phrase, tag.score, outcomeWeight));
      if (recommended.score > 0) matched.push(evidence('reuse.recommendedFor', query, recommended.phrase, recommended.score, outcomeWeight));
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
