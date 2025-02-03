// Category icons mapping with updated icons
const categoryIcons = {
  Philosophy: "📚",
  Ethics: "⚖️",
  "Business & Risk": "💼",
  "Thought Experiments": "💡",
  Politics: "🏛️",
  "Biases & Fallacies": "🔍",
  "AI & Future": "🤖",
  "Fun & Casual": "🍻",
};

// Global variable that stores your selected category values.
let selectedCategories = [];
// Global variable to store the currently displayed question.
let currentQuestion = null;

// Utility functions for color interpolation
function hexToRgb(hex) {
  hex = hex.replace("#", "");
  let bigint = parseInt(hex, 16);
  let r = (bigint >> 16) & 255;
  let g = (bigint >> 8) & 255;
  let b = bigint & 255;
  return { r, g, b };
}

function rgbToHex(r, g, b) {
  return (
    "#" +
    [r, g, b]
      .map((x) => {
        const hex = x.toString(16);
        return hex.length === 1 ? "0" + hex : hex;
      })
      .join("")
  );
}

function interpolateColor(color1, color2, factor) {
  const r = Math.round(color1.r + factor * (color2.r - color1.r));
  const g = Math.round(color1.g + factor * (color2.g - color1.g));
  const b = Math.round(color1.b + factor * (color2.b - color1.b));
  return { r, g, b };
}

// Function to determine color based on score using linear interpolation
function scoreToColor(score) {
  const minScore = 1,
    maxScore = 10;
  const clampedScore = Math.min(maxScore, Math.max(minScore, score));
  const factor = (clampedScore - minScore) / (maxScore - minScore);

  // Five-color gradient: red -> orange -> yellow -> lime -> emerald
  const colors = [
    hexToRgb("#ef4444"), // red-500 (1-3)
    hexToRgb("#f59e0b"), // amber-500 (4-5)
    hexToRgb("#eab308"), // yellow-500 (6)
    hexToRgb("#84cc16"), // lime-500 (7)
    hexToRgb("#16a34a"), // green-600 (8-9)
    hexToRgb("#059669"), // emerald-600 (10)
  ];

  if (factor < 0.3) {
    return interpolate(colors[0], colors[1], factor / 0.3);
  } else if (factor < 0.5) {
    return interpolate(colors[1], colors[2], (factor - 0.3) / 0.2);
  } else if (factor < 0.7) {
    return interpolate(colors[2], colors[3], (factor - 0.5) / 0.2);
  } else if (factor < 0.9) {
    return interpolate(colors[3], colors[4], (factor - 0.7) / 0.2);
  } else {
    return interpolate(colors[4], colors[5], (factor - 0.9) / 0.1);
  }

  function interpolate(start, end, ratio) {
    const result = {
      r: Math.round(start.r + (end.r - start.r) * ratio),
      g: Math.round(start.g + (end.g - start.g) * ratio),
      b: Math.round(start.b + (end.b - start.b) * ratio),
    };
    return rgbToHex(result.r, result.g, result.b);
  }
}

// Helper function for typewriter effect
function typeWriter(element, text, speed) {
  if (element._typewriterTimer) {
    clearInterval(element._typewriterTimer);
  }
  element.textContent = "";
  let i = 0;
  element._typewriterTimer = setInterval(() => {
    element.textContent += text.charAt(i);
    i++;
    if (i >= text.length) {
      clearInterval(element._typewriterTimer);
      element._typewriterTimer = null;
    }
  }, speed);
}

// Helper function to update the question display using a given question object.
function updateQuestionDisplay(question) {
  const questionElem = document.getElementById("questionDescription");
  if (questionElem) {
    questionElem.textContent = question.description;
  }
  const categoryBadge = document.getElementById("categoryBadge");
  if (categoryBadge) {
    categoryBadge.textContent = question.category || "";
  }
}

