// Initialize the chart
let progressChart = null;

function initializeChart(answers) {
  const ctx = document.getElementById("progressChart").getContext("2d");

  const dates = answers.map((a) => new Date(a.created_at).toLocaleDateString());
  const initialData = answers.map((a) => {
    const values = Object.values(a.evaluation_scores);
    return (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);
  });

  progressChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: "Overall",
          data: initialData,
          borderColor: "#1f2937",
          borderWidth: 2,
          fill: false,
          tension: 0.1,
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
          },
          title: {
            display: true,
            text: "Ratings",
          },
        },
      },
      plugins: {
        legend: {
          display: true,
        },
      },
    },
  });
}

document.addEventListener("DOMContentLoaded", () => {
  // Initialize buttons after DOM is loaded
  const buttons = {
    overall: document.getElementById("showOverall"),
    logic: document.getElementById("showLogic"),
    clarity: document.getElementById("showClarity"),
    depth: document.getElementById("showDepth"),
    objectivity: document.getElementById("showObjectivity"),
    creativity: document.getElementById("showCreativity"),
  };

  const colors = {
    overall: "#1f2937",
    logic: "#ef4444",
    clarity: "#f59e0b",
    depth: "#84cc16",
    objectivity: "#06b6d4",
    creativity: "#8b5cf6",
  };

  function updateChart(type) {
    if (!progressChart) return;

    const answersDataElement = document.getElementById("answersData");
    const answers = JSON.parse(answersDataElement.textContent);

    // Reset all buttons to inactive state
    Object.entries(buttons).forEach(([_, btn]) => {
      if (btn) {
        btn.classList.remove("bg-gray-800", "text-white");
        btn.classList.add("bg-gray-100", "text-gray-800");
      }
    });

    // Activate clicked button
    const activeButton = buttons[type];
    if (activeButton) {
      activeButton.classList.remove("bg-gray-100", "text-gray-800");
      activeButton.classList.add("bg-gray-800", "text-white");
    }

    const dates = answers.map((a) =>
      new Date(a.created_at).toLocaleDateString()
    );
    let data;

    if (type === "overall") {
      data = answers.map((a) => {
        const values = Object.values(a.evaluation_scores);
        return (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);
      });
    } else {
      const scoreType = {
        logic: "Logical Structure",
        clarity: "Clarity",
        depth: "Depth",
        objectivity: "Objectivity",
        creativity: "Creativity",
      }[type];
      data = answers.map((a) => a.evaluation_scores[scoreType]);
    }

    progressChart.data.labels = dates;
    progressChart.data.datasets[0].label =
      type.charAt(0).toUpperCase() + type.slice(1);
    progressChart.data.datasets[0].data = data;
    progressChart.data.datasets[0].borderColor = colors[type];
    progressChart.update();
  }

  // Initialize chart and add button listeners
  const answersDataElement = document.getElementById("answersData");
  if (answersDataElement) {
    const answers = JSON.parse(answersDataElement.textContent);
    if (answers && answers.length > 0) {
      initializeChart(answers);

      // Add click handlers to buttons
      Object.entries(buttons).forEach(([type, button]) => {
        if (button) {
          button.addEventListener("click", () => updateChart(type));
        }
      });
    }
  }
});
