(() => {
  const TRACKED_EVENTS = new Set([
    "experience_search",
    "experience_view",
    "use_with_agent_copy",
    "json_download",
    "replay_feedback_open",
    "experience_submission_open",
  ]);

  const normalize = (value) => String(value || "").trim().toLowerCase();

  const matchesExperience = (experience, query, category, status) => {
    const normalizedQuery = normalize(query);
    const queryMatches =
      !normalizedQuery || normalize(experience.search).includes(normalizedQuery);
    const categoryMatches = !category || experience.category === category;
    const statusMatches = !status || experience.status === status;
    return queryMatches && categoryMatches && statusMatches;
  };

  const filterExperiences = (experiences, query, category, status) =>
    experiences.filter((experience) =>
      matchesExperience(experience, query, category, status),
    );

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { filterExperiences, matchesExperience, normalize };
  }

  if (typeof document === "undefined") return;

  const analyticsAdapter =
    window.aegAnalytics && typeof window.aegAnalytics.track === "function"
      ? window.aegAnalytics
      : { track: () => {} };

  const emitEvent = (name, detail = {}) => {
    if (!TRACKED_EVENTS.has(name)) return;
    const safeDetail = Object.fromEntries(
      Object.entries(detail).filter(([, value]) =>
        ["string", "number", "boolean"].includes(typeof value),
      ),
    );
    document.dispatchEvent(
      new CustomEvent("aeg:analytics", {
        detail: { event: name, ...safeDetail },
      }),
    );
    try {
      analyticsAdapter.track(name, safeDetail);
    } catch {
      // Analytics must never block the Registry experience.
    }
  };

  const toggle = document.querySelector("[data-nav-toggle]");
  const nav = document.querySelector("[data-site-nav]");

  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = toggle.getAttribute("aria-expanded") !== "true";
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute(
        "aria-label",
        open ? "Close navigation" : "Open navigation",
      );
      nav.dataset.open = String(open);
    });
    nav.addEventListener("click", (event) => {
      if (event.target.closest("a")) {
        toggle.setAttribute("aria-expanded", "false");
        toggle.setAttribute("aria-label", "Open navigation");
        nav.dataset.open = "false";
      }
    });
  }

  const run = document.querySelector("[data-run-demo]");
  const reset = document.querySelector("[data-reset-demo]");
  const idle = document.querySelector("[data-demo-idle]");
  const result = document.querySelector("[data-demo-result]");

  if (run && idle && result) {
    run.addEventListener("click", () => {
      run.disabled = true;
      run.textContent = "Normalizing task…";
      window.setTimeout(() => {
        idle.hidden = true;
        result.hidden = false;
        run.disabled = false;
        run.textContent = "Run lookup again";
        result.focus();
      }, 450);
    });
  }

  if (reset && idle && result && run) {
    reset.addEventListener("click", () => {
      result.hidden = true;
      idle.hidden = false;
      run.textContent = "Retrieve verified experience";
      run.focus();
    });
  }

  const copyText = async (button, target) => {
    const text = target.textContent;
    await navigator.clipboard.writeText(text);
    const originalLabel = button.textContent;
    button.textContent = "Copied";
    const copyStatus = document.querySelector("[data-copy-status]");
    if (copyStatus) {
      copyStatus.textContent = `${originalLabel} copied to the clipboard.`;
    }
    window.setTimeout(() => {
      button.textContent = originalLabel;
      if (copyStatus) copyStatus.textContent = "";
    }, 2200);
  };

  document.querySelectorAll("[data-copy], [data-copy-target]").forEach((button) => {
    button.addEventListener("click", async () => {
      const selector = button.dataset.copyTarget || button.dataset.copy;
      const target = selector ? document.querySelector(selector) : null;
      if (!target) return;
      try {
        await copyText(button, target);
        if (button.dataset.copyEvent) {
          emitEvent(button.dataset.copyEvent, {
            experience_id: document.body.dataset.experienceId || "unknown",
          });
        }
      } catch {
        const copyStatus = document.querySelector("[data-copy-status]");
        button.textContent = "Select and copy manually";
        if (copyStatus) {
          copyStatus.textContent =
            "Clipboard access is unavailable. Select the visible block and copy it manually.";
        }
        target.focus();
      }
    });
  });

  document.querySelectorAll("[data-aeg-event]").forEach((element) => {
    element.addEventListener("click", () => {
      emitEvent(element.dataset.aegEvent, {
        experience_id: document.body.dataset.experienceId || "registry",
      });
    });
  });

  const search = document.querySelector("[data-experience-search]");
  const category = document.querySelector("[data-category-filter]");
  const status = document.querySelector("[data-status-filter]");
  const cards = [...document.querySelectorAll("[data-experience-card]")];
  const noResults = document.querySelector("[data-no-results]");
  const emptyQueryState = document.querySelector("[data-empty-query-state]");
  const resultCount = document.querySelector("[data-result-count]");
  const resultLabel = document.querySelector("[data-result-label]");

  const cardData = cards.map((card) => ({
    element: card,
    id: card.dataset.experienceId,
    search: card.dataset.search,
    category: card.dataset.category,
    status: card.dataset.status,
  }));

  const updateRegistry = (track = false) => {
    if (!search || !category || !status) return;
    const matches = filterExperiences(
      cardData,
      search.value,
      category.value,
      status.value,
    );
    const visibleIds = new Set(matches.map((experience) => experience.id));
    cardData.forEach((experience) => {
      experience.element.hidden = !visibleIds.has(experience.id);
    });
    if (resultCount) resultCount.textContent = String(matches.length);
    if (resultLabel) {
      resultLabel.textContent =
        matches.length === 1 ? "experience" : "experiences";
    }
    if (noResults) noResults.hidden = matches.length !== 0;
    const hasInput = Boolean(search.value || category.value || status.value);
    if (emptyQueryState) emptyQueryState.hidden = hasInput;
    if (track) {
      emitEvent("experience_search", {
        query_length: search.value.trim().length,
        category: category.value || "all",
        verification_status: status.value || "all",
        result_count: matches.length,
      });
    }
  };

  if (search && category && status) {
    search.addEventListener("input", () => updateRegistry(true));
    category.addEventListener("change", () => updateRegistry(true));
    status.addEventListener("change", () => updateRegistry(true));
    document.querySelectorAll("[data-registry-reset]").forEach((button) => {
      button.addEventListener("click", () => {
        search.value = "";
        category.value = "";
        status.value = "";
        updateRegistry(true);
        search.focus();
      });
    });
    updateRegistry();
  }

  document.querySelectorAll("[data-tabs]").forEach((tabs) => {
    const tabButtons = [...tabs.querySelectorAll('[role="tab"]')];
    const tabPanels = [...tabs.querySelectorAll('[role="tabpanel"]')];
    const activate = (button) => {
      tabButtons.forEach((candidate) => {
        const selected = candidate === button;
        candidate.setAttribute("aria-selected", String(selected));
        candidate.tabIndex = selected ? 0 : -1;
      });
      tabPanels.forEach((panel) => {
        panel.hidden = `#${panel.id}` !== button.dataset.tabTarget;
      });
    };
    tabButtons.forEach((button, index) => {
      button.addEventListener("click", () => activate(button));
      button.addEventListener("keydown", (event) => {
        if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
          return;
        }
        event.preventDefault();
        let nextIndex = index;
        if (event.key === "ArrowRight") {
          nextIndex = (index + 1) % tabButtons.length;
        }
        if (event.key === "ArrowLeft") {
          nextIndex = (index - 1 + tabButtons.length) % tabButtons.length;
        }
        if (event.key === "Home") nextIndex = 0;
        if (event.key === "End") nextIndex = tabButtons.length - 1;
        activate(tabButtons[nextIndex]);
        tabButtons[nextIndex].focus();
      });
    });
  });

  if (document.body.matches("[data-experience-detail]")) {
    emitEvent("experience_view", {
      experience_id: document.body.dataset.experienceId || "unknown",
    });
  }
})();
