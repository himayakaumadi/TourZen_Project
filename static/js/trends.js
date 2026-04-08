// -------------------------------
// Color Palette for Modern Charts
// -------------------------------
const modernPalette = [
    "#10B981", "#34D399", "#059669", "#6EE7B7", 
    "#047857", "#A7F3D0", "#065F46", "#D1FAE5", 
    "#3B82F6", "#60A5FA"
];

// -------------------------------
// Global Modern Layout Settings
// -------------------------------
function getBaseLayout() {
    return {
        font: { family: "'Outfit', sans-serif", color: "#596E67" },
        plot_bgcolor: "rgba(0,0,0,0)",
        paper_bgcolor: "rgba(0,0,0,0)",
        margin: { t: 40, r: 40, b: 40, l: 40 },
        autosize: true,
        xaxis: { 
            gridcolor: "#F1F5F9", 
            zerolinecolor: "#E2E8F0",
            tickfont: { color: "#94A3B8" }
        },
        yaxis: { 
            gridcolor: "#F1F5F9", 
            zerolinecolor: "#E2E8F0",
            tickfont: { color: "#94A3B8" }
        },
        hoverlabel: {
            bgcolor: "#113229",
            font: { family: "'Outfit', sans-serif", color: "#ffffff" },
            bordercolor: "transparent"
        }
    };
}

// -------------------------------
// Elements
// -------------------------------
const yearSelect = document.getElementById("yearSelect");
const loading = document.getElementById("loading");

// -------------------------------
// Loader Helper
// -------------------------------
function setLoading(isLoading) {
    loading.classList.toggle("d-none", !isLoading);
}

// -------------------------------
// Generate Region/Age/Month Table (2 columns)
// -------------------------------
function generateTable(obj, col1Name, col2Name) {
    let html = `
        <table class="table table-borderless table-hover" style="border-radius:12px; overflow:hidden;">
            <thead style="background-color: var(--bg-color); color: var(--dark-text);">
                <tr>
                    <th class="text-start px-4 py-3" style="width: 50%">${col1Name}</th>
                    <th class="text-end px-4 py-3" style="width: 50%">${col2Name}</th>
                </tr>
            </thead>
            <tbody>
    `;

    for (let key in obj) {
        html += `
            <tr style="border-bottom: 1px solid #F1F5F9;">
                <td class="text-start px-4 text-muted" style="font-weight: 500;">${key}</td>
                <td class="text-end px-4 font-weight-bold" style="color: var(--dark-text);">${Math.round(Number(obj[key])).toLocaleString()}</td>
            </tr>
        `;
    }

    html += "</tbody></table>";
    return html;
}

// -------------------------------
// Generate Income Table (5 columns)
// -------------------------------
function generateIncomeTable(dataList) {
    let html = `
        <table class="table table-borderless table-hover" style="border-radius:12px; overflow:hidden; font-size:0.95rem;">
            <thead style="background-color: var(--bg-color); color: var(--dark-text);">
                <tr>
                    <th class="px-3 py-3">Month</th>
                    <th class="text-end px-3 py-3">Arrivals</th>
                    <th class="text-end px-3 py-3">Avg Value (USD)</th>
                    <th class="text-end px-3 py-3">Avg Duration</th>
                    <th class="text-end px-3 py-3">Income (USD Mn)</th>
                </tr>
            </thead>
            <tbody>
    `;

    dataList.forEach(row => {
        html += `
            <tr style="border-bottom: 1px solid #F1F5F9;">
                <td class="px-3 text-muted" style="font-weight: 500;">${row["Month"]}</td>
                <td class="text-end px-3">${Math.round(row["Number of tourist arrivals"]).toLocaleString()}</td>
                <td class="text-end px-3">${row["Average value of the Month"].toFixed(2)}</td>
                <td class="text-end px-3">${row["Average duration of the Month"].toFixed(2)}</td>
                <td class="text-end px-3" style="color: var(--primary-green); font-weight:700;">${Math.round(row["Total value (USD Mn)"]).toLocaleString()}</td>
            </tr>
        `;
    });

    html += "</tbody></table>";
    return html;
}

// -------------------------------
// Ordering Helpers
// -------------------------------
function sortMonthsArr(list) {
    const order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    return list.sort((a, b) => order.indexOf(a.Month) - order.indexOf(b.Month));
}

function sortMonthsObj(data) {
    const order = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ];

    const sorted = {};
    order.forEach(m => {
        if (data[m] !== undefined) sorted[m] = data[m];
    });
    return sorted;
}

function orderAgeCategories(data) {
    const order = [
        "60+", "51-60", "41-50", "31-40", "20-30", "Below 20"
    ];

    const sorted = {};
    order.forEach(a => {
        if (data[a] !== undefined) sorted[a] = data[a];
    });
    return sorted;
}

// -------------------------------
// 5. PDF GENERATION LOGIC
// -------------------------------
let currentPredictionData = null;

