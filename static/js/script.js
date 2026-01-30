// function updatePumpStatus() {
//   fetch('/fetch_data')
//     .then(response => response.json())
//     .then(data => {
//       if (data.error) {
//         console.error(data.error);
//         document.getElementById("Temp-Value").innerText = "Error";
//         document.getElementById("pressure-value").innerText = "Error";
//         return;
//       }

//       const tempe = data.temperature;
//       const pressure = data.pressure;

//       document.getElementById("Temp-Value").innerText = tempe + "°C";
//       document.getElementById("pressure-value").innerText = pressure + "Bar";
//     })
//     .catch(err => console.error(err));
// }

// setInterval(updatePumpStatus, 300);


const tempEl = document.getElementById("Temp-Value");
const pressEl = document.getElementById("pressure-value");

let inFlight = false;

function fmt(val, unit, decimals = 0) {
  if (val === null || val === undefined) return `-- ${unit}`;
  const num = Number(val);
  if (!Number.isFinite(num)) return `-- ${unit}`;
  return `${num.toFixed(decimals)} ${unit}`;
}

async function updatePumpStatus() {
  if (inFlight) return;          // prevent overlap
  inFlight = true;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 1200); // 1.2s timeout

  try {
    const res = await fetch("/fetch_data", { signal: controller.signal });

    if (!res.ok) {
      // server error or auth issue
      tempEl.textContent = "Error";
      pressEl.textContent = "Error";
      return;
    }

    const data = await res.json();

    // If backend sends {error: "..."}
    if (data.error) {
      console.error("[fetch_data]", data.error);
      tempEl.textContent = "-- °C";
      pressEl.textContent = "-- bar";
      return;
    }

    // Handle null PLC values
    tempEl.textContent = fmt(data.temperature, "°C", 1);
    pressEl.textContent = fmt(data.pressure, "bar", 2);

  } catch (err) {
    // AbortError is expected sometimes if timeout happens
    console.error("[updatePumpStatus]", err);
    tempEl.textContent = "-- °C";
    pressEl.textContent = "-- bar";
  } finally {
    clearTimeout(timeoutId);
    inFlight = false;
  }
}

// SCADA-style poll rate (match PLC scan / sampler)
setInterval(updatePumpStatus, 1000);
updatePumpStatus(); // run immediately once





