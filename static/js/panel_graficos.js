/* RF-27: gráfico de líneas con la evolución de las tasas por campaña (Chart.js). */
(function () {
  "use strict";

  var lienzo = document.getElementById("grafico-campanas");
  var fuente = document.getElementById("datos-grafico");
  if (!lienzo || !fuente || typeof Chart === "undefined") {
    return;
  }
  var datos = JSON.parse(fuente.textContent);

  // Paleta categórica validada (CVD y contraste): ranura 1 azul, ranura 2 naranja.
  var AZUL = "#2a78d6";
  var NARANJA = "#eb6834";
  var TEXTO = "#52514e";
  var REJILLA = "#e9ecef";

  function serie(etiqueta, valores, color, forma) {
    return {
      label: etiqueta,
      data: valores,
      borderColor: color,
      backgroundColor: color,
      borderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      pointStyle: forma,
      pointBorderColor: "#ffffff",
      pointBorderWidth: 2,
      tension: 0
    };
  }

  new Chart(lienzo, {
    type: "line",
    data: {
      labels: datos.etiquetas,
      datasets: [
        serie("Tasa de clics", datos.clics, AZUL, "circle"),
        serie("Tasa de reporte", datos.reportes, NARANJA, "triangle")
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          position: "top",
          align: "start",
          labels: { color: TEXTO, usePointStyle: true, boxWidth: 10 }
        },
        tooltip: {
          callbacks: {
            label: function (contexto) {
              return " " + contexto.dataset.label + ": " + contexto.parsed.y + " %";
            }
          }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          ticks: { color: TEXTO, callback: function (valor) { return valor + " %"; } },
          grid: { color: REJILLA },
          border: { display: false }
        },
        x: {
          ticks: { color: TEXTO, maxRotation: 0, autoSkip: true },
          grid: { display: false }
        }
      }
    }
  });
})();