// -------------------------------
// Call API on Year Change
// -------------------------------
yearSelect.addEventListener("change", function () {
    let year = this.value;
    if (!year) return;

    setLoading(true);

    fetch("/predict_trends", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year })
    })
    .then(res => res.json())
    .then(data => {
        currentPredictionData = data; // Store data for report generation
        loadRegion(data.region);
        loadAge(data.age);
        loadMonth(data.month);
        loadIncome(data.income);
        
        // Show the results container and the download button
        document.getElementById("trendsResults").classList.remove("d-none");
        const downloadBtn = document.getElementById("downloadPdfBtn");
        if (downloadBtn) downloadBtn.classList.remove("d-none");
    })
    .catch(err => {
        console.error("Prediction Error:", err);
        alert("Error loading predictions: " + err.message);
    })
    .finally(() => setLoading(false));
});

// -------------------------------
// 1. REGION SECTION
// -------------------------------
function loadRegion(regionData) {
    document.getElementById("regionTable").innerHTML = generateTable(regionData, "Region", "No. of Arrivals");

    const layout = Object.assign(getBaseLayout(), {
        margin: { t: 40, r: 40, b: 40, l: 40 },
        showlegend: true,
        legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.2 }
    });

    Plotly.newPlot("regionChart", [{
        labels: Object.keys(regionData),
        values: Object.values(regionData),
        type: "pie",
        hole: 0.6,
        textposition: "inside",
        textinfo: "percent",
        marker: { colors: modernPalette },
        hoverinfo: "label+value"
    }], layout, { responsive: true });
}

// -------------------------------
// 2. AGE SECTION
// -------------------------------
function loadAge(ageData) {
    const ordered = orderAgeCategories(ageData);

    document.getElementById("ageTable").innerHTML = generateTable(ordered, "Age Category", "No. of Arrivals");

    const layout = Object.assign(getBaseLayout(), {
        height: 350,
        margin: { t: 20, r: 20, b: 40, l: 80 }
    });

    Plotly.newPlot("ageChart", [{
        x: Object.values(ordered),
        y: Object.keys(ordered),
        type: "bar",
        orientation: "h",
        marker: {
            color: "#10B981",
            opacity: 0.85,
            line: { color: "transparent", width: 0 }
        }
    }], layout, { responsive: true });
}

// -------------------------------
// 3. MONTH SECTION
// -------------------------------
function loadMonth(monthData) {
    const sorted = sortMonthsObj(monthData);

    document.getElementById("monthTable").innerHTML = generateTable(sorted, "Month", "No. of Arrivals");

    const layout = Object.assign(getBaseLayout(), {
        height: 350,
        margin: { t: 20, r: 20, b: 50, l: 60 }
    });

    Plotly.newPlot("monthChart", [{
        x: Object.keys(sorted),
        y: Object.values(sorted),
        type: "bar",
        marker: {
            color: "#34D399",
            opacity: 0.9,
            line: { color: "transparent" }
        }
    }], layout, { responsive: true });
}

// -------------------------------
// 4. INCOME SECTION
// -------------------------------
function loadIncome(incomeData) {

    const sortedList = sortMonthsArr(incomeData);

    document.getElementById("incomeTable").innerHTML = generateIncomeTable(sortedList);

    const months = sortedList.map(x => x.Month.substring(0,3));
    const values = sortedList.map(x => x["Total value (USD Mn)"]);

    const layout = Object.assign(getBaseLayout(), {
        height: 350,
        margin: { t: 20, r: 20, b: 40, l: 60 }
    });

    Plotly.newPlot("incomeChart", [{
        x: months,
        y: values,
        type: "scatter",
        mode: "lines+markers",
        line: { width: 3, color: "#10B981", shape: "spline" }, // Spline curve for smooth lines
        fill: "tozeroy",
        fillcolor: "rgba(16, 185, 129, 0.15)", // Premium semi-transparent mint fill
        marker: { size: 6, color: "#059669" }
    }], layout, { responsive: true });
}
// -------------------------------
// 5. PDF GENERATION LOGIC
// -------------------------------
async function generateProfessionalReport() {
    const year = document.getElementById("yearSelect").value;
    const btn = document.getElementById("downloadPdfBtn");
    const originalBtnText = btn.innerHTML;

    if (!year) {
        alert("Please select a year first.");
        return;
    }

    if (!currentPredictionData) {
        alert("Please load trends for a specific year first.");
        return;
    }

    // UI Feedback: Show that processing is happening on the server
    btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Building Your Report...`;
    btn.disabled = true;

    try {
        // Send the pre-calculated data to the server via POST
        const response = await fetch(`/download_report/${year}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentPredictionData)
        });

        if (!response.ok) throw new Error("Failed to generate report");

        // Handle binary PDF blob
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `TourZen_Full_Report_${year}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

    } catch (err) {
        console.error("Report Generation Error:", err);
        alert("Error generating report: " + err.message);
    } finally {
        btn.innerHTML = originalBtnText;
        btn.disabled = false;
    }
}
