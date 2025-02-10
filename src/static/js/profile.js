// Initialize the chart
let progressChart = null;

// Define a color mapping for each metric.
const colors = {
  overall: "#1f2937",
  logic: "#ef4444",
  clarity: "#f59e0b",
  depth: "#84cc16",
  objectivity: "#06b6d4",
  creativity: "#8b5cf6",
};

document.addEventListener("DOMContentLoaded", () => {
  const answersDataElement = document.getElementById("answersData");
  const answers = JSON.parse(answersDataElement.textContent);

  // Initialize chart with default metric 'overall'
  initializeChart(answers, "overall");

  const buttons = {
    overall: document.getElementById("showOverall"),
    logic: document.getElementById("showLogic"),
    clarity: document.getElementById("showClarity"),
    depth: document.getElementById("showDepth"),
    objectivity: document.getElementById("showObjectivity"),
    creativity: document.getElementById("showCreativity"),
  };

  // Set click listeners on buttons – update chart when clicked.
  Object.keys(buttons).forEach((key) => {
    buttons[key].addEventListener("click", () => updateChart(key));
  });
});

function initializeChart(answers, defaultMetric = "overall") {
  const ctx = document.getElementById("progressChart").getContext("2d");
  const labels = answers.map((a) =>
    new Date(a.created_at).toLocaleDateString()
  );

  let data;
  if (defaultMetric === "overall") {
    data = answers.map((a) => {
      const values = Object.values(a.evaluation_scores);
      return (values.reduce((sum, v) => sum + v, 0) / values.length).toFixed(1);
    });
  } else {
    const metricLabels = {
      logic: "Logical Structure",
      clarity: "Clarity",
      depth: "Depth",
      objectivity: "Objectivity",
      creativity: "Creativity",
    };
    data = answers.map((a) => a.evaluation_scores[metricLabels[defaultMetric]]);
  }

  progressChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label:
            defaultMetric === "overall"
              ? "Overall"
              : defaultMetric === "logic"
              ? "Logical Structure"
              : defaultMetric.charAt(0).toUpperCase() + defaultMetric.slice(1),
          data: data,
          borderColor: colors[defaultMetric],
          borderWidth: 2,
          fill: false,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 4,
      scales: {
        x: {
          title: {
            display: true,
            text: "Time",
            font: { size: 14 },
          },
        },
        y: {
          beginAtZero: true,
          min: 0,
          max: 10.5,
          ticks: {
            stepSize: 1,
            callback: function (value) {
              return value === 10.5 ? 10 : value;
            },
            font: { size: 12 },
          },
          title: {
            display: true,
            text: "Ratings",
            font: { size: 14 },
          },
        },
      },
      plugins: {
        legend: {
          display: true,
          labels: {
            usePointStyle: true, // Use circular point markers
            pointStyle: "circle",
            font: { size: 12 },
            padding: 10,
          },
        },
        tooltip: {
          mode: "index",
          intersect: false,
          titleFont: { size: 14 },
          bodyFont: { size: 12 },
        },
      },
      interaction: {
        mode: "nearest",
        intersect: false,
      },
      elements: {
        line: {
          borderJoinStyle: "round",
        },
      },
    },
  });
}

function updateChart(metric) {
  if (!progressChart) return;

  const answersDataElement = document.getElementById("answersData");
  const answers = JSON.parse(answersDataElement.textContent);

  // Reset all buttons to inactive
  const buttons = {
    overall: document.getElementById("showOverall"),
    logic: document.getElementById("showLogic"),
    clarity: document.getElementById("showClarity"),
    depth: document.getElementById("showDepth"),
    objectivity: document.getElementById("showObjectivity"),
    creativity: document.getElementById("showCreativity"),
  };

  Object.values(buttons).forEach((btn) => {
    btn.classList.remove("bg-gray-800", "text-white");
    btn.classList.add("bg-gray-100", "text-gray-800");
  });

  // Activate the selected button
  buttons[metric].classList.remove("bg-gray-100", "text-gray-800");
  buttons[metric].classList.add("bg-gray-800", "text-white");

  const labels = answers.map((a) =>
    new Date(a.created_at).toLocaleDateString()
  );
  let data;
  if (metric === "overall") {
    data = answers.map((a) => {
      const values = Object.values(a.evaluation_scores);
      return (values.reduce((sum, v) => sum + v, 0) / values.length).toFixed(1);
    });
  } else {
    const metricLabels = {
      logic: "Logical Structure",
      clarity: "Clarity",
      depth: "Depth",
      objectivity: "Objectivity",
      creativity: "Creativity",
    };
    data = answers.map((a) => a.evaluation_scores[metricLabels[metric]]);
  }

  progressChart.data.labels = labels;
  progressChart.data.datasets = [
    {
      label:
        metric === "overall"
          ? "Overall"
          : metric === "logic"
          ? "Logical Structure"
          : metric.charAt(0).toUpperCase() + metric.slice(1),
      data: data,
      borderColor: colors[metric],
      borderWidth: 2,
      fill: false,
      tension: 0.3,
      pointRadius: 4,
      pointHoverRadius: 6,
    },
  ];
  progressChart.update();
}
