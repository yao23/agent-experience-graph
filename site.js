(() => {
  const toggle = document.querySelector("[data-nav-toggle]");
  const nav = document.querySelector("[data-site-nav]");

  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = toggle.getAttribute("aria-expanded") !== "true";
      toggle.setAttribute("aria-expanded", String(open));
      nav.dataset.open = String(open);
    });
    nav.addEventListener("click", (event) => {
      if (event.target.closest("a")) {
        toggle.setAttribute("aria-expanded", "false");
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

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.querySelector(button.dataset.copy);
      if (!target) return;
      try {
        await navigator.clipboard.writeText(target.innerText);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Select and copy manually";
      }
    });
  });
})();
