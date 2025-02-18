function showLoginModal() {
  const translations = window.translations || {};
  const modal = document.createElement("div");
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
         onclick="event.target === this && this.remove()">
      <div class="bg-white rounded-lg p-6 w-full max-w-md relative"
           onclick="event.stopPropagation()">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">${
            translations.auth?.loginTitle || "Login"
          }</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove(); event.stopPropagation()"
                  class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
        </div>
        <form id="loginForm" class="space-y-4">
          <div id="loginErrorMessage" class="text-sm text-red-500 mb-2 hidden"></div>
          <div>
            <label class="block text-sm font-medium mb-1">${
              translations.auth?.usernameOrEmail || "Username or Email"
            }</label>
            <input type="text" id="loginIdentity" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">${
              translations.auth?.password || "Password"
            }</label>
            <input type="password" id="loginPassword" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div class="text-right">
            <a href="#" onclick="showPasswordResetRequestModal()" class="text-sm text-blue-600 hover:text-blue-800">
              ${translations.auth?.forgotPassword || "Forgot Password?"}
            </a>
          </div>
          <div class="flex gap-4">
            <button type="submit" class="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
              ${translations.auth?.loginTitle || "Login"}
            </button>
            <button type="button" onclick="switchToSignup()" class="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300">
              ${translations.auth?.signupTitle || "Signup"}
            </button>
          </div>
        </form>
        <div id="googleButtonContainer" class="mt-4"></div>
        <div class="mt-6">
          <button onclick="handleGoogleAuth()"
                  class="w-full flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
            <svg class="w-5 h-5" viewBox="0 0 24 24">
              <path fill="currentColor" d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a5.94 5.94 0 1 1 0-11.88c1.094 0 2.354.371 3.227 1.067l2.355-2.362A9.914 9.914 0 0 0 12.545 2C7.021 2 2.545 6.477 2.545 12s4.476 10 10 10c5.523 0 10-4.477 10-10a9.9 9.9 0 0 0-1.091-4.571l-8.909 3.81z"/>
            </svg>
            ${translations.auth?.continueWithGoogle || "Continue with Google"}
          </button>
        </div>
      </div>
    </div>
  `;

  // Attach submit event listener after the modal is added to the DOM
  const loginForm = modal.querySelector("#loginForm");
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const identity = document.getElementById("loginIdentity").value;
    const password = document.getElementById("loginPassword").value;
    const errorMessage = document.getElementById("loginErrorMessage");

    try {
      errorMessage.textContent = "";
      errorMessage.classList.add("hidden");

      const response = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login: identity, password: password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw {
          status: response.status,
          message: data.error || "Login failed",
        };
      }

      if (data.user && data.user.preferred_language) {
        localStorage.setItem("language", data.user.preferred_language);
      }

      modal.remove();
      window.location.reload();
    } catch (error) {
      handleLoginError(error);
    }
  });

  // Remove any existing modal and append this one
  document.querySelectorAll("div.fixed.inset-0").forEach((el) => el.remove());
  document.body.appendChild(modal);
}

function showSignupModal() {
  const translations = window.translations || {};
  const modal = document.createElement("div");
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
         onclick="event.target === this && this.remove()">
      <div class="bg-white rounded-lg p-6 w-full max-w-md relative"
           onclick="event.stopPropagation()">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">${
            translations.auth?.signupTitle || "Signup"
          }</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove(); event.stopPropagation()"
                  class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
        </div>
        <form id="signupForm" class="space-y-4">
          <div id="signupErrorMessage" class="text-sm text-red-500 mb-2 hidden"></div>
          <div>
            <label class="block text-sm font-medium mb-1">${
              translations.auth?.username || "Username"
            }</label>
            <input type="text" id="signupUsername" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">${
              translations.auth?.email || "Email"
            }</label>
            <input type="email" id="signupEmail" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">${
              translations.auth?.password || "Password"
            }</label>
            <input type="password" id="signupPassword" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <div class="flex gap-4">
            <button type="button" onclick="switchToLogin()" class="flex-1 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300">
              ${translations.auth?.loginTitle || "Login"}
            </button>
            <button type="submit" class="flex-1 bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
              ${translations.auth?.signupTitle || "Signup"}
            </button>
          </div>
        </form>
        <div id="googleButtonContainer" class="mt-4"></div>
        <div class="mt-6">
          <button onclick="handleGoogleAuth()"
                  class="w-full flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
            <svg class="w-5 h-5" viewBox="0 0 24 24">
              <path fill="currentColor" d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a5.94 5.94 0 1 1 0-11.88c1.094 0 2.354.371 3.227 1.067l2.355-2.362A9.914 9.914 0 0 0 12.545 2C7.021 2 2.545 6.477 2.545 12s4.476 10 10 10c5.523 0 10-4.477 10-10a9.9 9.9 0 0 0-1.091-4.571l-8.909 3.81z"/>
            </svg>
            ${translations.auth?.continueWithGoogle || "Continue with Google"}
          </button>
        </div>
      </div>
    </div>
  `;

  const signupForm = modal.querySelector("#signupForm");
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = document.getElementById("signupUsername").value;
    const email = document.getElementById("signupEmail").value;
    const password = document.getElementById("signupPassword").value;
    const errorMessage = document.getElementById("signupErrorMessage");
    try {
      errorMessage.textContent = "";
      errorMessage.classList.add("hidden");
      const response = await fetch("/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Signup failed");
      modal.remove();
      window.location.reload();
    } catch (error) {
      handleSignupError(error);
    }
  });

  // Remove any existing modal and add this one
  document.querySelectorAll("div.fixed.inset-0").forEach((el) => el.remove());
  document.body.appendChild(modal);
}

