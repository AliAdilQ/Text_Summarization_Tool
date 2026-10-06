(() => {
  const data = JSON.parse(document.getElementById("chart-data").textContent);
  let charts = [];
  function renderCharts() {
    charts.forEach((chart) => chart.destroy());
    const dark = document.documentElement.dataset.theme === "dark";
    const ink = dark ? "#aebdb8" : "#81908b";
    const grid = dark ? "#263c35" : "#edf1ee";
    Chart.defaults.font.family = "DM Sans, sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.color = ink;
    Chart.defaults.animation.duration = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches
      ? 0
      : 700;
    const teal = dark ? "#61c6a6" : "#19806a";
    charts = [
      new Chart(document.getElementById("activity-chart"), {
        type: "line",
        data: {
          labels: data.days,
          datasets: [
            {
              label: "Summaries",
              data: data.activity,
              borderColor: teal,
              backgroundColor: dark ? "#61c6a618" : "#19806a12",
              fill: true,
              tension: 0.35,
              pointBackgroundColor: teal,
              pointBorderColor: dark ? "#1b2c26" : "#fff",
              pointBorderWidth: 3,
              pointRadius: 5,
              borderWidth: 2.5,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, border: { display: false } },
            y: {
              beginAtZero: true,
              ticks: { precision: 0 },
              grid: { color: grid },
              border: { display: false },
            },
          },
        },
      }),
      new Chart(document.getElementById("length-chart"), {
        type: "doughnut",
        data: {
          labels: ["Short", "Medium", "Long"],
          datasets: [
            {
              data: data.lengths,
              backgroundColor: [teal, "#a6c9bc", "#d9e7df"],
              borderWidth: 0,
              hoverOffset: 5,
              spacing: 4,
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "78%",
          plugins: { legend: { display: false } },
        },
      }),
      new Chart(document.getElementById("users-chart"), {
        type: "bar",
        data: {
          labels: data.users,
          datasets: [
            {
              label: "Summaries",
              data: data.user_counts,
              backgroundColor: [
                teal,
                "#6b9c8a",
                "#91b4a5",
                "#b2ccbe",
                "#d0dfd5",
              ],
              borderRadius: 4,
              barThickness: 12,
            },
          ],
        },
        options: {
          indexAxis: "y",
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: {
              beginAtZero: true,
              ticks: { precision: 0 },
              grid: { color: grid },
              border: { display: false },
            },
            y: { grid: { display: false }, border: { display: false } },
          },
        },
      }),
    ];
  }
  renderCharts();
  window.addEventListener("themechange", renderCharts);
})();
