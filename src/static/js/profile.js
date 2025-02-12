// Initialize the chart variable
let progressChart = null;

// Define a color mapping for each metric.
const colors = {
  overall: "#1f2937",
  relevance: "#f472b6",
  logic: "#ef4444",
  clarity: "#f59e0b",
  depth: "#84cc16",
  objectivity: "#06b6d4",
  creativity: "#8b5cf6",
  challenge: "#a855f7",
};

document.addEventListener("DOMContentLoaded", () => {
  const answersDataElement = document.getElementById("answersData");
  const answers = JSON.parse(answersDataElement.textContent);

  // Initialize chart with default metric(s): start with 'overall'
  initializeChart(answers, ["overall"]);

  const buttons = {
    overall: document.getElementById("showOverall"),
    relevance: document.getElementById("showRelevance"),
    logic: document.getElementById("showLogic"),
    clarity: document.getElementById("showClarity"),
    depth: document.getElementById("showDepth"),
    objectivity: document.getElementById("showObjectivity"),
    creativity: document.getElementById("showCreativity"),
    challenge: document.getElementById("showChallenge"), // New button for challenge scores
  };

  // Attach click listeners to toggle active/inactive on each button.
  Object.keys(buttons).forEach((key) => {
    buttons[key].addEventListener("click", () => {
      if (buttons[key].classList.contains("bg-gray-800")) {
        // Switch to inactive state
        buttons[key].classList.remove(
          "bg-gray-800",
          "text-white",
          "button-active"
        );
        buttons[key].classList.add(
          "bg-gray-100",
          "text-gray-800",
          "button-inactive"
        );
      } else {
        // Switch to active state
        buttons[key].classList.remove(
          "bg-gray-100",
          "text-gray-800",
          "button-inactive"
        );
        buttons[key].classList.add(
          "bg-gray-800",
          "text-white",
          "button-active"
        );
      }
      updateChartMultiple(answers, buttons);
    });
  });
});

function getDatasetsForMetrics(answers, selectedMetrics) {
  // Display labels corresponding to each metric key.
  const metricLabels = {
    overall: "Overall",
    relevance: "Relevance",
    logic: "Logical Structure",
    clarity: "Clarity",
    depth: "Depth",
    objectivity: "Objectivity",
    creativity: "Creativity",
    challenge: "Challenge",
  };

  const datasets = [];
  selectedMetrics.forEach((metric) => {
    let data;
    if (metric === "overall") {
      // For overall, compute the average of all evaluation scores.
      data = answers.map((a) => {
        const values = Object.values(a.evaluation_scores);
        return parseFloat(
          (values.reduce((sum, v) => sum + v, 0) / values.length).toFixed(1)
        );
      });
    } else if (metric === "challenge") {
      // For challenge, retrieve the overall challenge score if available.
      data = answers.map((a) => {
        if (
          a.challenge_evaluation_scores &&
          a.challenge_evaluation_scores.Overall !== undefined
        ) {
          return parseFloat(a.challenge_evaluation_scores.Overall.toFixed(1));
        } else {
          return null;
        }
      });
    } else {
      data = answers.map((a) => a.evaluation_scores[metricLabels[metric]]);
    }
    datasets.push({
      label: metricLabels[metric],
      data: data,
      borderColor: colors[metric],
      borderWidth: 2,
      fill: false,
      tension: 0.3,
      pointRadius: 4,
      pointHoverRadius: 6,
    });
  });
  return datasets;
}

function initializeChart(answers, defaultMetrics = ["overall"]) {
  const ctx = document.getElementById("progressChart").getContext("2d");
  const labels = answers.map((a) =>
    new Date(a.created_at).toLocaleDateString()
  );

  progressChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: getDatasetsForMetrics(answers, defaultMetrics),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: {
            display: true,
            text: "Time",
            font: { size: 14 },
          },
          grid: {
            display: false,
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
          grid: {
            display: true,
            color: "rgba(0, 0, 0, 0.04)",
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          usePointStyle: true,
          callbacks: {
            labelColor: function (context) {
              return {
                backgroundColor: context.dataset.borderColor,
                borderColor: context.dataset.borderColor,
                borderWidth: 1,
                borderRadius: 50,
                pointStyle: "circle",
              };
            },
            labelPointStyle: function (context) {
              return {
                pointStyle: "circle",
                rotation: 0,
              };
            },
          },
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

function updateChartMultiple(answers, buttons) {
  // Determine which metrics are active based on their button classes.
  const activeMetrics = Object.keys(buttons).filter((key) =>
    buttons[key].classList.contains("bg-gray-800")
  );
  // Fallback: if none selected, default to "overall".
  if (activeMetrics.length === 0) {
    activeMetrics.push("overall");
    buttons.overall.classList.remove("bg-gray-100", "text-gray-800");
    buttons.overall.classList.add("bg-gray-800", "text-white");
  }
  progressChart.data.datasets = getDatasetsForMetrics(answers, activeMetrics);
  progressChart.data.labels = answers.map((a) =>
    new Date(a.created_at).toLocaleDateString()
  );
  progressChart.update();
}
