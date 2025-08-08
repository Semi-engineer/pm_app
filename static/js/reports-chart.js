document.addEventListener('DOMContentLoaded', function() {

    // ========== กราฟที่ 1: กราฟค่าใช้จ่าย (Bar Chart) ==========

    // 1. ดึง Element ที่เก็บข้อมูล
    const costDataElement = document.getElementById('costChartDataContainer');
    
    // 2. อ่านและแปลงข้อมูลจาก data-* attributes (จาก String เป็น JSON/Array)
    const costLabels = JSON.parse(costDataElement.dataset.labels);
    const costValues = JSON.parse(costDataElement.dataset.values);

    // 3. ดึง Canvas และสร้างกราฟ
    const costCtx = document.getElementById('costChart');
    if (costCtx) {
        new Chart(costCtx, {
            type: 'bar',
            data: {
                labels: costLabels,
                datasets: [{
                    label: 'ค่าใช้จ่ายรวม (บาท)',
                    data: costValues,
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
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
                            callback: function(value, index, values) {
                                return '฿' + value.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }


    // ========== กราฟที่ 2: กราฟประเภทงาน (Pie Chart) ==========

    // 1. ดึง Element ที่เก็บข้อมูล
    const jobTypeDataElement = document.getElementById('jobTypeChartDataContainer');

    // 2. อ่านและแปลงข้อมูล
    const jobTypeLabels = JSON.parse(jobTypeDataElement.dataset.labels);
    const jobTypeValues = JSON.parse(jobTypeDataElement.dataset.values);
    
    // 3. ดึง Canvas และสร้างกราฟ
    const jobTypeCtx = document.getElementById('jobTypeChart');
    if (jobTypeCtx) {
        new Chart(jobTypeCtx, {
            type: 'pie',
            data: {
                labels: jobTypeLabels,
                datasets: [{
                    label: 'จำนวนงาน',
                    data: jobTypeValues,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(153, 102, 255, 0.7)',
                        'rgba(255, 159, 64, 0.7)'
                    ],
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
            }
        });
    }

});