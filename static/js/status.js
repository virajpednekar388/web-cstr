const KEY = "plc_connected_last";

function paint(connected) {
  const statusDiv = document.getElementById("status");

  if (connected === true) {
    statusDiv.textContent = "PLC CONNECTED";
    statusDiv.className = "connected";
  } else if (connected === false) {
    statusDiv.textContent = "PLC DISCONNECTED";
    statusDiv.className = "disconnected";
  } else {
    statusDiv.textContent = "Checking...";
    statusDiv.className = "unknown";
  }
}

// 1) Show last known status instantly on load (even after refresh)
const saved = localStorage.getItem(KEY);
if (saved === "true") paint(true);
else if (saved === "false") paint(false);
else paint(null);

// 2) Fetch latest status from Flask, then update UI + store it
async function checkPLC() {
  try {
    const res = await fetch("/plc-status", { cache: "no-store" });
    const data = await res.json();

    const connected = Boolean(data.connected);
    paint(connected);
    localStorage.setItem(KEY, String(connected));
  } catch (err) {
    // If API fails, show disconnected and store it
    paint(false);
    localStorage.setItem(KEY, "false");
  }
}

setInterval(checkPLC, 2000);
checkPLC();
