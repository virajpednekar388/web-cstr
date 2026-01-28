



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

setInterval(updatePumpStatus, 300);


document.querySelectorAll("nav a").forEach(a=>{
  if (a.href === window.location.href) a.classList.add("active");
});

document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector("nav");
  const btn = document.getElementById("navToggle");

  // restore
  const saved = localStorage.getItem("navState");
  if (saved === "expanded") {
    nav.classList.remove("collapsed");
    btn.setAttribute("aria-expanded", "true");
  } else {
    nav.classList.add("collapsed");
    btn.setAttribute("aria-expanded", "false");
  }

  // toggle
  btn.addEventListener("click", () => {
    const isCollapsed = nav.classList.toggle("collapsed");
    btn.setAttribute("aria-expanded", String(!isCollapsed));
    localStorage.setItem("navState", isCollapsed ? "collapsed" : "expanded");
  });
});


