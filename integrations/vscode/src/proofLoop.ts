import {ExperienceRating, VerifiedExperienceMatch} from './verifiedExperience';

export type ProofLoopStage =
  | 'query-entered'
  | 'matched'
  | 'inspected'
  | 'copied'
  | 'validated'
  | 'rated'
  | 'abstained';

export type ValidationOutcome = 'passed' | 'partially-passed' | 'failed' | 'not-applied';

export interface ProofLoopSession {
  schemaVersion: '1.0.0';
  id: string;
  query: string;
  stage: ProofLoopStage;
  experienceId?: string;
  experienceTask?: string;
  retrievalScore?: number;
  validationOutcome?: ValidationOutcome;
  rating?: ExperienceRating;
}

export type ProofLoopEvent =
  | {type: 'match'; match: VerifiedExperienceMatch}
  | {type: 'abstain'}
  | {type: 'inspect'}
  | {type: 'copy'}
  | {type: 'validate'; outcome: ValidationOutcome}
  | {type: 'rate'; rating: ExperienceRating};

export function beginProofLoop(query: string, id: string): ProofLoopSession {
  const normalized = query.trim();
  if (!normalized) throw new Error('A proof-loop query is required.');
  if (!id.trim()) throw new Error('A proof-loop session ID is required.');
  return {
    schemaVersion: '1.0.0',
    id,
    query: normalized,
    stage: 'query-entered'
  };
}

export function transitionProofLoop(
  session: ProofLoopSession,
  event: ProofLoopEvent
): ProofLoopSession {
  if (session.stage === 'query-entered' && event.type === 'match') {
    return {
      ...session,
      stage: 'matched',
      experienceId: event.match.experience.id,
      experienceTask: event.match.experience.task,
      retrievalScore: event.match.score
    };
  }
  if (session.stage === 'query-entered' && event.type === 'abstain') {
    return {...session, stage: 'abstained'};
  }
  if (session.stage === 'matched' && event.type === 'inspect') {
    return {...session, stage: 'inspected'};
  }
  if (session.stage === 'inspected' && event.type === 'copy') {
    return {...session, stage: 'copied'};
  }
  if (session.stage === 'copied' && event.type === 'validate') {
    return {...session, stage: 'validated', validationOutcome: event.outcome};
  }
  if (session.stage === 'validated' && event.type === 'rate') {
    return {...session, stage: 'rated', rating: event.rating};
  }
  throw new Error(`Invalid proof-loop transition: ${session.stage} -> ${event.type}`);
}

export function proofLoopStep(stage: ProofLoopStage): number {
  if (stage === 'query-entered') return 1;
  if (stage === 'matched' || stage === 'inspected') return 2;
  if (stage === 'copied') return 3;
  if (stage === 'validated') return 4;
  if (stage === 'rated') return 5;
  return 2;
}
