#!/usr/bin/env python3
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


OUTCOME_WEIGHT = {
    "success": 1.0,
    "partial": 0.75,
    "failure": 0.35,
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "build",
    "create",
    "for",
    "from",
    "in",
    "into",
    "of",
    "or",
    "the",
    "to",
    "with",
}

FIELD_WEIGHTS = {
    "task": 0.27,
    "subtasks": 0.28,
    "reuse.retrievalTags": 0.15,
    "reuse.recommendedFor": 0.18,
    "skills": 0.035,
    "tools": 0.035,
    "constraints": 0.05,
}


def tokenize(value):
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return {
        token
        for token in re.findall(r"[a-z0-9_:+.-]+", str(value).lower())
        if token not in STOPWORDS
    }


def similarity(left, right):
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def load_json_arg(value):
    stripped = value.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(stripped)
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(stripped)


def load_traces(path):
    trace_path = Path(path)
    if not trace_path.exists():
        return []
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Trace library must be a JSON array.")
    return data


def save_traces(path, traces):
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(json.dumps(traces, indent=2) + "\n", encoding="utf-8")


def normalize_subtasks(record):
    subtasks = record.get("subtasks", [])
    normalized = []
    for item in subtasks:
        if isinstance(item, str):
            normalized.append({"description": item})
        elif isinstance(item, dict):
            normalized.append(item)
    return normalized


def best_phrase_match(query_phrase, candidates):
    best_score = 0.0
    best_phrase = ""
    for candidate in candidates:
        score = similarity(query_phrase, candidate)
        if score > best_score:
            best_score = score
            best_phrase = str(candidate)
    return best_score, best_phrase


def field_evidence(field, query_phrase, trace_phrase, score):
    return {
        "field": field,
        "query": str(query_phrase),
        "trace": str(trace_phrase),
        "similarity": round(score, 4),
        "contribution": round(FIELD_WEIGHTS[field] * score, 4),
    }


def trace_score(query, trace):
    task_score = similarity(query.get("task", ""), trace.get("task", ""))
    evidence = []
    if task_score > 0:
        evidence.append(field_evidence("task", query.get("task", ""), trace.get("task", ""), task_score))
    query_subtasks = normalize_subtasks(query)
    trace_subtasks = normalize_subtasks(trace)

    subtask_scores = []
    matched_pairs = []
    for query_subtask in query_subtasks:
        q_desc = query_subtask.get("description", "")
        best_score = 0.0
        best_trace_subtask = None
        for trace_subtask in trace_subtasks:
            score = similarity(q_desc, trace_subtask.get("description", ""))
            if score > best_score:
                best_score = score
                best_trace_subtask = trace_subtask
        if best_trace_subtask:
            subtask_scores.append(best_score)
            matched_pairs.append((query_subtask, best_trace_subtask, best_score))
            if best_score > 0:
                evidence.append(
                    field_evidence(
                        "subtasks",
                        q_desc,
                        best_trace_subtask.get("description", ""),
                        best_score,
                    )
                )

    average_subtask_score = (
        sum(subtask_scores) / len(subtask_scores) if subtask_scores else 0.0
    )
    skill_score = similarity(query.get("skills", []), trace.get("skills", []))
    tool_score = similarity(query.get("tools", []), trace.get("tools", []))
    if skill_score > 0:
        evidence.append(field_evidence("skills", query.get("skills", []), trace.get("skills", []), skill_score))
    if tool_score > 0:
        evidence.append(field_evidence("tools", query.get("tools", []), trace.get("tools", []), tool_score))

    reuse = trace.get("reuse", {}) if isinstance(trace.get("reuse", {}), dict) else {}
    query_task = query.get("task", "")
    tag_score, matched_tag = best_phrase_match(query_task, reuse.get("retrievalTags", []))
    recommended_score, matched_recommendation = best_phrase_match(query_task, reuse.get("recommendedFor", []))
    if tag_score > 0:
        evidence.append(field_evidence("reuse.retrievalTags", query_task, matched_tag, tag_score))
    if recommended_score > 0:
        evidence.append(field_evidence("reuse.recommendedFor", query_task, matched_recommendation, recommended_score))

    constraint_scores = []
    for query_constraint in query.get("constraints", []):
        constraint_score, matched_constraint = best_phrase_match(query_constraint, trace.get("constraints", []))
        if constraint_score > 0:
            constraint_scores.append(constraint_score)
            evidence.append(field_evidence("constraints", query_constraint, matched_constraint, constraint_score))
    constraint_score = sum(constraint_scores) / len(constraint_scores) if constraint_scores else 0.0
    outcome = str(trace.get("outcome", "")).lower()
    outcome_weight = OUTCOME_WEIGHT.get(outcome, 0.5)

    raw_score = (
        FIELD_WEIGHTS["task"] * task_score
        + FIELD_WEIGHTS["subtasks"] * average_subtask_score
        + FIELD_WEIGHTS["reuse.retrievalTags"] * tag_score
        + FIELD_WEIGHTS["reuse.recommendedFor"] * recommended_score
        + FIELD_WEIGHTS["skills"] * skill_score
        + FIELD_WEIGHTS["tools"] * tool_score
        + FIELD_WEIGHTS["constraints"] * constraint_score
    )
    weighted_score = raw_score * outcome_weight
    for item in evidence:
        item["weighted_contribution"] = round(item["contribution"] * outcome_weight, 4)
    return weighted_score, matched_pairs, evidence


