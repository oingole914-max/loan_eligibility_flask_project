(() => {
  "use strict";

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ------------------------------------------------------------------
   * Subtle reveal-on-scroll. Content is fully visible without JavaScript.
   * ---------------------------------------------------------------- */
  const revealItems = document.querySelectorAll("[data-reveal]");
  if (revealItems.length && !reduceMotion && "IntersectionObserver" in window) {
    revealItems.forEach((item) => item.classList.add("reveal-init"));
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -30px 0px" }
    );
    revealItems.forEach((item) => observer.observe(item));
  }

  /* ------------------------------------------------------------------
   * Submit-button loading state for real form submissions.
   * ---------------------------------------------------------------- */
  document.querySelectorAll("form[data-loading-form]").forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector("[data-submit-button]");
      if (!button) return;
      button.classList.add("is-loading");
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
    });
  });

  /* ------------------------------------------------------------------
   * Password visibility controls.
   * ---------------------------------------------------------------- */
  document.querySelectorAll("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.togglePassword);
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      const icon = button.querySelector("i");
      if (icon) {
        icon.classList.toggle("bi-eye", showing);
        icon.classList.toggle("bi-eye-slash", !showing);
      }
    });
  });

  /* ------------------------------------------------------------------
   * Destructive-action confirmation. Only begins after confirmation.
   * ---------------------------------------------------------------- */
  document.querySelectorAll("[data-confirm]").forEach((element) => {
    const message = element.dataset.confirm;
    const eventName = element.tagName === "FORM" ? "submit" : "click";
    element.addEventListener(eventName, (event) => {
      if (!window.confirm(message)) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    });
  });

  /* ------------------------------------------------------------------
   * Auto-dismiss only non-critical flash messages.
   * ---------------------------------------------------------------- */
  document.querySelectorAll(".app-alert.alert-success, .app-alert.alert-info").forEach((alert) => {
    window.setTimeout(() => {
      if (!alert.isConnected || !window.bootstrap) return;
      const instance = bootstrap.Alert.getOrCreateInstance(alert);
      instance.close();
    }, 7000);
  });

  /* ------------------------------------------------------------------
   * Print action on the prediction result page.
   * ---------------------------------------------------------------- */
  document.querySelectorAll("[data-print-page]").forEach((button) => {
    button.addEventListener("click", () => window.print());
  });

  /* ------------------------------------------------------------------
   * Eligibility doughnut chart (admin dashboard). Data comes from the
   * server as actual database counts, never hardcoded.
   * ---------------------------------------------------------------- */
  const eligibilityCanvas = document.getElementById("eligibilityChart");
  if (eligibilityCanvas && window.Chart) {
    const eligible = Number(eligibilityCanvas.dataset.eligible || 0);
    const ineligible = Number(eligibilityCanvas.dataset.ineligible || 0);
    const total = eligible + ineligible;

    if (total > 0) {
      new Chart(eligibilityCanvas, {
        type: "doughnut",
        data: {
          labels: ["Eligible", "Not eligible"],
          datasets: [
            {
              data: [eligible, ineligible],
              backgroundColor: ["#15805a", "#bc3f3b"],
              hoverBackgroundColor: ["#116b4b", "#a53632"],
              borderWidth: 0,
              hoverOffset: 3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: true,
          aspectRatio: 1,
          cutout: "76%",
          animation: { duration: reduceMotion ? 0 : 650 },
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: "#07162f",
              padding: 10,
              cornerRadius: 8,
              displayColors: true,
              callbacks: {
                label(context) {
                  const value = context.parsed;
                  const percent = total ? ((value / total) * 100).toFixed(1) : "0.0";
                  return ` ${context.label}: ${value} (${percent}%)`;
                },
              },
            },
          },
        },
      });
    }
  }

  /* ------------------------------------------------------------------
   * Live application snapshot (derived only from the user's own inputs).
   * ---------------------------------------------------------------- */
  const applicantIncome = document.getElementById("applicantIncome");
  const coapplicantIncome = document.getElementById("coapplicantIncome");
  const loanAmount = document.getElementById("loanAmount");
  const loanTerm = document.getElementById("loanTerm");
  const incomePreview = document.getElementById("incomePreview");
  const loanPreview = document.getElementById("loanPreview");
  const termPreview = document.getElementById("termPreview");

  if (applicantIncome && incomePreview) {
    const money = new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    });

    const parse = (input) => {
      const value = Number.parseFloat(input.value);
      return Number.isFinite(value) && value >= 0 ? value : null;
    };

    const formatMoney = (value) => (value === null ? "—" : money.format(value));

    const updateIncome = () => {
      const applicant = parse(applicantIncome);
      const coapplicant = coapplicantIncome ? parse(coapplicantIncome) : 0;
      if (applicant === null) {
        incomePreview.textContent = "—";
        return;
      }
      incomePreview.textContent = formatMoney(applicant + (coapplicant || 0));
    };

    const updateLoan = () => {
      const amount = loanAmount ? parse(loanAmount) : null;
      loanPreview.textContent = amount === null ? "—" : formatMoney(amount * 1000);
    };

    const updateTerm = () => {
      if (!loanTerm) return;
      const months = Number.parseInt(loanTerm.value, 10);
      if (!Number.isFinite(months) || months <= 0) {
        termPreview.textContent = "—";
      } else if (months % 12 === 0) {
        const years = months / 12;
        termPreview.textContent = `${years} year${years === 1 ? "" : "s"} (${months} months)`;
      } else {
        termPreview.textContent = `${months} months`;
      }
    };

    [applicantIncome, coapplicantIncome].forEach((input) => {
      if (input) input.addEventListener("input", updateIncome);
    });
    if (loanAmount) loanAmount.addEventListener("input", updateLoan);
    if (loanTerm) loanTerm.addEventListener("input", updateTerm);

    updateIncome();
    updateLoan();
    updateTerm();
  }
})();
