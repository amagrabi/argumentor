// Initialize mermaid
mermaid.initialize({
  startOnLoad: true,
  theme: "neutral",
  flowchart: {
    curve: "basis",
    padding: 15,
    nodeSpacing: 50,
    rankSpacing: 50,
  },
});

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

// Add new function to handle session update and UI refresh
async function updateAuthUI(userData, redirect = false) {
  try {
    const response = await fetch("/update_session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(userData || {}),
    });
    if (!response.ok) throw new Error("Failed to update session");

    const result = await response.json();
    const info = result.user || result;

    // Update UI elements if present. For example:
    const loginButton = document.querySelector("#loginButton");
    if (loginButton) {
      const logoutButton = document.createElement("button");
      logoutButton.className =
        "bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-full text-sm";
      logoutButton.onclick = handleLogout;
      logoutButton.textContent = "Logout";
      loginButton.replaceWith(logoutButton);
      console.log("Login button replaced with logout button");
    } else {
      console.log("Login button not found, assuming already logged in.");
    }

    // Update other header elements as needed.
    const userLevelElem = document.getElementById("userLevelElem");
    if (userLevelElem) {
      userLevelElem.textContent = info.level_info.display_name;
      console.log("User level updated:", info.level_info.display_name);
    } else {
      console.warn("User level element not found.");
    }

    const miniXpBarFill = document.getElementById("miniXpBarFill");
    if (miniXpBarFill) {
      miniXpBarFill.style.width = info.level_info.progress_percent + "%";
      console.log("XP bar updated:", info.level_info.progress_percent + "%");
    } else {
      console.warn("Mini XP bar element not found.");
    }

    if (redirect) {
      window.location.replace("/profile");
    }
  } catch (error) {
    console.error("Failed to update session:", error);
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

  // Before processing the new response, clear any previous challenge content:
  const challengeSection = document.getElementById("challengeSection");
  if (challengeSection) {
    challengeSection.classList.add("hidden");
  }
  const challengeResponseInput = document.getElementById(
    "challengeResponseInput"
  );
  if (challengeResponseInput) {
    challengeResponseInput.value = "";
  }
  const challengeEvalDiv = document.getElementById(
    "challengeEvaluationResults"
  );
  if (challengeEvalDiv) {
    challengeEvalDiv.innerHTML = "";
    challengeEvalDiv.classList.add("hidden");
  }
  document.getElementById("challengeErrorMessage").textContent = "";

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

    console.log("Evaluation response:", data.evaluation);

    submitBtn.innerHTML = "Submit";
    submitBtn.disabled = false;

    // First display overall evaluation with a prominent total score bar
    const overallEvalDiv = document.getElementById("overallEvaluation");
    const totalScore = data.evaluation.total_score;
    const totalScorePercent = totalScore * 10;
    const totalScoreColor = scoreToColor(totalScore);

    overallEvalDiv.innerHTML = `
      <p class="text-l font-bold mb-2">
        Total Score: <span id="totalScoreValue">${totalScore.toFixed(
          1
        )}/10</span>
      </p>
      <div class="w-full bg-gray-200 rounded-full h-4 mb-2">
        <div id="totalScoreBar" class="rounded-full total-progress-bar" style="width: 10%; background-color: #e53e3e;"></div>
      </div>
      <p id="overallFeedback" class="text-md">
        ${data.evaluation.overall_feedback}
      </p>
    `;

    // Add argument structure visualization if available
    if (data.evaluation.argument_structure) {
      const structure = data.evaluation.argument_structure;
      overallEvalDiv.innerHTML += `
        <div class="mt-6 p-4 bg-gray-50 rounded-lg">
          <h3 class="text-lg font-bold mb-2">Argument Structure</h3>
          <div id="argumentStructureViz" class="overflow-x-auto"></div>
        </div>
      `;

      const graph = `graph TD;
        ${structure.nodes
          .map(
            (node) =>
              `${node.id}["${node.type === "premise" ? "💭" : "✨"} ${
                node.text
              }"]`
          )
          .join(";\n")}
        ${structure.edges
          .map((edge) => `${edge.from}-->${edge.to}`)
          .join(";\n")}
      `;

      mermaid
        .render("argumentGraph", graph)
        .then((result) => {
          document.getElementById("argumentStructureViz").innerHTML =
            result.svg;
        })
        .catch((error) => {
          console.error("Failed to render argument structure:", error);
        });
    }

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

    // Update header elements immediately after answer submission
    const userLevelElem = document.getElementById("userLevelElem");
    if (userLevelElem) {
      userLevelElem.textContent = data.current_level;
    }

    const miniXpBarFill = document.getElementById("miniXpBarFill");
    if (miniXpBarFill) {
      miniXpBarFill.style.width = data.level_info.progress_percent + "%";
    }

    // After a successful answer submission, store the answer ID for later use:
    if (data.answer_id) {
      sessionStorage.setItem("lastAnswerId", data.answer_id);
    }

    // If the evaluation contains a challenge, display the challenge text and reveal the challenge section.
    if (data.evaluation.challenge) {
      const challengeSection = document.getElementById("challengeSection");
      const challengeTextElem = document.getElementById("challengeText");
      challengeTextElem.textContent = data.evaluation.challenge;
      challengeSection.classList.remove("hidden");
    }

    // Update character count for the challenge response text area.
    document
      .getElementById("challengeResponseInput")
      .addEventListener("input", (e) => {
        const max = 1000;
        const remaining = max - e.target.value.length;
        document.getElementById("challengeCount").textContent = remaining;
      });

    // Challenge Response submission handler.
    document
      .getElementById("submitChallengeResponse")
      .addEventListener("click", async () => {
        const startTime = Date.now(); // Add timestamp tracking
        const challengeResponse = document
          .getElementById("challengeResponseInput")
          .value.trim();
        const challengeErrorMessage = document.getElementById(
          "challengeErrorMessage"
        );
        if (!challengeResponse) {
          challengeErrorMessage.textContent =
            "Please provide a response to the challenge.";
          return;
        }
        const answerId = sessionStorage.getItem("lastAnswerId");
        if (!answerId) {
          challengeErrorMessage.textContent = "No associated answer found.";
          return;
        }

        const submitBtn = document.getElementById("submitChallengeResponse");
        submitBtn.innerHTML = `
          <span class="loading-dots">
            <span class="animate-pulse">Analyzing</span>
          </span>
        `;
        submitBtn.disabled = true;

        try {
          const response = await fetch("/submit_challenge_response", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              challenge_response: challengeResponse,
              answer_id: answerId,
            }),
          });

          // Calculate and enforce minimum display time
          if (response.ok) {
            const elapsed = Date.now() - startTime;
            if (elapsed < 3000) {
              await new Promise((resolve) =>
                setTimeout(resolve, 3000 - elapsed)
              );
            }
          }

          const data = await response.json();
          if (!response.ok) {
            challengeErrorMessage.textContent =
              data.error || "Submission failed";
            submitBtn.innerHTML = "Submit";
            submitBtn.disabled = false;
            return;
          }

          // Display detailed challenge evaluation feedback similar to primary evaluation.
          const challengeEvalDiv = document.getElementById(
            "challengeEvaluationResults"
          );
          const totalScore = data.evaluation.total_score;
          const totalScorePercent = totalScore * 10; // Scale (e.g., 7 -> 70%)
          const totalScoreColor = scoreToColor(totalScore);

          challengeEvalDiv.innerHTML = `
          <p class="text-l font-bold mb-2">
            Challenge Response Total Score: <span id="challengeTotalScoreValue" style="color: ${totalScoreColor};">${totalScore.toFixed(
            1
          )}/10</span>
          </p>
          <div class="w-full bg-gray-200 rounded-full h-4 mb-2">
            <div id="challengeTotalScoreBar" class="rounded-full total-progress-bar"
              style="width: ${totalScorePercent}%; background-color: ${totalScoreColor};">
            </div>
          </div>
          <p id="challengeOverallFeedback" class="text-md">${
            data.evaluation.overall_feedback
          }</p>
          <div class="flex flex-wrap gap-2 mt-2">
            ${Object.entries(data.evaluation.scores)
              .filter(([key]) => key.toLowerCase() !== "overall")
              .map(
                ([category, score]) =>
                  `<div class="px-2 py-1 rounded-full text-xs" style="background-color: ${scoreToColor(
                    score
                  )};">
                    ${category}: ${score}/10
                  </div>`
              )
              .join("")}
          </div>
        `;
          challengeEvalDiv.classList.remove("hidden");

          // Update XP and level info.
          document.getElementById("xpGained").innerHTML =
            "<strong>" + data.challenge_xp_earned + "</strong>";
          document.getElementById("currentLevel").innerHTML =
            "<strong>" + data.current_level + "</strong>";
          document.getElementById("xpProgressText").textContent =
            data.level_info.xp_into_level + " / " + data.level_info.xp_needed;
          document.getElementById("nextLevel").textContent =
            data.level_info.next_level;

          submitBtn.innerHTML = "Submit";
          submitBtn.disabled = false;
        } catch (error) {
          console.error("Error submitting challenge response:", error);
          challengeErrorMessage.textContent =
            "Submission failed, server error. Please try again.";
          submitBtn.innerHTML = "Submit";
          submitBtn.disabled = false;
        }
      });
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

const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", function (event) {
    event.preventDefault();
    handleLogin();
  });
}