function switchToSignup() {
  document.querySelectorAll("div.fixed.inset-0").forEach((el) => el.remove());
  showSignupModal();
}

function switchToLogin() {
  document.querySelectorAll("div.fixed.inset-0").forEach((el) => el.remove());
  showLoginModal();
}

// When someone wants to authenticate, call this to show the login modal by default.
function showAuthModal() {
  showLoginModal();
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
function handleGoogleAuthResponse(response) {
  if (!response.credential) {
    console.log("No token received");
    return;
  }

  // First try authenticating without username
  fetch("/google-auth", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: response.credential }),
  })
    .then((res) => {
      if (res.status === 400) {
        // If server requires username, show username prompt modal
        return res.json().then((data) => {
          if (data.error === "Username is required for Google signups.") {
            showGoogleUsernameModal(response.credential);
            throw new Error("username_required");
          }
          throw new Error(data.error || "Google authentication failed");
        });
      }
      if (!res.ok) {
        throw new Error("Google authentication failed");
      }
      return res.json();
    })
    .then((data) => {
      // Handle language preference
      if (data.user && data.user.preferred_language) {
        localStorage.setItem("language", data.user.preferred_language);
      }

      const authForm = document.querySelector("#authForm");
      if (authForm) {
        const modal = authForm.closest('div[class*="fixed inset-0"]');
        if (modal) modal.remove();
      }
      window.location.reload();
    })
    .catch((error) => {
      if (error.message !== "username_required") {
        console.error("Google auth error:", error);
        alert("Failed to authenticate with Google");
      }
    });
}

