# Manual developer-validation sprint

Date prepared: 2026-08-28

Status: ready for a human founder to begin; no outreach or trial has started.

## Decision and evidence boundary

Autonomous experience-transfer experiments are paused. ETP-04 does not exist
and is not authorized. ETP-02 and ETP-03 remain terminal, and neither produced
a valid scientific conclusion.

Earlier exploratory evidence must not be generalized into claims of
product-market fit, cross-project transfer, statistical significance, general
AEG effectiveness, or product demand. The latest no-tool patch-pipeline result
was an operational authentication failure, not evidence for or against
experience-transfer effectiveness.

The next evidence target is developer pain and willingness to adopt, not
another harness result. This sprint is manual product discovery and concierge
validation. It is not an autonomous model experiment or a scientific
experiment arm.

## Registry launch alignment

The AEG Verified Experience Registry is now the primary self-service surface
for product-market-fit learning. Manual interviews and founder-led outreach
remain active, but they are a post-launch distribution and evidence channel,
not the product's critical path. After launch, each outreach message should
point to one relevant Experience Card instead of describing an abstract product.

The evidence thresholds below are unchanged. Two weeks after launch,
founder-only retrieval, copying, downloads, or replay activity is insufficient
evidence and must not justify expanding into community, social, reputation, or
marketplace features.

## Two-week founder timebox

Run the sprint for at most 14 calendar days from the human-selected start date
and spend no more than six focused founder hours in total.

| Activity | Maximum focused founder time | Output cap |
| --- | ---: | --- |
| Prepare and personalize outreach | 1 hour | 12 messages |
| Conduct discovery conversations | 2 hours | 3–5 conversations |
| Deliver manual concierge trials | 2 hours | At most 2 trials |
| Review evidence and write the decision memo | 1 hour | 1 short memo |

The operating limits are:

- exactly zero automated outreach;
- no more than 12 personalized outreach messages;
- 3–5 discovery conversations;
- at most two founder-led manual concierge trials;
- exactly zero autonomous model experiments.

A practical sequence is to personalize and send outreach early in the
timebox, use the middle days for conversations and any qualified concierge
trials, and reserve the final founder hour for an evidence-based decision.
Stop when either the 14-day duration or six-hour effort cap is reached.

## Initial customer profile

Prioritize individual developers and small engineering teams that:

- use AI coding agents regularly;
- encounter recurring CI, dependency, migration, deployment, or environment
  failures;
- lose time rediscovering earlier fixes;
- already preserve debugging knowledge in chat transcripts, issue trackers,
  runbooks, postmortems, or personal notes; and
- can share at least one sanitized historical failure artifact.

Do not record personal names, employers, private contact details, confidential
company information, or other identifying details in this public-safe sprint
document or its public outputs.

## Founder-led concierge offer

> Bring one recurring or expensive developer failure. We will convert the
> sanitized evidence into a compact, verified Experience Brief containing what
> was attempted, what failed, what worked, why it worked, and when it should or
> should not be reused. We will then evaluate whether that brief makes a similar
> future or replayed task faster, clearer, or less error-prone.

This is a founder-led, manual service used to learn about the workflow. It is
not a production product, an automated agent, or a promise that a Brief will
improve an outcome.

For each accepted concierge trial:

1. Obtain explicit permission to retain a sanitized historical artifact.
2. Agree on the recurring or replayed task and a useful observable measure,
   such as elapsed time, number of dead ends, errors avoided, or participant
   clarity.
3. Manually draft the Experience Brief from the supplied evidence, clearly
   separating observed facts, participant interpretation, and unknowns.
4. Ask the participant to verify factual accuracy, reuse conditions, and
   contraindications before attempting reuse.
5. Observe one similar future task or replay, record the agreed measure, and
   ask what changed in the participant's behavior or confidence.
6. Record objections and follow-up intent without treating compliments as
   demand evidence.

## Discovery conversation guide

Start with the workflow and pain; do not pitch the concierge offer before
understanding how the participant currently works.

