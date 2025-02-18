// Import translations
let translations = {};

// Load translations when DOM is ready
async function loadTranslations() {
  const currentLanguage = localStorage.getItem("language") || "en";
  try {
    const response = await fetch(
      `/static/translations/${currentLanguage}.json`
    );
    translations = await response.json();
    // Make translations globally available
    window.translations = translations;
  } catch (error) {
    console.error("Error loading translations:", error);
  }
}

// Initialize the chart variable
let progressChart = null;

// Define a color mapping for each metric.
const colors = {
  overall: "#1f2937",
  relevance: "#2563eb",
  logic: "#ef4444",
  clarity: "#f59e0b",
  depth: "#84cc16",
  objectivity: "#06b6d4",
  creativity: "#8b5cf6",
  challenge: "#a0522d",
};

document.addEventListener("DOMContentLoaded", async () => {
  // Load translations first
  await loadTranslations();

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
    challenge: document.getElementById("showChallenge"),
  };

  // Set initial active/inactive states:
  // Make "overall" active by default (using its metric color)
  buttons.overall.classList.add("button-active");
  buttons.overall.style.backgroundColor = colors.overall;
  // All other buttons are inactive from the start.
  Object.keys(buttons).forEach((metric) => {
    if (metric !== "overall") {
      buttons[metric].classList.add("button-inactive");
    }
  });

  // Attach click listeners to toggle active/inactive on each button.
  Object.keys(buttons).forEach((metric) => {
    buttons[metric].addEventListener("click", (e) => {
      // Prevent event from bubbling up to avoid translation updates
      e.stopPropagation();

      if (buttons[metric].classList.contains("button-active")) {
        // Switch to inactive state:
        buttons[metric].classList.remove("button-active");
        buttons[metric].classList.add("button-inactive");
        // Clear the inline background color.
        buttons[metric].style.backgroundColor = "";
        // Remove any Tailwind active classes (this fixes the "Overall" button)
        buttons[metric].classList.remove("bg-gray-800", "text-white");
        // Add Tailwind inactive classes.
        buttons[metric].classList.add("bg-gray-100", "text-gray-800");
      } else {
        // Switch to active state:
        buttons[metric].classList.remove("button-inactive");
        // Remove inactive styling classes.
        buttons[metric].classList.remove("bg-gray-100", "text-gray-800");
        buttons[metric].classList.add("button-active");
        // Set the background to the metric's specific color.
        buttons[metric].style.backgroundColor = colors[metric];
        // Ensure active text color is white for visibility.
        buttons[metric].classList.add("text-white");
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
  const ctx = document.getElementById("progressChart")?.getContext("2d");
  if (ctx) {
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
              text: translations.profile.time,
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
              text: translations.profile.rating,
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
}

function updateChartMultiple(answers, buttons) {
  // Determine which metrics are active based on the "button-active" class
  const activeMetrics = Object.keys(buttons).filter((key) =>
    buttons[key].classList.contains("button-active")
  );

  progressChart.data.datasets = getDatasetsForMetrics(answers, activeMetrics);
  progressChart.data.labels = answers.map((a) =>
    new Date(a.created_at).toLocaleDateString()
  );
  progressChart.update();
}
