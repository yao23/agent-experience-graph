# Eligibility checklist

A future task is eligible only when every required item is `yes` before
diagnosis:

- [ ] Ownership and authorization to analyze the supplied material are clear.
- [ ] The task contains no unnecessary personal, proprietary, regulated, or
      credential material.
- [ ] A bounded local reproduction exists.
- [ ] A deterministic objective oracle can be frozen before diagnosis.
- [ ] Source freshness and default-branch state were checked.
- [ ] Issue timelines, fork PRs, closed/draft/rejected PRs, commits, backlinks,
      contributor branches, and global defect/patch searches were checked.
- [ ] No existing correct repair owns the contribution path.
- [ ] AEG can be queried before diagnosis without revealing a known repair.
- [ ] License and provenance permit the planned local analysis.
- [ ] Compute, model, token, time, and human budgets are bounded.
- [ ] Requested output fits a separately approved phase.

Automatic rejection conditions include required secrets, production writes,
unclear IP rights, unavailable oracle, active correct repair, prohibited data,
or any need for unapproved external contact. Phase 0 itself authorizes no task
intake or real repair.
