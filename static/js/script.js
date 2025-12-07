

// pump status code 

function updatePumpStatus() {
  fetch('/get_pump_status')  // Flask route returns JSON like {"pump": true}
    .then(response => response.json())
    .then(data => {
      const pumpImg = document.getElementById('pumpStatus');
      const pumpText = document.getElementById('heater-pump');

      if (data.pump) {
        pumpImg.classList.add('running');      // Start animation
        pumpText.innerText = "ON";             // Set text
        pumpText.style.color = "green";        // Set color
      } else {
        pumpImg.classList.remove('running');   // Stop animation
        pumpText.innerText = "OFF";
        pumpText.style.color = "red";
      }
    })
    .catch(err => console.error(err));
}

// Check every 2 seconds
setInterval(updatePumpStatus, 2000);




function updatePumpStatus() {
  fetch('/fetch_data')
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        console.error(data.error);
        document.getElementById("Temp-Value").innerText = "Error";
        document.getElementById("pressure-value").innerText = "Error";
        return;
      }

      const tempe = data.temperature;
      const pressure = data.pressure;

      document.getElementById("Temp-Value").innerText = tempe + "°C";
      document.getElementById("pressure-value").innerText = pressure + "Bar";
    })
    .catch(err => console.error(err));
}

setInterval(updatePumpStatus, 2000);




// static/js/main.js

let tempChart = null;
let pressureChart = null;
let liveIntervalId = null;
const LIVE_POLL_MS = 2000; // live update frequency used by front-end display

// ---------- Charts init ----------
function mainInitCharts() {
  // temperature
  tempChart = new ApexCharts(document.querySelector("#tempChart"), {
    chart: { type: 'area', height: 350, animations: { enabled: true }, toolbar: { show: true } },
    series: [{ name: 'Temperature', data: [] }],
    xaxis: { type: 'datetime', labels: { format: 'HH:mm:ss' } },
    yaxis: { title: { text: 'Temperature (°C)' } },
    stroke: { curve: 'smooth', width: 3 },
    markers: { size: 4 },
    tooltip: { shared: true, intersect: false, y: { formatter: val => Number(val).toFixed(2) } }
  });
  tempChart.render();

  // pressure
  pressureChart = new ApexCharts(document.querySelector("#pressureChart"), {
    chart: { type: 'area', height: 350, animations: { enabled: true }, toolbar: { show: true } },
    series: [{ name: 'Pressure', data: [] }],
    xaxis: { type: 'datetime', labels: { format: 'HH:mm:ss' } },
    yaxis: { title: { text: 'Pressure' } },
    stroke: { curve: 'smooth', width: 3 },
    markers: { size: 4 },
    tooltip: { shared: true, intersect: false, y: { formatter: val => Number(val).toFixed(2) } }
  });
  pressureChart.render();

  // start live polling for charts
  mainStartLiveView();
}

// ---------- Live polling (single fetch) ----------
async function mainFetchLiveOnce() {
  try {
    const res = await fetch('/fetch_data');
    const data = await res.json();
    if (data && data.temperature != null && data.pressure != null) {
      const t = new Date().getTime();
      // Append to charts
      tempChart.appendData([{ data: [{ x: t, y: data.temperature }] }]);
      pressureChart.appendData([{ data: [{ x: t, y: data.pressure }] }]);
    }
  } catch (e) {
    console.error("Live fetch error:", e);
  }
}

function mainStartLiveView() {
  if (liveIntervalId) return;
  mainFetchLiveOnce();
  liveIntervalId = setInterval(mainFetchLiveOnce, LIVE_POLL_MS);
  console.log("[main] Live view started");
}

function mainStopLiveView() {
  if (liveIntervalId) {
    clearInterval(liveIntervalId);
    liveIntervalId = null;
    console.log("[main] Live view stopped");
  }
}

// ---------- Historical loading for charts ----------
async function mainLoadHistorical(type, duration) {
  try {
    const res = await fetch(`/historian?duration=${duration}`);
    const rows = await res.json();
    if (!Array.isArray(rows)) return;

    const seriesData = rows.map(r => {
      return { x: new Date(r.timestamp).getTime(), y: (type === 'temperature' ? r.temperature : r.pressure) };
    });

    if (type === 'temperature') {
      tempChart.updateSeries([{ name: 'Temperature', data: seriesData }]);
    } else {
      pressureChart.updateSeries([{ name: 'Pressure', data: seriesData }]);
    }
  } catch (e) {
    console.error("Load historical error:", e);
  }
}

// ---------- DataLog: load history into table ----------
async function mainLoadDataLog() {
  try {
    const res = await fetch('/historian?duration=all');
    const rows = await res.json();
    const tbody = document.getElementById('dataBody');
    tbody.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${r.timestamp}</td><td>${r.temperature}</td><td>${r.pressure}</td>`;
      tbody.appendChild(tr);
    });
  } catch (e) {
    console.error("Load datalog error:", e);
  }
}

// ---------- Export & UI helpers ----------
function mainDownloadExcel() {
  // build array of arrays from table
  const table = document.getElementById('dataTable');
  const rows = Array.from(table.querySelectorAll('tr'));
  const data = rows.map(row => Array.from(row.querySelectorAll('th,td')).map(cell => cell.innerText));
  if (data.length <= 1) {
    alert("No data to export");
    return;
  }
  const ws = XLSX.utils.aoa_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "PLC_Log");
  XLSX.writeFile(wb, "Data_Log.xlsx");
}

function mainClearTable() {
  const tbody = document.getElementById('dataBody');
  tbody.innerHTML = '';
}

// Convenience wrappers bound in DataLog.html
function mainStartLiveView() { /* uses the charts' start; reuse same function */ mainStartLiveView.__proto__.call(); }
function mainStopLiveView()  { /* placeholder if bound externally, actual stop implemented above */ mainStopLiveView.__proto__.call(); }

// The above convenience wrappers are used only for binding in templates.
// In some environments you might prefer direct bindings to mainStartLiveView/mainStopLiveView functions.