// Modified getNewQuestion function:
// 1. It appends the selectedCategories as a query parameter to the request URL.
// 2. After fetching a new question, it stores that question in sessionStorage.
async function getNewQuestion() {
  try {
    // Build query string from selectedCategories to filter questions
    let query =
      selectedCategories.length > 0
        ? `?categories=${selectedCategories.join(",")}`
        : "";
    const response = await fetch("/get_new_question" + query);
    const question = await response.json();
    if (question.error) {
      console.error("Error fetching new question:", question.error);
      return;
    }
    currentQuestion = question;
    // Save the current question to sessionStorage to persist it across navigations
    sessionStorage.setItem("currentQuestion", JSON.stringify(question));

    // Animate the new question description
    const questionElem = document.getElementById("questionDescription");
    if (questionElem) {
      typeWriter(questionElem, question.description, 15);
    }
    // Update the category badge
    const categoryBadge = document.getElementById("categoryBadge");
    if (categoryBadge) {
      categoryBadge.textContent = question.category || "";
    }
    // Scroll into view
    if (questionElem) {
      questionElem.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  } catch (error) {
    console.error("Error fetching new question:", error);
  }
}

// Delegated event listener for handling the Next Question click
document.body.addEventListener("click", (e) => {
  if (e.target && e.target.id === "nextQuestion") {
    document.getElementById("answerInput").value = "";
    document.getElementById("charCount").textContent = "200";
    const evaluationResults = document.getElementById("evaluationResults");
    evaluationResults.classList.add("hidden");
    evaluationResults.style.display = "none";
    getNewQuestion();
  }
});

// Character counter for the answer input field
const answerInput = document.getElementById("answerInput");
const charCount = document.getElementById("charCount");
if (answerInput) {
  answerInput.addEventListener("input", () => {
    const remaining = 200 - answerInput.value.length;
    charCount.textContent = remaining;
    document.getElementById("errorMessage").textContent = "";
  });
}

// Helper function for number animation
function animateNumber(element, start, end, interval) {
  let current = start;
  const steps = 15;
  const stepValue = (end - start) / steps;
  const startColor = hexToRgb("#e53e3e");
  const endColor = hexToRgb(element.getAttribute("data-color"));

  const timer = setInterval(() => {
    current += stepValue;
    const factor = (current - start) / (end - start);
    const color = interpolateColor(startColor, endColor, factor);
    element.style.color = rgbToHex(color.r, color.g, color.b);

    if (
      (stepValue > 0 && current >= end) ||
      (stepValue < 0 && current <= end)
    ) {
      current = end;
      clearInterval(timer);
    }
    element.textContent = Math.floor(current) + "/10";
  }, 30);
}

// Answer submission handling
document.getElementById("submitAnswer").addEventListener("click", async () => {
  const answer = answerInput.value.trim();
  if (!answer) {
    document.getElementById("errorMessage").textContent =
      "Please provide an answer before submitting.";
    return;
  }
  try {
    const response = await fetch("/submit_answer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ answer }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      document.getElementById("errorMessage").textContent =
        errorData.error || "Submission failed";
      return;
    }

    const data = await response.json();

    if (!data || !data.evaluation) {
      document.getElementById("errorMessage").textContent =
        "Invalid response from server";
      return;
    }

    const scoresDiv = document.getElementById("scores");
    scoresDiv.innerHTML = "";
    Object.entries(data.evaluation.scores).forEach(([category, score]) => {
      const finalScore = score;
      const finalWidthPercent = score * 10;
      const color = scoreToColor(score);
      const feedbackText = data.evaluation.feedback[category] || "";
      scoresDiv.innerHTML += `
        <div class="mb-4">
          <div class="flex justify-between items-center">
            <span class="font-medium">${category}</span>
            <span class="font-medium score-value" data-final="${finalScore}" data-color="${color}" style="color: #e53e3e;">1/10</span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
            <div class="rounded-full h-2 progress-fill"
                  data-score="${finalWidthPercent}"
                  data-color="${color}"
                  style="width: 10%; background-color: #e53e3e;"></div>
          </div>
          <p class="text-sm text-gray-500 feedback" data-final="${feedbackText}"></p>
        </div>
      `;
    });

    setTimeout(() => {
      document.querySelectorAll(".progress-fill").forEach((fill, index) => {
        const delay = index * 100;
        setTimeout(() => {
          const targetWidth = fill.getAttribute("data-score");
          const targetColor = fill.getAttribute("data-color");
          fill.style.backgroundColor = "#e53e3e";
          fill.style.width = "10%";
          void fill.offsetWidth;
          fill.style.width = targetWidth + "%";
          fill.style.backgroundColor = targetColor;
        }, delay);
      });
      document.querySelectorAll(".score-value").forEach((span, index) => {
        const delay = index * 100;
        setTimeout(() => {
          animateNumber(span, 1, parseInt(span.getAttribute("data-final")), 30);
        }, delay);
      });
      document.querySelectorAll(".feedback").forEach((paragraph, index) => {
        const delay = index * 100;
        setTimeout(() => {
          typeWriter(paragraph, paragraph.getAttribute("data-final"), 15);
        }, delay);
      });
    }, 100);

    // Update score and XP/progress info
    document.getElementById("xpGained").innerHTML =
      "<strong>" + data.xp_gained + "</strong>";
    document.getElementById("currentLevel").innerHTML =
      "<strong>" + data.current_level + "</strong>";
    document.getElementById("xpProgressText").textContent =
      data.level_info.xp_into_level + " / " + data.level_info.xp_needed;
    document.getElementById("nextLevel").textContent =
      data.level_info.next_level;

    const xpOldBar = document.getElementById("xpOldBar");
    const xpNewBar = document.getElementById("xpNewBar");

    if (data.leveled_up) {
      xpOldBar.style.display = "none";
      xpNewBar.style.left = "0%";
      xpNewBar.style.width = data.level_info.progress_percent + "%";
    } else {
      xpOldBar.style.display = "block";
      const oldXpValue = data.current_xp - data.xp_gained;
      const oldPercent =
        ((oldXpValue - data.level_info.current_threshold) /
          data.level_info.xp_needed) *
        100;
      xpOldBar.style.width = oldPercent + "%";
      xpNewBar.style.left = oldPercent + "%";
      const newPortion = data.level_info.progress_percent - oldPercent;
      xpNewBar.style.width = newPortion + "%";
    }

    if (data.leveled_up) {
      document.getElementById("levelUpMessage").textContent = "Level Up!";
    } else {
      document.getElementById("levelUpMessage").textContent = "";
    }

    const evaluationResults = document.getElementById("evaluationResults");
    evaluationResults.classList.remove("hidden");
    evaluationResults.classList.add("fade-in");
    evaluationResults.scrollIntoView({ behavior: "smooth" });

    document.getElementById("userLevel").textContent = data.current_level;
    document.getElementById("miniXpBar").firstElementChild.style.width =
      data.level_info.progress_percent + "%";
  } catch (error) {
    console.error("Error submitting answer:", error);
    document.getElementById("errorMessage").textContent =
      "Submission failed - server error";
  }
});

document
  .getElementById("rerollButton")
  .addEventListener("click", getNewQuestion);

// Categories Modal behavior
const settingsButton = document.getElementById("settingsButton");
const modalOverlay = document.getElementById("modalOverlay");
settingsButton.addEventListener("click", (e) => {
  e.stopPropagation();
  modalOverlay.classList.remove("hidden");
  document.getElementById("categoriesError").classList.add("hidden");
});

// Category item toggle for selection
document.querySelectorAll(".category-item").forEach((item) => {
  item.addEventListener("click", function (e) {
    this.classList.toggle("selected");
  });
});

// Prevent modal overlay from closing if no category is selected
modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) {
    if (document.querySelectorAll(".category-item.selected").length === 0) {
      document.getElementById("categoriesError").classList.remove("hidden");
    } else {
      modalOverlay.classList.add("hidden");
      updateSelectedCategories();
    }
  }
});

