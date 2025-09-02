document.addEventListener('DOMContentLoaded', function() {
    // Helper: safe JSON parse with fallback
    function safeParse(raw) {
        if (!raw) return [];
        const trimmed = raw.trim();
        // Guard against incomplete brackets like '[' or '[' whitespace
        if (trimmed === '[' || trimmed === ']' ) return [];
        try { return JSON.parse(trimmed); } catch(e) { console.warn('Invalid JSON dataset', raw, e); return []; }
    }

    const charts = {}; // collect chart instances to announce later

    // ===== Chart 1: Maintenance Cost (Bar) =====
    const costScript = document.getElementById('costChartData');
    if (costScript) {
        const parsed = safeParse(costScript.textContent);
        const costLabels = parsed.labels || [];
        const costValues = parsed.values || [];
        const costCtx = document.getElementById('costChart');
        const emptyEl = document.getElementById('costEmpty');
        if (costCtx && costLabels.length && costValues.length) {
            charts.cost = new Chart(costCtx, {
                type: 'bar',
                data: {
                    labels: costLabels,
                    datasets: [{
                        label: 'ค่าใช้จ่ายรวม (บาท)',
                        data: costValues,
                        backgroundColor: costValues.map(()=> 'rgba(54, 162, 235, 0.6)'),
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '฿' + (value || 0).toLocaleString();
                                }
                            }
                        }
                    }
                }
            });
            if (emptyEl) emptyEl.hidden = true;
        } else if (emptyEl) { emptyEl.hidden = false; costCtx?.setAttribute('hidden','true'); }
    }

    // ===== Chart 2: Job Type Distribution (Pie) =====
    const jobTypeScript = document.getElementById('jobTypeChartData');
    if (jobTypeScript) {
        const parsedJT = safeParse(jobTypeScript.textContent);
        const jobTypeLabels = parsedJT.labels || [];
        const jobTypeValues = parsedJT.values || [];
        const jobTypeCtx = document.getElementById('jobTypeChart');
        const emptyJT = document.getElementById('jobTypeEmpty');
        if (jobTypeCtx && jobTypeLabels.length && jobTypeValues.length) {
            const palette = [
                'rgba(255, 99, 132, 0.7)',
                'rgba(54, 162, 235, 0.7)',
                'rgba(255, 206, 86, 0.7)',
                'rgba(75, 192, 192, 0.7)',
                'rgba(153, 102, 255, 0.7)',
                'rgba(255, 159, 64, 0.7)'
            ];
            charts.jobType = new Chart(jobTypeCtx, {
                type: 'pie',
                data: {
                    labels: jobTypeLabels,
                    datasets: [{
                        label: 'จำนวนงาน',
                        data: jobTypeValues,
                        backgroundColor: jobTypeValues.map((_,i)=> palette[i % palette.length]),
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
            if (emptyJT) emptyJT.hidden = true;
        } else if (emptyJT) { emptyJT.hidden = false; jobTypeCtx?.setAttribute('hidden','true'); }
    }

    // Dispatch custom event for legend builder if at least one chart created
    if (Object.keys(charts).length) {
        document.dispatchEvent(new CustomEvent('charts:ready', { detail: { charts } }));
    }
});