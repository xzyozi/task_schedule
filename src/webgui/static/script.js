// src/webgui/static/script.js

document.addEventListener('DOMContentLoaded', function() {
    const totalJobsElement = document.querySelector('.card.bg-primary .card-text');
    const runningJobsElement = document.querySelector('.card.bg-info .card-text');
    const successfulRunsElement = document.querySelector('.card.bg-success .card-text');
    const failedRunsElement = document.querySelector('.card.bg-danger .card-text');

    function updateDashboard() {
        fetch('http://127.0.0.1:8000/api/dashboard/summary')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                totalJobsElement.textContent = data.total_jobs;
                runningJobsElement.textContent = data.running_jobs;
                successfulRunsElement.textContent = data.successful_runs;
                failedRunsElement.textContent = data.failed_runs;
            })
            .catch(error => {
                console.error('Error fetching dashboard summary:', error);
                // Optionally, display an error message on the dashboard
            });
    }

    // Update the dashboard immediately on load
    updateDashboard();

    // Update the dashboard every 5 seconds
    setInterval(updateDashboard, 5000);
});