// Close modal on "Done" click
document.getElementById("closeCategories").addEventListener("click", (e) => {
  e.stopPropagation();
  if (document.querySelectorAll(".category-item.selected").length === 0) {
    document.getElementById("categoriesError").classList.remove("hidden");
    return;
  }
  modalOverlay.classList.add("hidden");
  updateSelectedCategories();
});

// Update selectedCategories based on selected items and possibly re-roll the question
function updateSelectedCategories() {
  selectedCategories = Array.from(
    document.querySelectorAll(".category-item.selected")
  ).map((el) => el.getAttribute("data-value"));
  if (
    currentQuestion &&
    !selectedCategories.includes(currentQuestion.category)
  ) {
    getNewQuestion();
  }
}

// Replace the DOMContentLoaded handler so that it checks for a previously stored question.
// If found, it displays that question instead of fetching a new one.
window.addEventListener("DOMContentLoaded", () => {
  updateSelectedCategories();
  const storedQuestion = sessionStorage.getItem("currentQuestion");
  if (storedQuestion) {
    currentQuestion = JSON.parse(storedQuestion);
    updateQuestionDisplay(currentQuestion);
  } else {
    getNewQuestion();
  }
});

// Question selection overlay handler
document
  .getElementById("selectQuestionButton")
  .addEventListener("click", () => {
    fetch("/get_all_questions")
      .then((response) => response.json())
      .then((questions) => {
        const questionList = document.getElementById("questionList");
        questionList.innerHTML = "";

        const filteredQuestions = questions.filter((q) =>
          selectedCategories.includes(q.category)
        );
        const groups = {};
        const categoryOrder = [];
        filteredQuestions.forEach((question) => {
          if (!groups[question.category]) {
            groups[question.category] = [];
            categoryOrder.push(question.category);
          }
          groups[question.category].push(question);
        });

        if (filteredQuestions.length === 0) {
          const noQuestionsItem = document.createElement("div");
          noQuestionsItem.className = "text-gray-600 py-2";
          noQuestionsItem.textContent =
            "No questions available for the selected categories.";
          questionList.appendChild(noQuestionsItem);
        } else {
          categoryOrder.forEach((category) => {
            const heading = document.createElement("h4");
            heading.className = "mt-4 mb-2 font-bold text-lg";
            heading.textContent = category;
            questionList.appendChild(heading);

            groups[category].forEach((question) => {
              const item = document.createElement("div");
              item.className =
                "question-item cursor-pointer p-2 border-b hover:bg-gray-100";
              item.textContent = question.description;
              item.dataset.id = question.id;
              item.addEventListener("click", () => {
                fetch("/select_question", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ question_id: question.id }),
                })
                  .then((response) => response.json())
                  .then((selected) => {
                    currentQuestion = selected;
                    const categoryText = categoryIcons[selected.category]
                      ? categoryIcons[selected.category] +
                        " " +
                        selected.category
                      : selected.category;
                    document.getElementById("categoryBadge").textContent =
                      categoryText;
                    typeWriter(
                      document.getElementById("questionDescription"),
                      selected.description,
                      15
                    );
                    document.getElementById("answerInput").value = "";
                    document.getElementById("charCount").textContent = "200";
                    document
                      .getElementById("evaluationResults")
                      .classList.add("hidden");
                    document.getElementById("errorMessage").textContent = "";
                    document
                      .getElementById("questionSelectionOverlay")
                      .classList.add("hidden");
                  })
                  .catch((error) =>
                    console.error("Error selecting question:", error)
                  );
              });
              questionList.appendChild(item);
            });
          });
        }
        document
          .getElementById("questionSelectionOverlay")
          .classList.remove("hidden");
      })
      .catch((error) => console.error("Error fetching questions:", error));
  });

document
  .getElementById("closeQuestionSelection")
  .addEventListener("click", () => {
    document.getElementById("questionSelectionOverlay").classList.add("hidden");
  });

document
  .getElementById("questionSelectionOverlay")
  .addEventListener("click", (e) => {
    if (e.target === document.getElementById("questionSelectionOverlay")) {
      document
        .getElementById("questionSelectionOverlay")
        .classList.add("hidden");
    }
  });
