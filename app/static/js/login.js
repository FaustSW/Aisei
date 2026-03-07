let profiles = [];
let selectedProfile = null;

/* ============================================================================================================== */
/* LOAD PROFILES FROM BACKEND */
/* ============================================================================================================== */

function loadProfiles() {
  // Profiles are injected into the page by the backend template
  if (typeof PROFILES_FROM_DB !== "undefined") {
    profiles = PROFILES_FROM_DB;
  }
  renderProfiles();
}

/* ============================================================================================================== */
/* DISPLAY ALL PROFILE CARDS */
/* ============================================================================================================== */

function renderProfiles() {
  const grid = document.getElementById("profilesGrid");
  grid.innerHTML = "";

  profiles.forEach((profile) => {
    const profileCard = document.createElement("div");
    profileCard.className = "profile-card";
    profileCard.onclick = (event) => selectProfile(profile, event);

    profileCard.innerHTML = `
                    <button class="remove-btn" onclick="removeProfile(event, ${profile.id})">×</button>
                    <div class="profile-avatar ${profile.avatar}">${profile.initials}</div>
                    <div class="profile-name">${profile.name}</div>
                    <div class="profile-username">@${profile.username}</div>
                `;

    grid.appendChild(profileCard);
  });
}

/* ============================================================================================================== */
/* PROFILE CLICK */
/* ============================================================================================================== */

function selectProfile(profile, event) {
  selectedProfile = profile;

  document.querySelectorAll(".profile-card").forEach((card) => {
    card.classList.remove("selected");
  });

  event.currentTarget.classList.add("selected");
  document.getElementById("selectedProfileName").textContent =
    `Enter password for ${profile.name}`;
  document.getElementById("passwordSection").style.display = "block";
  document.getElementById("passwordInput").value = "";
  document.getElementById("passwordInput").focus();
  document.getElementById("message").style.display = "none";
  document.getElementById("passwordError").classList.remove("show");
}

/* ============================================================================================================== */
/* REMOVE PROFILE */
/* ============================================================================================================== */

function removeProfile(event, profileId) {
  event.stopPropagation();

  const profile = profiles.find((p) => p.id === profileId);
  if (!profile) return;

  if (confirm(`Are you sure you want to delete ${profile.name}?`)) {
    fetch("/delete_user", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: profileId }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.ok) {
          profiles = profiles.filter((p) => p.id !== profileId);
          renderProfiles();
          selectedProfile = null;
          document.getElementById("passwordSection").style.display = "none";
          document.getElementById("selectedProfileName").textContent =
            "Select a profile to continue";
          document.getElementById("message").style.display = "none";
          showMessage(`✅ ${profile.name} has been deleted!`, "success");
        } else {
          showMessage(
            "Error deleting profile: " + (data.error || "unknown"),
            "error",
          );
        }
      })
      .catch((err) => {
        console.error("Error:", err);
        showMessage("Error deleting profile", "error");
      });
  }
}

/* ============================================================================================================== */
/* CHECK PASSWORD & LOGIN */
/* ============================================================================================================== */

function handleLogin() {
  if (!selectedProfile) {
    showMessage("Please select a profile", "error");
    return;
  }

  const password = document.getElementById("passwordInput").value;

  // Check if password matches
  if (password === selectedProfile.password) {
    // Password is CORRECT
    document.getElementById("passwordError").classList.remove("show");
    showMessage(`✅ Welcome, ${selectedProfile.name}!`, "success");

    // POST to backend to set session
    fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: selectedProfile.username }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.ok) {
          window.location.href = "/go_to_review";
        } else {
          showMessage(
            "Error logging in: " + (data.error || "unknown"),
            "error",
          );
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        showMessage("Error logging in", "error");
      });
  } else {
    // Password is WRONG
    document.getElementById("passwordError").classList.add("show");
    document.getElementById("passwordInput").value = "";
    document.getElementById("passwordInput").focus();
  }
}

function showMessage(text, type) {
  const messageDiv = document.getElementById("message");
  messageDiv.textContent = text;
  messageDiv.className = `message ${type}`;
}

/* ============================================================================================================== */
/* OPEN/CLOSE POP UP (add profile pop up) */
/* ============================================================================================================== */

function openAddProfileModal() {
  document.getElementById("addProfileModal").classList.add("show");
}

function closeAddProfileModal() {
  document.getElementById("addProfileModal").classList.remove("show");
  document.getElementById("createProfileForm").reset();
}

/* ============================================================================================================== */
/* CREATE NEW PROFILE */
/* ============================================================================================================== */

document
  .getElementById("createProfileForm")
  .addEventListener("submit", function (e) {
    e.preventDefault();

    const name = document.getElementById("newUsername").value.trim();
    const username = document.getElementById("newLoginUsername").value.trim();
    const password = document.getElementById("newPassword").value;

    if (profiles.find((p) => p.username === username)) {
      alert("Username already exists!");
      return;
    }

    const avatarClass = `avatar-${(profiles.length % 5) + 1}`;

    // POST to backend to create user in DB
    fetch("/create_user", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        username: username,
        password: password,
        avatar: avatarClass,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.ok) {
          profiles.push(data.profile);
          renderProfiles();
          closeAddProfileModal();
          showMessage("✅ Profile created successfully!", "success");
        } else {
          alert("Error: " + (data.error || "unknown"));
        }
      })
      .catch((err) => {
        console.error("Error:", err);
        alert("Error creating profile");
      });
  });

/* ============================================================================================================== */
/* EXTRA - for extra functions */
/* ============================================================================================================== */

// Close pop-up when clicking outside of it
window.onclick = function (event) {
  const modal = document.getElementById("addProfileModal");
  if (event.target === modal) {
    closeAddProfileModal();
  }
};

// Press Enter key to login instead of clicking button
document
  .getElementById("passwordInput")
  .addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      handleLogin();
    }
  });

// Load all profiles when page first opens
loadProfiles();
