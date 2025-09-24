// src/webgui/static/script.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = 'http://127.0.0.1:8000';

    // --- Dashboard Summary Elements ---
    const totalJobsElement = document.querySelector('.card.bg-primary .card-text');
    const runningJobsElement = document.querySelector('.card.bg-info .card-text');
    const successfulRunsElement = document.querySelector('.card.bg-success .card-text');
    const failedRunsElement = document.querySelector('.card.bg-danger .card-text');

    // --- Job List Elements ---
    const jobListBody = document.getElementById('job-list-body');

    /**
     * Fetches and updates the dashboard summary cards.
     */
    function updateDashboard() {
        fetch(`${API_BASE_URL}/api/dashboard/summary`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if(totalJobsElement) totalJobsElement.textContent = data.total_jobs;
                if(runningJobsElement) runningJobsElement.textContent = data.running_jobs;
                if(successfulRunsElement) successfulRunsElement.textContent = data.successful_runs;
                if(failedRunsElement) failedRunsElement.textContent = data.failed_runs;
            })
            .catch(error => {
                console.error('Error fetching dashboard summary:', error);
                // Display a static error message
                if(totalJobsElement) totalJobsElement.textContent = 'N/A';
                if(runningJobsElement) runningJobsElement.textContent = 'N/A';
                if(successfulRunsElement) successfulRunsElement.textContent = 'N/A';
                if(failedRunsElement) failedRunsElement.textContent = 'N/A';
            });
    }

    /**
     * Fetches and updates the job list table.
     */
    function updateJobList() {
        if (!jobListBody) return; // Do nothing if the table body isn't on the page

        fetch(`${API_BASE_URL}/api/scheduler/jobs`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(jobs => {
                jobListBody.innerHTML = ''; // Clear existing rows
                jobs.forEach(job => {
                    const nextRun = job.next_run_time ? new Date(job.next_run_time).toLocaleString() : 'Paused';
                    const status = job.next_run_time ? '<span class="badge bg-success">Scheduled</span>' : '<span class="badge bg-warning">Paused</span>';

                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${job.id}</td>
                        <td>${nextRun}</td>
                        <td>${status}</td>
                        <td>
                            <button class="btn btn-sm btn-primary btn-run" data-job-id="${job.id}" title="Run Now">Run</button>
                            <button class="btn btn-sm btn-secondary btn-pause" data-job-id="${job.id}" title="Pause">Pause</button>
                            <button class="btn btn-sm btn-success btn-resume" data-job-id="${job.id}" title="Resume">Resume</button>
                        </td>
                    `;
                    jobListBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching job list:', error);
                const row = document.createElement('tr');
                row.innerHTML = `<td colspan="4" class="text-center text-danger">Failed to load job list.</td>`;
                jobListBody.innerHTML = '';
                jobListBody.appendChild(row);
            });
    }

    /**
     * Handles clicks on the action buttons in the job list.
     * @param {Event} event The click event.
     */
    function handleJobAction(event) {
        const target = event.target;
        const jobId = target.dataset.jobId;
        if (!jobId) return;

        let action = '';
        if (target.classList.contains('btn-run')) {
            action = 'run';
        } else if (target.classList.contains('btn-pause')) {
            action = 'pause';
        } else if (target.classList.contains('btn-resume')) {
            action = 'resume';
        }

        if (action) {
            fetch(`${API_BASE_URL}/api/scheduler/jobs/${jobId}/${action}`, {
                method: 'POST'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Action failed! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(`Job ${jobId} action ${action} successful:`, data.message);
                // Refresh the list to show the updated status
                updateJobList();
                updateDashboard(); // Also refresh summary
            })
            .catch(error => {
                console.error(`Error performing action ${action} on job ${jobId}:`, error);
                // Optionally, show an alert to the user
                alert(`Action failed for job ${jobId}. See console for details.`);
            });
        }
    }

    // --- Initial Load and Interval Updates ---

    // Update everything immediately on load
    updateDashboard();
    updateJobList();

    // Set up periodic updates
    setInterval(() => {
        updateDashboard();
        updateJobList();
    }, 5000); // Update every 5 seconds

    // Add single event listener for all job actions
    if (jobListBody) {
        jobListBody.addEventListener('click', handleJobAction);
    }
});