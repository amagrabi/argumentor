// Category icons mapping with updated icons
const categoryIcons = {
  Philosophy: "📚",
  Ethics: "⚖️",
  "Business & Risk": "💼",
  "Thought Experiments": "💡",
  Politics: "🏛️",
  "Biases & Fallacies": "🔍",
  "AI & Future": "🤖",
  "Fun & Casual": "🎉",
};

const CHAR_LIMITS = {
  CLAIM: 200,
  ARGUMENT: 1000,
  COUNTERARGUMENT: 500,
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
    const categoryText = categoryIcons[question.category]
      ? `${categoryIcons[question.category]} ${question.category}`
      : question.category;
    categoryBadge.textContent = categoryText;
  }
}

// Modified getNewQuestion function:
// 1. It appends the selectedCategories as a query parameter to the request URL.
// 2. After fetching a new question, it stores that question in sessionStorage.
async function getNewQuestion(shouldScroll = true) {
  try {
    let query = "";
    if (selectedCategories.length > 0) {
      const encodedCategories = selectedCategories.map(encodeURIComponent);
      query = `?categories=${encodedCategories.join(",")}`;
    }
    const response = await fetch("/get_question" + query);
    const question = await response.json();
    if (question.error) {
      console.error("Error fetching new question:", question.error);
      return;
    }
    currentQuestion = question;
    sessionStorage.setItem("currentQuestion", JSON.stringify(question));

    document.getElementById("claimInput").value = "";
    document.getElementById("argumentInput").value = "";
    document.getElementById("counterargumentInput").value = "";

    // Animate the new question description
    const questionElem = document.getElementById("questionDescription");
    if (questionElem) {
      typeWriter(questionElem, question.description, 15);
    }

    // Update only the category badge, and not the question text again
    const categoryBadge = document.getElementById("categoryBadge");
    if (categoryBadge) {
      const categoryText = categoryIcons[question.category]
        ? `${categoryIcons[question.category]} ${question.category}`
        : question.category;
      categoryBadge.textContent = categoryText;
    }

    if (questionElem && shouldScroll) {
      questionElem.scrollIntoView({
        behavior: "smooth",
        block: "start",
        inline: "nearest",
      });

      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    }
  } catch (error) {
    console.error("Error fetching new question:", error);
  }
}

function showAuthModal() {
  const modal = document.createElement("div");
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
         onclick="event.target === this && this.remove()">
      <div class="bg-white rounded-lg p-6 w-full max-w-md relative"
           onclick="event.stopPropagation()">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">Login/Signup</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove(); event.stopPropagation()"
                  class="text-gray-500 hover:text-gray-700 text-2xl">
            &times;
          </button>
        </div>
        <!-- Email/Password Form -->
        <form id="authForm" class="space-y-4">
          <div id="authErrorMessage" class="text-sm text-red-500 mb-2 hidden"></div>
          <div>
            <label class="block text-sm font-medium mb-1">Username</label>
            <input type="text" id="authUsername" required
                  class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Password</label>
            <input type="password" id="authPassword" required
                  class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div class="flex gap-4">
            <button type="submit" class="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
              Login
            </button>
            <button type="button" onclick="handleAuth('signup')"
                    class="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300">
              Signup
            </button>
          </div>
        </form>
        <div id="googleButtonContainer" class="mt-4"></div>
        <!-- Google Login -->
        <div class="mt-6">
          <button onclick="handleGoogleAuth()"
                  class="w-full flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
            <svg class="w-5 h-5" viewBox="0 0 24 24"><path fill="currentColor" d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a5.94 5.94 0 1 1 0-11.88c1.094 0 2.354.371 3.227 1.067l2.355-2.362A9.914 9.914 0 0 0 12.545 2C7.021 2 2.545 6.477 2.545 12s4.476 10 10 10c5.523 0 10-4.477 10-10a9.9 9.9 0 0 0-1.091-4.571l-8.909 3.81z"/></svg>
            Continue with Google
          </button>
        </div>
      </div>
    </div>
  `;

  // Clear any existing modals first
  document
    .querySelectorAll('div[class*="fixed inset-0"]')
    .forEach((existingModal) => existingModal.remove());

  // Add ESC key listener
  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      modal.remove();
      document.removeEventListener("keydown", handleKeyDown);
    }
  };
  document.addEventListener("keydown", handleKeyDown);

  // Append modal to document
  document.body.appendChild(modal);

  // IMPORTANT: Attach submit event listener AFTER the modal (and its form) is added to the DOM
  const authForm = modal.querySelector("#authForm");
  authForm.addEventListener("submit", function (event) {
    event.preventDefault();
    handleAuth("login");
  });

  // Add input listeners to clear error messages
  modal.querySelectorAll("input").forEach((input) => {
    input.addEventListener("input", () => {
      document.getElementById("authErrorMessage").classList.add("hidden");
    });
  });
}

async function handleAuth(action) {
  const username = document.getElementById("authUsername").value;
  const password = document.getElementById("authPassword").value;
  const errorMessage = document.getElementById("authErrorMessage");

  try {
    errorMessage.textContent = "";
    errorMessage.classList.add("hidden");

    const response = await fetch(`/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const contentType = response.headers.get("content-type");
    const data = contentType?.includes("json")
      ? await response.json()
      : { error: await response.text() };

    if (!response.ok) throw new Error(data.error || "Authentication failed");
    window.location.reload();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.classList.remove("hidden");
  }
}

