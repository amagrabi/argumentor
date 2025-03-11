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

// Function to translate categories specifically
function translateCategories() {
  if (!translations.categories) {
    return;
  }

  document.querySelectorAll('[data-i18n^="categories."]').forEach((element) => {
    const key = element.getAttribute("data-i18n");
    const categoryName = key.replace("categories.", "");

    // Special handling for Custom category
    if (categoryName === "Custom" && translations.categories.Custom) {
      element.textContent = translations.categories.Custom;
      return;
    }

    // Try direct match first
    if (translations.categories[categoryName]) {
      element.textContent = translations.categories[categoryName];
      return;
    }

    // If no direct match, try to find the category by comparing with the original text
    const originalText = element.textContent.trim();

    // Find the matching category in translations
    for (const [category, translation] of Object.entries(
      translations.categories
    )) {
      if (category === originalText) {
        element.textContent = translation;
        break;
      }
    }
  });
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

  // Apply category translations
  translateCategories();

  // Initialize XP progress bar
  initializeXpProgressBar();

  const answersDataElement = document.getElementById("answersData");
  const answers = JSON.parse(answersDataElement.textContent);

  // Initialize chart with default metric(s): start with 'overall'
  initializeChart(answers, ["overall"]);

  // Add resize event listener to update chart on window resize
  let resizeTimeout;
  window.addEventListener("resize", function () {
    // Debounce the resize event
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function () {
      // Destroy the old chart
      if (progressChart) {
        progressChart.destroy();
      }
      // Reinitialize with current active metrics
      const activeMetrics = Object.keys(buttons).filter((key) =>
        buttons[key].classList.contains("button-active")
      );
      initializeChart(answers, activeMetrics);
    }, 250);
  });

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

// Function to initialize the XP progress bar
function initializeXpProgressBar() {
  const progressBar = document.querySelector(".xp-progress-bar");
  if (progressBar) {
    // Get the progress percentage from the element's attribute
    const progressElement = document.querySelector(".xp-bar-container");
    if (progressElement) {
      const progressPercent = progressElement.getAttribute(
        "data-progress-percent"
      );
      if (progressPercent) {
        progressBar.style.width = `${progressPercent}%`;
      } else {
        // If data attribute is not available, try to get it from the text content
        const progressText = document.getElementById("xpProgressText");
        if (progressText) {
          const progressParts = progressText.textContent
            .split("/")
            .map((part) => part.trim());
          if (progressParts.length === 2) {
            const current = parseFloat(progressParts[0]);
            const total = parseFloat(progressParts[1]);
            if (!isNaN(current) && !isNaN(total) && total > 0) {
              const percent = (current / total) * 100;
              progressBar.style.width = `${percent}%`;
            }
          }
        }
      }
    }
  }
}

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
          (a.challenge_evaluation_scores.Overall !== undefined ||
            a.challenge_evaluation_scores["Overall"] !== undefined)
        ) {
          // Try to access with both direct property and bracket notation
          const overallScore =
            a.challenge_evaluation_scores.Overall !== undefined
              ? a.challenge_evaluation_scores.Overall
              : a.challenge_evaluation_scores["Overall"];
          return parseFloat(overallScore.toFixed(1));
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
    // Create reversed copy of answers array to maintain original data
    const reversedAnswers = [...answers].reverse();

    // Format dates in a more compact way for mobile
    const labels = reversedAnswers.map((a) => {
      const date = new Date(a.created_at);
      // Use shorter date format on mobile
      if (window.innerWidth < 768) {
        // Format as MM/DD without year to save space
        return `${(date.getMonth() + 1).toString().padStart(2, "0")}/${date
          .getDate()
          .toString()
          .padStart(2, "0")}`;
      } else {
        // For desktop, use a more readable format
        const options = { month: "short", day: "numeric" };
        if (date.getFullYear() !== new Date().getFullYear()) {
          // Add year only if it's not the current year
          options.year = "numeric";
        }
        return date.toLocaleDateString(undefined, options);
      }
    });

    // Calculate appropriate y-axis settings based on data
    const allValues = [];
    reversedAnswers.forEach((answer) => {
      if (answer.evaluation_scores) {
        Object.values(answer.evaluation_scores).forEach((score) => {
          if (typeof score === "number") allValues.push(score);
        });
      }
      if (
        answer.challenge_evaluation_scores &&
        answer.challenge_evaluation_scores.Overall
      ) {
        allValues.push(answer.challenge_evaluation_scores.Overall);
      }
    });

    // Find the max value in the data, with a minimum of 10
    const dataMax = Math.max(10, ...allValues);
    // Round up to nearest whole number
    const yAxisMax = Math.ceil(dataMax);

    progressChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: getDatasetsForMetrics(reversedAnswers, defaultMetrics),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: {
          padding: {
            left: 10,
            right: 15,
            top: 10,
            bottom: window.innerWidth < 768 ? 25 : 15, // More bottom padding on mobile
          },
        },
        scales: {
          x: {
            title: {
              display: window.innerWidth >= 768,
              text: translations.profile.time,
              font: {
                size: window.innerWidth < 768 ? 10 : 14,
              },
            },
            grid: {
              display: false,
            },
            ticks: {
              maxRotation: window.innerWidth < 768 ? 30 : 45, // Less rotation on mobile
              minRotation: window.innerWidth < 768 ? 30 : 45,
              font: {
                size: window.innerWidth < 768 ? 8 : 12,
              },
              autoSkip: true,
              maxTicksLimit: window.innerWidth < 768 ? 4 : 12, // Fewer labels on mobile
              padding: window.innerWidth < 768 ? 8 : 5, // More padding on mobile
            },
          },
          y: {
            beginAtZero: true,
            min: 0,
            max: yAxisMax,
            ticks: {
              stepSize: window.innerWidth < 768 ? Math.ceil(yAxisMax / 5) : 1,
              precision: 0,
              font: {
                size: window.innerWidth < 768 ? 8 : 12,
              },
              includeBounds: true,
            },
            title: {
              display: window.innerWidth >= 768,
              text: translations.profile.rating,
              font: {
                size: window.innerWidth < 768 ? 10 : 14,
              },
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

  // Create reversed copy of answers array
  const reversedAnswers = [...answers].reverse();

  progressChart.data.datasets = getDatasetsForMetrics(
    reversedAnswers,
    activeMetrics
  );
  progressChart.data.labels = reversedAnswers.map((a) =>
    new Date(a.created_at).toLocaleDateString()
  );
  progressChart.update();
}
