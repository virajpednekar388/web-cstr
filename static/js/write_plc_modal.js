// ===================== MODAL OPEN/CLOSE =====================
const openBtn = document.getElementById("openWritePLCModal");
const overlay = document.getElementById("writePlcOverlay");
const closeBtn = document.getElementById("closeWritePLCModal");

function openModal() {
  overlay.classList.add("show");
  overlay.setAttribute("aria-hidden", "false");
}

function closeModal() {
  overlay.classList.remove("show");
  overlay.setAttribute("aria-hidden", "true");
}

if (openBtn) {
  openBtn.addEventListener("click", (e) => {
    e.preventDefault();
    openModal();
  });
}

if (closeBtn) closeBtn.addEventListener("click", closeModal);

// click outside modal closes
overlay.addEventListener("click", (e) => {
  if (e.target === overlay) closeModal();
});

// ESC closes
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && overlay.classList.contains("show")) closeModal();
});


// ===================== VALVE WRITE (calls Flask APIs) =====================
function updateSliderLabel(valveNum, value) {
  document.getElementById(`v${valveNum}Value`).textContent = `${value}%`;
}

function setValveStatus(valveNum, state, text) {
  const dot = document.getElementById(`v${valveNum}Dot`);
  const label = document.getElementById(`v${valveNum}StatusText`);

  dot.classList.remove("ok", "err", "busy");
  if (state) dot.classList.add(state);

  label.textContent = text || "Idle";
}

async function postValve(valveNum, payload) {
  const url = valveNum === 1 ? "/api/valve1" : "/api/valve2";

  setValveStatus(valveNum, "busy", "Sending...");

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok || data.ok === false) {
      setValveStatus(valveNum, "err", `Failed: ${data.error || "HTTP " + res.status}`);
      return;
    }

    if (payload.command) {
      setValveStatus(valveNum, "ok", `OK: ${payload.command.toUpperCase()}`);
    } else {
      setValveStatus(valveNum, "ok", `OK: set ${payload.percent}%`);
    }
  } catch (err) {
    setValveStatus(valveNum, "err", `Error: ${err.message}`);
  }
}

function sendValveCommand(valveNum, command) {
  postValve(valveNum, { command });
}

function sendValvePercent(valveNum) {
  const slider = document.getElementById(valveNum === 1 ? "v1Slider" : "v2Slider");
  const percent = parseInt(slider.value, 10);
  postValve(valveNum, { percent });
}