async function handleLogout() {
  try {
    const response = await fetch("/logout", { method: "POST" });
    if (response.ok) {
      window.location.reload();
    }
  } catch (error) {
    console.error("Logout failed:", error);
  }
}

// Initialize Google client
function initGoogleAuth() {
  const meta = document.querySelector('meta[name="google-signin-client_id"]');
  const clientId = meta ? meta.getAttribute("content") : "";
  google.accounts.id.initialize({
    client_id: clientId,
    callback: handleGoogleAuthResponse,
  });
}

// Handle Google auth button click
function handleGoogleAuth() {
  console.log("Google auth button clicked");
  if (google && google.accounts && google.accounts.id) {
    google.accounts.id.prompt((notification) => {
      console.log("Google prompt response:", notification);
    });
  } else {
    console.error(
      "Google API not available. Check if the script loaded properly."
    );
  }
}

// Handle Google auth response
async function handleGoogleAuthResponse(response) {
  try {
    const res = await fetch("/google-auth", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ token: response.credential }),
    });

    if (!res.ok) throw new Error("Google authentication failed");
    window.location.reload();
  } catch (error) {
    console.error("Google auth error:", error);
    alert("Failed to authenticate with Google");
  }
}

// Load Google library and initialize
(function loadGoogleAuth() {
  const script = document.createElement("script");
  script.src = "https://accounts.google.com/gsi/client";
  script.async = true;
  script.defer = true;
  document.head.appendChild(script);
  script.onload = initGoogleAuth;
})();

// Update character counters
const setupCharCounter = (inputId, countId, fieldName) => {
  const input = document.getElementById(inputId);
  const count = document.getElementById(countId);
  if (input && count) {
    const maxLength = CHAR_LIMITS[fieldName.toUpperCase()];
    input.setAttribute("maxlength", maxLength);
    count.textContent = maxLength;

    input.addEventListener("input", () => {
      const remaining = maxLength - input.value.length;
      count.textContent = remaining;
      // Clear error message on any input
      document.getElementById("errorMessage").textContent = "";
      // Additional check to clear message when requirements are met
      if (
        input.value.length > 0 &&
        document.getElementById("errorMessage").textContent
      ) {
        document.getElementById("errorMessage").textContent = "";
      }
    });
  }
};

// Initialize all counters
setupCharCounter("claimInput", "claimCount", "claim");
setupCharCounter("argumentInput", "argumentCount", "argument");
setupCharCounter(
  "counterargumentInput",
  "counterargumentCount",
  "counterargument"
);

