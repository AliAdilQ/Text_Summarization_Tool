(() => {
  const form = document.getElementById("summarizer-form");
  const input = document.getElementById("text");
  const button = document.getElementById("generate-button");
  const error = document.getElementById("summary-error");
  const panel = document.getElementById("result-panel");
  const wordCount = (text) =>
    (text.match(/[\p{L}\p{N}]+(?:['’-][\p{L}\p{N}]+)*/gu) || []).length;
  let currentResult = "",
    busy = false;
  function updateCounts() {
    document.getElementById("word-count").textContent = wordCount(
      input.value,
    ).toLocaleString();
    document.getElementById("char-count").textContent = Array.from(
      input.value,
    ).length.toLocaleString();
    error.hidden = true;
  }
  input.addEventListener("input", updateCounts);
  updateCounts();
  document.getElementById("clear-text").addEventListener("click", () => {
    input.value = "";
    updateCounts();
    input.focus();
  });
  document.getElementById("sample-text").addEventListener("click", () => {
    input.value =
      "Energy systems around the world are changing as communities invest in cleaner sources of electricity. Solar panels and wind turbines are becoming more affordable, helping local governments reduce dependence on fossil fuels. However, producing clean energy is only one part of the transition. Electricity must also be available when the sun is not shining and the wind is calm. Battery storage gives grid operators a way to save surplus power during periods of high production and release it when demand rises. Researchers are developing new battery materials that rely on abundant resources and can last through thousands of charging cycles. Public investment in transmission lines is equally important because renewable energy is often produced far from the cities that need it. Community energy projects allow residents to share the benefits of local installations and participate in decisions about their development. A successful transition combines technology, reliable infrastructure, and policies that make electricity accessible to everyone. Training programs can help workers gain skills in installation, maintenance, and grid management. Together, these efforts create an energy system that is more resilient, more efficient, and better prepared for the future.";
    updateCounts();
    input.focus();
    input.setSelectionRange(0, 0);
    input.scrollTop = 0;
  });
  function showError(message) {
    error.textContent = message;
    error.hidden = false;
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    if (wordCount(input.value) < 30) {
      showError(
        "Add at least 30 words so there is enough context to summarize.",
      );
      input.focus();
      return;
    }
    if (Array.from(input.value).length > 50000) {
      showError("Keep your text under 50,000 characters.");
      return;
    }
    busy = true;
    button.disabled = true;
    input.readOnly = true;
    document.getElementById("clear-text").disabled = true;
    document.getElementById("sample-text").disabled = true;
    error.hidden = true;
    panel.setAttribute("aria-busy", "true");
    document.getElementById("result-empty").hidden = true;
    document.getElementById("result-content").hidden = true;
    document.getElementById("result-loading").hidden = false;
    button.querySelector("span").textContent = "Finding the essentials…";
    try {
      const response = await fetch(form.dataset.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')
            .content,
        },
        body: JSON.stringify({
          text: input.value,
          length: form.querySelector('input[name="length"]:checked').value,
        }),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(
          data.error || "We couldn’t complete that summary. Please try again.",
        );
      currentResult = data.summary;
      document.getElementById("summary-output").textContent = data.summary;
      document.getElementById("result-original").textContent =
        data.original_word_count.toLocaleString();
      document.getElementById("result-words").textContent =
        data.summary_word_count.toLocaleString();
      document.getElementById("result-compression").textContent =
        `${data.compression_ratio}%`;
      document.getElementById("result-time").textContent =
        `${data.processing_time}s`;
      document.getElementById("result-method").textContent =
        `${data.method.charAt(0).toUpperCase() + data.method.slice(1)} engine`;
      document.getElementById("result-notice").textContent = data.notice;
      const savedLink = document.getElementById("saved-link");
      savedLink.hidden = !data.saved;
      if (data.saved) savedLink.href = data.detail_url;
      document.getElementById("result-content").hidden = false;
      panel.querySelector(".result-badge").textContent =
        `${data.length.charAt(0).toUpperCase() + data.length.slice(1)} summary`;
      if (window.innerWidth < 800)
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (problem) {
      showError(
        problem instanceof SyntaxError
          ? "The server returned an unexpected response. Please try again."
          : problem.message,
      );
      document.getElementById(
        currentResult ? "result-content" : "result-empty",
      ).hidden = false;
    } finally {
      busy = false;
      button.disabled = false;
      input.readOnly = false;
      document.getElementById("clear-text").disabled = false;
      document.getElementById("sample-text").disabled = false;
      panel.setAttribute("aria-busy", "false");
      document.getElementById("result-loading").hidden = true;
      button.querySelector("span").textContent = "Generate summary";
    }
  });
  document.getElementById("download-summary").addEventListener("click", () => {
    if (!currentResult) return;
    const url = URL.createObjectURL(
      new Blob([currentResult + "\n"], { type: "text/plain;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "briefly-summary.txt";
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    window.showToast("Your summary is ready to keep.");
  });
})();