function showGoogleUsernameModal(credential) {
  const translations = window.translations || {};
  const modal = document.createElement("div");
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
         onclick="event.target === this && this.remove()">
      <div class="bg-white rounded-lg p-6 w-full max-w-md relative"
           onclick="event.stopPropagation()">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">${
            translations.auth?.googleAuth?.chooseUsername || "Choose Username"
          }</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove()"
                  class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
        </div>
        <form id="googleUsernameForm" class="space-y-4">
          <div id="googleUsernameError" class="text-sm text-red-500 mb-2 hidden"></div>
          <div>
            <label class="block text-sm font-medium mb-1">${
              translations.auth?.username || "Username"
            }</label>
            <p class="text-sm text-gray-500 mb-2">${
              translations.auth?.googleAuth?.usernameDescription
            }</p>
            <input type="text" id="googleUsername" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <button type="submit" class="w-full bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
            ${translations.auth?.googleAuth?.continue || "Continue"}
          </button>
        </form>
      </div>
    </div>
  `;

  const form = modal.querySelector("#googleUsernameForm");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const username = document.getElementById("googleUsername").value;
    const errorDiv = document.getElementById("googleUsernameError");

    fetch("/google-auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: credential, username }),
    })
      .then((res) => {
        if (!res.ok)
          return res.json().then((data) => Promise.reject(data.error));
        return res.json();
      })
      .then((data) => {
        if (data.user && data.user.preferred_language) {
          localStorage.setItem("language", data.user.preferred_language);
        }
        modal.remove();
        window.location.reload();
      })
      .catch((error) => {
        // Translate error messages
        if (error.includes("Username already exists")) {
          errorDiv.textContent =
            translations.auth?.googleAuth?.errors?.usernameExists || error;
        } else {
          errorDiv.textContent =
            translations.auth?.errors?.serverError || error;
        }
        errorDiv.classList.remove("hidden");
      });
  });

  document.body.appendChild(modal);
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

function showPasswordResetRequestModal() {
  const modal = document.createElement("div");
  modal.innerHTML = `
    <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4"
         onclick="event.target === this && this.remove()">
      <div class="bg-white rounded-lg p-6 w-full max-w-md relative"
           onclick="event.stopPropagation()">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">Reset Password</h3>
          <button onclick="this.parentElement.parentElement.parentElement.remove()"
                  class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
        </div>
        <form id="resetRequestForm" class="space-y-4">
          <div id="resetRequestMessage" class="text-sm mb-2 hidden"></div>
          <div>
            <label class="block text-sm font-medium mb-1">Email</label>
            <input type="email" id="resetEmail" required class="w-full px-3 py-2 border rounded-lg">
          </div>
          <button type="submit" class="w-full bg-gray-800 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
            Request Reset Link
          </button>
        </form>
      </div>
    </div>
  `;

  const form = modal.querySelector("#resetRequestForm");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("resetEmail").value;
    const messageDiv = document.getElementById("resetRequestMessage");

    try {
      const response = await fetch("/request-reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();
      messageDiv.textContent = data.message;
      messageDiv.classList.remove("hidden", "text-red-500");
      messageDiv.classList.add("text-green-500");

      // Clear form
      document.getElementById("resetEmail").value = "";
    } catch (error) {
      messageDiv.textContent = "Failed to send reset request";
      messageDiv.classList.remove("hidden", "text-green-500");
      messageDiv.classList.add("text-red-500");
    }
  });

  document.body.appendChild(modal);
}

function handleLoginError(error) {
  const translations = window.translations || {};
  const errorElement = document.getElementById("loginErrorMessage");
  errorElement.classList.remove("hidden");

  // Map HTTP status codes and error messages to translation keys
  let errorMessage;
  if (error.message.includes("Invalid credentials") || error.status === 401) {
    errorMessage = translations.auth?.errors?.invalidCredentials;
  } else if (error.message.includes("User not found")) {
    errorMessage = translations.auth?.errors?.userNotFound;
  } else if (error.message.includes("Too many attempts")) {
    errorMessage = translations.auth?.errors?.tooManyAttempts;
  } else {
    errorMessage = translations.auth?.errors?.serverError;
  }

  errorElement.textContent = errorMessage || error.message;
}

function handleSignupError(error) {
  const translations = window.translations || {};
  const errorElement = document.getElementById("signupErrorMessage");
  errorElement.classList.remove("hidden");

  let errorMessage;
  if (error.message.includes("Email already exists")) {
    errorMessage = translations.auth?.errors?.emailInUse;
  } else if (error.message.includes("Username already exists")) {
    errorMessage = translations.auth?.errors?.usernameInUse;
  } else if (error.message.includes("Password too weak")) {
    errorMessage = translations.auth?.errors?.weakPassword;
  } else if (error.message.includes("Invalid email")) {
    errorMessage = translations.auth?.errors?.invalidEmail;
  } else {
    errorMessage = translations.auth?.errors?.serverError;
  }

  errorElement.textContent = errorMessage || error.message;
}