// Updated submission handler
document.getElementById("submitAnswer").addEventListener("click", async () => {
  const startTime = Date.now();
  const claim = document.getElementById("claimInput").value.trim();
  const argument = document.getElementById("argumentInput").value.trim();
  const submitBtn = document.getElementById("submitAnswer");
  const counterargument = document
    .getElementById("counterargumentInput")
    .value.trim();

  if (!claim || !argument) {
    document.getElementById("errorMessage").textContent =
      "Please fill in both required fields (Claim and Argument) before submitting.";
    return;
  }

  const payload = {
    claim,
    argument,
    counterargument: counterargument || null,
  };

  if (currentQuestion?.id) {
    payload.question_id = currentQuestion.id;
  }

  // Disable button and show loading state
  submitBtn.innerHTML = `
    <span class="loading-dots">
      <span class="animate-pulse">Analyzing</span>
    </span>
  `;
  submitBtn.disabled = true;

  try {
    const response = await fetch("/submit_answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    // Calculate remaining time only for successful responses
    if (response.ok) {
      const elapsed = Date.now() - startTime;
      if (elapsed < 2000) {
        await new Promise((resolve) => setTimeout(resolve, 2000 - elapsed));
      }
    }

    const data = await response.json(); // Single parse here

    if (!response.ok) {
      document.getElementById("errorMessage").textContent =
        data.error || "Submission failed"; // Use 'data' instead of 'errorData'
      submitBtn.innerHTML = "Submit";
      submitBtn.disabled = false;
      return;
    }

    if (!data || !data.evaluation) {
      document.getElementById("errorMessage").textContent =
        "Invalid response from server";
      submitBtn.innerHTML = "Submit";
      submitBtn.disabled = false;
      return;
    }

    submitBtn.innerHTML = "Submit";
    submitBtn.disabled = false;

    // First display overall evaluation with a prominent total score bar
    const overallEvalDiv = document.getElementById("overallEvaluation");
    const totalScore = data.evaluation.total_score;
    const totalScorePercent = totalScore * 10; // converts out of 10 to percent (e.g. 7 -> 70%)
    const totalScoreColor = scoreToColor(totalScore);

    overallEvalDiv.innerHTML = `
    <p class="text-l font-bold mb-2">
      Total Score: <span id="totalScoreValue">${totalScore.toFixed(1)}/10</span>
    </p>
    <div class="w-full bg-gray-200 rounded-full h-4 mb-2">
      <div id="totalScoreBar" class="rounded-full total-progress-bar" style="width: 10%; background-color: #e53e3e;"></div>
    </div>
    <p id="overallFeedback" class="text-md">
      ${data.evaluation.overall_feedback}
    </p>
  `;

    // Remove line 258 that sets the text color of the entire paragraph
    // Add this instead to color just the score value:
    document.getElementById("totalScoreValue").style.color = totalScoreColor;

    // Animate the total score bar (a short delay allows a smooth transition)
    setTimeout(() => {
      const totalScoreBar = document.getElementById("totalScoreBar");
      totalScoreBar.style.width = totalScorePercent + "%";
      totalScoreBar.style.backgroundColor = totalScoreColor;
    }, 50);

    // Now populate the detailed individual factor scores (the look and animation remain unchanged)
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
          void fill.offsetWidth; // Trigger reflow
          fill.style.width = targetWidth + "%";
          fill.style.backgroundColor = targetColor;
        }, delay);
      });
      document
        .querySelectorAll(".score-value")
        .forEach((scoreElement, index) => {
          const finalScore = parseFloat(scoreElement.dataset.final);
          const targetColor = scoreElement.dataset.color;
          const startColor = hexToRgb("#e53e3e");
          const endColor = hexToRgb(targetColor);
          let current = 1;
          const updateScore = () => {
            if (current <= finalScore) {
              const factor = (current - 1) / 9;
              const interpolated = interpolateColor(
                startColor,
                endColor,
                factor
              );
              scoreElement.style.color = rgbToHex(
                interpolated.r,
                interpolated.g,
                interpolated.b
              );
              scoreElement.textContent = `${current}/10`;
              current++;
              requestAnimationFrame(updateScore);
            }
          };
          requestAnimationFrame(updateScore);
        });
      document.querySelectorAll(".feedback").forEach((paragraph, index) => {
        const delay = index * 100;
        setTimeout(() => {
          typeWriter(paragraph, paragraph.getAttribute("data-final"), 15);
        }, delay);
      });
    }, 100);

    // Update XP and level info as before...
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
    evaluationResults.style.display = "block";
    evaluationResults.classList.add("fade-in");
    evaluationResults.scrollIntoView({ behavior: "smooth" });
    document.getElementById("userLevel").textContent = data.current_level;
    document.getElementById("miniXpBar").firstElementChild.style.width =
      data.level_info.progress_percent + "%";
  } catch (error) {
    console.error("Error submitting answer:", error);
    document.getElementById("errorMessage").textContent =
      "Submission failed, server error. It's not you it's me, sorry. Send me feedback if the issues persists.";
    submitBtn.textContent = "Submit";
    submitBtn.disabled = false;
  }
});

document
  .getElementById("rerollButton")
  .addEventListener("click", () => getNewQuestion(false));

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
    getNewQuestion(false).then(() => {
      document.getElementById("claimInput").value = "";
      document.getElementById("argumentInput").value = "";
      document.getElementById("counterargumentInput").value = "";
    });
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
                // Immediately hide the question selection overlay
                const overlay = document.getElementById(
                  "questionSelectionOverlay"
                );
                overlay.classList.add("hidden");

                // Now fetch and update with the selected question
                fetch("/select_question", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ question_id: question.id }),
                })
                  .then((response) => response.json())
                  .then((selected) => {
                    currentQuestion = selected;
                    updateQuestionDisplay(selected);
                    typeWriter(
                      document.getElementById("questionDescription"),
                      selected.description,
                      15
                    );
                    // Clear the input fields
                    document.getElementById("claimInput").value = "";
                    document.getElementById("argumentInput").value = "";
                    document.getElementById("counterargumentInput").value = "";
                    document.getElementById("charCount").textContent = "200";
                    document.getElementById("errorMessage").textContent = "";
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

document.getElementById("nextQuestion").addEventListener("click", async () => {
  try {
    // Completely clear the evaluation section
    const evaluationResults = document.getElementById("evaluationResults");
    // Hide the entire evaluation container
    evaluationResults.classList.add("hidden");
    evaluationResults.style.display = "none";
    // Clear all inner content so nothing remains visible:
    const scoresDiv = document.getElementById("scores");
    scoresDiv.innerHTML = "";

    // Now get a new question and scroll to it
    await getNewQuestion(true);

    // Reset input fields
    document.getElementById("claimInput").value = "";
    document.getElementById("argumentInput").value = "";
    document.getElementById("counterargumentInput").value = "";

    // Scroll to the question section
    document.getElementById("questionDescription").scrollIntoView({
      behavior: "smooth",
      block: "start",
      inline: "nearest",
    });
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  } catch (error) {
    console.error("Error loading new question:", error);
    document.getElementById("errorMessage").textContent =
      "Failed to load new question";
  }
});

document
  .getElementById("loginForm")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    // Call your login function (for example, handleLogin)
    handleLogin();
  });
