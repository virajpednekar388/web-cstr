let chart = null;
let timer = null;
let paused = false;

function $(id){ return document.getElementById(id); }

function hideBaseStatus(){
  // base.html has #status for PLC; you said don't show status on Trends page
  const el = document.getElementById("status");
  if (el) el.style.display = "none";
}

function stepForWindow(windowMin){
  // downsample for big windows
  if (windowMin >= 1440) return 10;
  if (windowMin >= 720)  return 8;
  if (windowMin >= 360)  return 5;
  return 0;
}

async function loadWindow(){
  const windowMin = parseInt($("rangeSelect").value, 10);
  const step = stepForWindow(windowMin);

  const url = step > 0
    ? `/api/trends?window=${windowMin}&step=${step}`
    : `/api/trends?window=${windowMin}`;

  const res = await fetch(url);
  const data = await res.json();
  if (!data.ok) return;

  const t = data.points.map(p => ({ x: p.ts, y: p.temperature }));
  const p = data.points.map(p => ({ x: p.ts, y: p.pressure }));

  chart.updateSeries([
    { name: "Temperature", data: t },
    { name: "Pressure", data: p }
  ], false);
}

function startLive(){
  stopLive();
  loadWindow();
  timer = setInterval(() => {
    if (!paused) loadWindow();
  }, 2000);
}

function stopLive(){
  if (timer){
    clearInterval(timer);
    timer = null;
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  hideBaseStatus();

  const options = {
    chart: {
      type: "line",
      height: 440,
      animations: { enabled: false },
      toolbar: { show: true },
      zoom: { enabled: true, type: "x", autoScaleYaxis: true },
      foreColor: "#a8b3d6",
      events: {
        mounted: (c) => {
          c.el.addEventListener("dblclick", () => c.resetSeries());
        }
      }
    },
    stroke: { width: 2, curve: "smooth" },
    dataLabels: { enabled: false },
    grid: { borderColor: "rgba(255,255,255,.08)" },
    xaxis: { type: "datetime" },
    tooltip: { x: { format: "dd MMM HH:mm:ss" } },
    series: [
      { name: "Temperature", data: [] },
      { name: "Pressure", data: [] }
    ]
  };

  chart = new ApexCharts(document.querySelector("#trendChart"), options);
  await chart.render();

  $("rangeSelect").addEventListener("change", startLive);

  $("pauseBtn").addEventListener("click", () => paused = true);
  $("liveBtn").addEventListener("click", () => { paused = false; startLive(); });

  startLive();
});
