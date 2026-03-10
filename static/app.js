let currentTicker = null;
let chart = null;

const statusEl = document.getElementById("status");
const prepareForm = document.getElementById("prepare-form");
const queryInput = document.getElementById("query-input");
const candidateWrap = document.getElementById("candidate-wrap");
const tickerSelect = document.getElementById("ticker-select");
const confirmBtn = document.getElementById("confirm-btn");
const resultCard = document.getElementById("result-card");
const qaCard = document.getElementById("qa-card");
const companyMeta = document.getElementById("company-meta");
const kpiPrice = document.getElementById("kpi-price");
const kpiMonth = document.getElementById("kpi-month");
const kpiYear = document.getElementById("kpi-year");
const qaForm = document.getElementById("qa-form");
const questionInput = document.getElementById("question-input");
const qaAnswer = document.getElementById("qa-answer");
const qaSources = document.getElementById("qa-sources");

function setStatus(message) {
  statusEl.textContent = message;
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${Number(value).toFixed(2)}%`;
}

function formatPrice(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "N/A";
  }
  return `$${Number(value).toFixed(2)}`;
}

async function apiPost(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (!resp.ok || !data.ok) {
    const message = data?.error?.message || "Request failed.";
    throw new Error(message);
  }
  return data;
}

function renderCandidates(candidates) {
  tickerSelect.innerHTML = "";
  candidates.forEach((candidate) => {
    const option = document.createElement("option");
    option.value = candidate.ticker;
    option.textContent = `${candidate.ticker} - ${candidate.name} (${candidate.exchange}) [${candidate.score_hint || "candidate"}]`;
    tickerSelect.appendChild(option);
  });
  candidateWrap.classList.remove("hidden");
}

function renderChart(series) {
  const ctx = document.getElementById("price-chart");
  const labels = series.map((p) => p.date);
  const data = series.map((p) => p.close);

  if (chart) {
    chart.destroy();
  }

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Close Price",
          data,
          borderColor: "#00A4EF",
          backgroundColor: "rgba(0, 164, 239, 0.15)",
          tension: 0.25,
          pointRadius: 0,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label(context) {
              return `Close: $${Number(context.parsed.y).toFixed(2)}`;
            },
          },
        },
      },
      scales: {
        x: { display: false },
        y: {
          grid: {
            color: "rgba(115, 115, 115, 0.16)",
          },
          ticks: {
            callback(value) {
              return `$${value}`;
            },
          },
        },
      },
    },
  });
}

prepareForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setStatus("Searching for ticker candidates...");
  resultCard.classList.add("hidden");
  qaCard.classList.add("hidden");

  try {
    const query = queryInput.value.trim();
    const data = await apiPost("/api/prepare", { query });
    renderCandidates(data.candidates || []);
    setStatus("Select a candidate and click Proceed to confirm.");
  } catch (err) {
    setStatus(err.message);
  }
});

confirmBtn.addEventListener("click", async () => {
  const ticker = tickerSelect.value;
  if (!ticker) {
    setStatus("Please choose a ticker.");
    return;
  }

  setStatus(`Fetching stock details for ${ticker}...`);
  try {
    const data = await apiPost("/api/confirm", { ticker });
    currentTicker = ticker;

    companyMeta.textContent = `${data.company_name} (${data.ticker}) | Exchange: ${data.exchange} | Currency: ${data.currency}`;
    kpiPrice.textContent = formatPrice(data.current_price);
    kpiMonth.textContent = formatPercent(data.month_growth_pct);
    kpiYear.textContent = formatPercent(data.year_growth_pct);
    renderChart(data.series || []);

    resultCard.classList.remove("hidden");
    qaCard.classList.remove("hidden");
    setStatus("Snapshot loaded. You can now ask a question.");
  } catch (err) {
    setStatus(err.message);
  }
});

qaForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentTicker) {
    setStatus("Select and confirm a ticker first.");
    return;
  }

  const question = questionInput.value.trim();
  if (!question) {
    setStatus("Please type a question.");
    return;
  }

  setStatus("Getting grounded answer...");
  qaAnswer.textContent = "";
  qaSources.innerHTML = "";

  try {
    const data = await apiPost("/api/qa", { ticker: currentTicker, question });
    qaAnswer.textContent = data.answer || "No answer returned.";

    (data.sources || []).forEach((url) => {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = url;
      li.appendChild(a);
      qaSources.appendChild(li);
    });

    setStatus(`Answer generated via ${data.provider}.`);
  } catch (err) {
    setStatus(err.message);
  }
});
