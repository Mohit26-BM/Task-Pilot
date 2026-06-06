function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function scorePassword(password) {
  let score = 0;
  if (password.length >= 8) score += 1;
  if (/[a-z]/.test(password)) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;
  return score;
}

function passwordMessage(password) {
  const missing = [];
  if (password.length < 8) missing.push("8+ characters");
  if (!/[a-z]/.test(password)) missing.push("lowercase");
  if (!/[A-Z]/.test(password)) missing.push("uppercase");
  if (!/\d/.test(password)) missing.push("number");
  if (!/[^A-Za-z0-9]/.test(password)) missing.push("symbol");
  return missing.length ? `Add ${missing.join(", ")}.` : "Strong password.";
}

function updateEmailHint(input, hint) {
  if (!input || !hint) return true;
  const value = input.value.trim();
  if (!value) {
    hint.textContent = "";
    hint.className = "field-hint";
    return false;
  }
  const valid = isValidEmail(value);
  hint.textContent = valid ? "Email looks good." : "Enter a valid email address.";
  hint.className = `field-hint ${valid ? "ok" : "error"}`;
  return valid;
}

function updateStrength() {
  const input = document.getElementById("signupPassword");
  const bar = document.getElementById("strengthBar");
  const label = document.getElementById("strengthLabel");
  const hint = document.getElementById("passwordHint");
  if (!input || !bar || !label) return 0;
  const score = scorePassword(input.value);
  bar.style.width = `${score * 20}%`;
  bar.className = score >= 5 ? "strong" : score >= 3 ? "medium" : "";
  const labelText = score >= 5 ? "Strong" : score >= 3 ? "Medium" : input.value ? "Weak" : "Waiting";
  label.textContent = `Password strength: ${labelText}`;
  if (hint) {
    hint.textContent = passwordMessage(input.value);
    hint.className = `field-hint ${score >= 5 ? "ok" : input.value ? "error" : ""}`;
  }
  return score;
}

document.getElementById("loginForm")?.email?.addEventListener("input", (event) => {
  updateEmailHint(event.currentTarget, document.getElementById("loginEmailHint"));
});

document.getElementById("signupForm")?.email?.addEventListener("input", (event) => {
  updateEmailHint(event.currentTarget, document.getElementById("signupEmailHint"));
});

document.getElementById("signupPassword")?.addEventListener("input", updateStrength);

document.getElementById("loginForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  if (!updateEmailHint(event.currentTarget.email, document.getElementById("loginEmailHint"))) {
    toast("Please enter a valid email address.", "error");
    return;
  }
  try {
    const data = await api("/login", { method: "POST", body: JSON.stringify(payload) });
    store.setSession(data.token, data.user);
    flash("Login successful");
    location.href = "/dashboard";
  } catch (error) {
    toast(error.message, "error");
  }
});

document.getElementById("signupForm")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  if (!updateEmailHint(event.currentTarget.email, document.getElementById("signupEmailHint"))) {
    toast("Please enter a valid email address.", "error");
    return;
  }
  if (updateStrength() < 5) {
    toast("Please choose a stronger password.", "error");
    return;
  }
  try {
    const data = await api("/signup", { method: "POST", body: JSON.stringify(payload) });
    store.setSession(data.token, data.user);
    flash("Signup successful. Welcome to TaskPilot.");
    location.href = "/dashboard";
  } catch (error) {
    toast(error.message, "error");
  }
});
