(() => {
  const year = document.querySelector("[data-year]");
  if (year) year.textContent = String(new Date().getFullYear());

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", async () => {
      const target = document.getElementById(button.dataset.copy);
      if (!target) return;
      const original = button.textContent;
      try {
        await navigator.clipboard.writeText(target.innerText);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Select code";
        const range = document.createRange();
        range.selectNodeContents(target);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      }
      window.setTimeout(() => {
        button.textContent = original;
      }, 1800);
    });
  });

  const demo = document.querySelector("[data-demo]");
  if (!demo) return;

  const runButton = demo.querySelector("[data-run-demo]");
  const idle = demo.querySelector("[data-demo-idle]");
  const steps = demo.querySelector("[data-demo-steps]");
  const result = demo.querySelector("[data-demo-result]");
  const stepItems = [...demo.querySelectorAll("[data-step]")];
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let timers = [];

  const clearTimers = () => {
    timers.forEach(window.clearTimeout);
    timers = [];
  };

  const showResult = () => {
    stepItems.forEach((item) => {
      item.classList.remove("active");
      item.classList.add("done");
    });
    result.hidden = false;
    runButton.disabled = false;
    runButton.innerHTML = 'Run again <span aria-hidden="true">↻</span>';
  };

  runButton.addEventListener("click", () => {
    clearTimers();
    runButton.disabled = true;
    runButton.textContent = "Searching traces…";
    idle.hidden = true;
    steps.hidden = false;
    result.hidden = true;
    stepItems.forEach((item) => item.classList.remove("active", "done"));

    if (reducedMotion) {
      showResult();
      return;
    }

    stepItems.forEach((item, index) => {
      timers.push(
        window.setTimeout(() => {
          stepItems.forEach((previous, previousIndex) => {
            previous.classList.toggle("done", previousIndex < index);
            previous.classList.toggle("active", previousIndex === index);
          });
        }, index * 650),
      );
    });

    timers.push(window.setTimeout(showResult, stepItems.length * 650 + 250));
  });
})();
