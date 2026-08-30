"use strict";

const assert = require("node:assert/strict");
const { filterExperiences, matchesExperience, normalize } = require("../site.js");

const experiences = [
  {
    id: "repair-lab",
    search: "repair misleading telemetry duplicated jsonl events completed commands recovery",
    category: "Coding Agent CI",
    status: "CROSS_RUN_VERIFIED",
  },
  {
    id: "tornado",
    search: "websocket tcp_nodelay assertionerror stale stream protocol delegation",
    category: "Framework Regression",
    status: "LOCALLY_VERIFIED",
  },
];

assert.equal(normalize("  TCP_NODELAY "), "tcp_nodelay");
assert.equal(matchesExperience(experiences[1], "stale stream", "", ""), true);
assert.deepEqual(
  filterExperiences(experiences, "completed commands", "Coding Agent CI", "CROSS_RUN_VERIFIED").map(
    (experience) => experience.id,
  ),
  ["repair-lab"],
);
assert.deepEqual(
  filterExperiences(experiences, "", "Framework Regression", "LOCALLY_VERIFIED").map(
    (experience) => experience.id,
  ),
  ["tornado"],
);
assert.deepEqual(filterExperiences(experiences, "no such failure", "", ""), []);
assert.deepEqual(filterExperiences(experiences, "", "", ""), experiences);

console.log(JSON.stringify({ status: "passed", tests: 6 }));
