



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