def recommend(query, traces, limit, min_score):
    ranked = []
    skill_evidence = defaultdict(list)
    tool_evidence = defaultdict(list)
    lesson_evidence = []

    for trace in traces:
        score, matched_pairs, evidence = trace_score(query, trace)
        if score < min_score:
            continue
        ranked.append(
            {
                "id": trace.get("id", "unknown"),
                "task": trace.get("task", ""),
                "outcome": trace.get("outcome", ""),
                "score": round(score, 4),
                "evidence": sorted(
                    evidence,
                    key=lambda item: item["weighted_contribution"],
                    reverse=True,
                ),
                "matched_subtasks": [
                    {
                        "query": query_subtask.get("description", ""),
                        "trace": trace_subtask.get("description", ""),
                        "score": round(pair_score, 4),
                    }
                    for query_subtask, trace_subtask, pair_score in matched_pairs
                    if pair_score > 0
                ],
            }
        )

        evidence_id = trace.get("id", "unknown")
        for _, trace_subtask, pair_score in matched_pairs:
            if pair_score <= 0:
                continue
            for skill in trace_subtask.get("skills", []):
                skill_evidence[skill].append((score * pair_score, evidence_id))
            for tool in trace_subtask.get("tools", []):
                tool_evidence[tool].append((score * pair_score, evidence_id))
            for lesson in trace_subtask.get("lessons", []):
                lesson_evidence.append((score * pair_score, evidence_id, lesson))

        for skill in trace.get("skills", []):
            skill_evidence[skill].append((score * 0.25, evidence_id))
        for tool in trace.get("tools", []):
            tool_evidence[tool].append((score * 0.25, evidence_id))
        for lesson in trace.get("lessons", []):
            lesson_evidence.append((score * 0.25, evidence_id, lesson))

    ranked.sort(key=lambda item: item["score"], reverse=True)

    def summarize_counter(evidence):
        rows = []
        for name, hits in evidence.items():
            total = sum(value for value, _ in hits)
            sources = sorted({source for _, source in hits})
            rows.append(
                {
                    "name": name,
                    "score": round(total, 4),
                    "evidence": sources[:5],
                }
            )
        return sorted(rows, key=lambda item: item["score"], reverse=True)

    lessons = []
    seen_lessons = set()
    for score, source, lesson in sorted(lesson_evidence, reverse=True):
        key = (source, lesson)
        if key in seen_lessons:
            continue
        seen_lessons.add(key)
        lessons.append({"lesson": lesson, "score": round(score, 4), "evidence": source})
        if len(lessons) >= limit:
            break

    return {
        "matches": ranked[:limit],
        "recommended_skills": summarize_counter(skill_evidence)[:limit],
        "recommended_tools": summarize_counter(tool_evidence)[:limit],
        "lessons": lessons,
    }


def append_trace(traces_path, new_trace_arg):
    traces = load_traces(traces_path)
    new_trace = load_json_arg(new_trace_arg)
    if not isinstance(new_trace, dict):
        raise ValueError("New trace must be a JSON object.")
    if not new_trace.get("id") or not new_trace.get("task") or not new_trace.get("outcome"):
        raise ValueError("New trace requires id, task, and outcome.")
    traces = [trace for trace in traces if trace.get("id") != new_trace["id"]]
    traces.append(new_trace)
    save_traces(traces_path, traces)
    return {"appended": new_trace["id"], "trace_count": len(traces)}


def main():
    parser = argparse.ArgumentParser(
        description="Recommend agent skills and tools from prior execution traces."
    )
    parser.add_argument("--traces", required=True, help="Path to a JSON trace library.")
    parser.add_argument("--query", help="JSON string or path for the current task query.")
    parser.add_argument("--append-trace", help="JSON string or path for a trace to append.")
    parser.add_argument("--top", type=int, default=5, help="Number of recommendations.")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.05,
        help="Minimum trace score to include in recommendations.",
    )
    args = parser.parse_args()

    if args.append_trace:
        print(json.dumps(append_trace(args.traces, args.append_trace), indent=2))
        return

    if not args.query:
        parser.error("--query is required unless --append-trace is provided")

    query = load_json_arg(args.query)
    if not isinstance(query, dict):
        raise ValueError("Query must be a JSON object.")
    traces = load_traces(args.traces)
    print(json.dumps(recommend(query, traces, args.top, args.min_score), indent=2))


if __name__ == "__main__":
    main()