1. What was the last costly or recurring engineering failure you handled?
2. Roughly how much time did it consume, and how many people were involved?
3. Where is the resolution stored now?
4. Has the same knowledge been needed again? What happened when it was?
5. What makes the existing documentation or history difficult to reuse?
6. What evidence would make a prior experience trustworthy enough to apply?
7. When should that experience expire, be ignored, or be explicitly rejected?
8. Who would use this capability, who would approve it, and who might purchase
   it?
9. Would you be willing to share one sanitized historical failure artifact?
10. Would you try a founder-created manual Experience Brief on a similar future
    or replayed task?
11. If it worked, what would you actually do next: request another Brief,
    recommend it, join a pilot, sign a letter of intent, or pay for it?

## Evidence ledger

Keep private raw evidence outside public reusable artifacts. Put only
anonymized, sanitized observations in a public-safe ledger. Do not add an entry
until the underlying interaction has occurred, and do not fabricate missing
values.

| Anonymized participant ID | Role/team type | Failure category | Frequency | Estimated time or cost | Current knowledge-storage method | Sanitized artifact supplied | Experience Brief created | Reuse or replay attempted | Measurable effect | Trust or privacy objection | Repeat-use intent | Payment or LOI signal | Strongest verbatim insight | Follow-up decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

For verbatim insights, obtain permission, remove identifying details, and
preserve the participant's meaning. Use `unknown` rather than guessing.

## Provisional decision thresholds

### `CONTINUE_CONCIERGE_VALIDATION`

This decision requires all of the following:

- at least three completed conversations;
- at least two participants describing a recurring, material problem;
- at least two sanitized real artifacts supplied;
- at least one completed concierge trial; and
- at least one strong behavior-based signal: a repeat request, referral, letter
  of intent, pilot commitment, or willingness to pay.

### `ITERATE_PROBLEM_OR_ICP`

Use this decision when pain exists but participants will not supply artifacts,
reuse the output, or identify a buyer. The next step must narrow or change the
problem, customer profile, trust model, or offer rather than count positive
comments as validation.

### `STOP_OR_DEPRIORITIZE`

Use this decision when conversations show that the problem is rare, already
solved adequately, too privacy-sensitive, or not valuable enough to change
behavior.

Interview compliments alone do not count as demand evidence.

## Outreach drafts

### Warm-contact message

Hi — I am learning how developers reuse hard-won fixes for recurring CI,
dependency, migration, deployment, and environment failures. Would you be open
to a 20-minute learning conversation about the last failure that cost you real
time and where that resolution lives now? If useful and safe, you can also
bring one sanitized historical artifact, but no proprietary code or sensitive
details are needed. This is early founder-led research, not a product pitch.

### Cold LinkedIn or email message

Hi — I am researching whether developers repeatedly lose time rediscovering
fixes that already exist in chats, issues, runbooks, or notes. Could I ask you
about your workflow in a 20-minute learning conversation? Optionally, if you
have a sanitized historical failure you can share safely, I would like to
understand what would make that experience reusable and trustworthy. This is a
manual early-stage study; I am not claiming a finished product or proven
outcomes.

Personalize either draft to the recipient's public context. Send messages
manually, one at a time, and stop at 12 total.

## Data handling

- Obtain explicit permission before retaining any participant artifact.
- Sanitize credentials, proprietary code, personal data, customer data, and
  internal identifiers before retention or use.
- Retain only the minimum information necessary for the agreed learning goal,
  and delete it when that purpose ends or permission is withdrawn.
- Publish participant-derived material only after the participant approves the
  exact public-safe form.
- Keep private raw evidence access-controlled and separate from public reusable
  Experience Briefs.
- Do not place raw participant artifacts, private contact details, or
  re-identifying combinations of facts in the public repository.

## End-of-sprint output

At the end of the timebox, write one short evidence-based decision memo. It
must answer:

1. Is the pain recurring and costly?
2. Will developers provide the necessary evidence?
3. Does the Experience Brief change behavior or outcomes?
4. Who is the buyer?
5. What is the narrowest promising workflow?
6. Should AEG continue, narrow its initial customer profile, change its offer,
   or deprioritize this direction?

The memo must distinguish observed behavior from interpretation, report
negative and missing evidence, apply one provisional decision threshold, and
avoid scientific or product-demand claims that the sprint did not establish.
