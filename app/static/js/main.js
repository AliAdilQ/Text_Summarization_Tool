/* Shared navigation, theme, clipboard, notifications, and confirmed mutations. */
(() => {
  const themeButtons = document.querySelectorAll(".theme-toggle");
  function updateThemeButtons() {
    const dark = document.documentElement.dataset.theme === "dark";
    themeButtons.forEach((button) => {
      button.innerHTML = `<i class="bi bi-${dark ? "sun" : "moon"}"></i>`;
      button.setAttribute(
        "aria-label",
        `Switch to ${dark ? "light" : "dark"} mode`,
      );
    });
  }
  themeButtons.forEach((button) =>
    button.addEventListener("click", () => {
      const theme =
        document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = theme;
      try {
        localStorage.setItem("briefly-theme", theme);
      } catch (error) {
        /* Theme still works without storage. */
      }
      updateThemeButtons();
      window.dispatchEvent(new CustomEvent("themechange", { detail: theme }));
    }),
  );
  updateThemeButtons();
  const mobileToggle = document.querySelector(".nav-mobile-toggle");
  mobileToggle?.addEventListener("click", () => {
    const expanded = mobileToggle.getAttribute("aria-expanded") === "true";
    mobileToggle.setAttribute("aria-expanded", String(!expanded));
    document.getElementById("main-nav").classList.toggle("open", !expanded);
  });
  document
    .querySelectorAll(".dismiss-flash")
    .forEach((button) =>
      button.addEventListener("click", () =>
        button.closest(".flash-message").remove(),
      ),
    );
  let toastTimer;
  window.showToast = (message) => {
    const toast = document.getElementById("app-toast");
    toast.textContent = message;
    toast.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("visible"), 3600);
  };
  document.querySelectorAll("[data-copy-target]").forEach((button) =>
    button.addEventListener("click", async () => {
      const text = document.getElementById(
        button.dataset.copyTarget,
      )?.textContent;
      if (!text) return;
      try {
        if (navigator.clipboard && window.isSecureContext)
          await navigator.clipboard.writeText(text);
        else {
          const textarea = document.createElement("textarea");
          textarea.value = text;
          textarea.style.position = "fixed";
          textarea.style.opacity = "0";
          document.body.append(textarea);
          textarea.select();
          const copied = document.execCommand("copy");
          textarea.remove();
          if (!copied) throw new Error("Clipboard unavailable");
        }
        window.showToast("Summary copied. Take the good ideas with you.");
      } catch (error) {
        window.showToast(
          "Select the summary text and copy it using your keyboard.",
        );
      }
    }),
  );
  const dialog = document.getElementById("confirm-dialog");
  let pendingForm;
  document.querySelectorAll("form[data-confirm]").forEach((form) =>
    form.addEventListener("submit", (event) => {
      if (form.dataset.confirmed === "true") return;
      event.preventDefault();
      pendingForm = form;
      document.getElementById("confirm-message").textContent =
        form.dataset.confirm;
      dialog.returnValue = "cancel";
      dialog.showModal();
    }),
  );
  dialog?.addEventListener("close", () => {
    if (dialog.returnValue === "confirm" && pendingForm) {
      pendingForm.dataset.confirmed = "true";
      pendingForm.requestSubmit();
    }
    pendingForm = null;
  });
})();
