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

        fetch(`${API_BASE_URL}/api/unified-jobs`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(items => {
                jobListBody.innerHTML = ''; // Clear existing rows
                items.forEach(item => {
                    const nextRun = item.next_run_time ? new Date(item.next_run_time).toLocaleString() : '-';
                    
                    let statusBadge;
                    if (!item.is_enabled || item.status === 'paused') {
                        statusBadge = '<span class="badge bg-secondary">Paused</span>';
                    } else {
                        statusBadge = '<span class="badge bg-success">Scheduled</span>';
                    }

                    const idForScheduler = item.type === 'workflow' ? `workflow_${item.id}` : item.id;
                    const detailUrl = item.type === 'workflow' ? `/workflows/${item.id}` : `/jobs/${item.id}`;

                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td><a href="${detailUrl}">${item.name}</a></td>
                        <td>${item.schedule}</td>
                        <td>${nextRun}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <button class="btn btn-sm btn-primary btn-run" data-id="${idForScheduler}" title="Run Now">Run</button>
                            <button class="btn btn-sm btn-secondary btn-pause" data-id="${idForScheduler}" title="Pause" ${!item.is_enabled ? 'disabled' : ''}>Pause</button>
                            <button class="btn btn-sm btn-success btn-resume" data-id="${idForScheduler}" title="Resume" ${!item.is_enabled ? 'disabled' : ''}>Resume</button>
                        </td>
                    `;
                    jobListBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching job list:', error);
                const row = document.createElement('tr');
                row.innerHTML = `<td colspan="5" class="text-center text-danger">Failed to load job list.</td>`;
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
        const schedulerId = target.dataset.id;
        if (!schedulerId) return;

        let action = '';
        if (target.classList.contains('btn-run')) {
            action = 'run';
        } else if (target.classList.contains('btn-pause')) {
            action = 'pause';
        } else if (target.classList.contains('btn-resume')) {
            action = 'resume';
        }

        if (action) {
            fetch(`${API_BASE_URL}/api/scheduler/jobs/${schedulerId}/${action}`, {
                method: 'POST'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Action failed! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log(`Action '${action}' for '${schedulerId}' successful:`, data.message);
                // Refresh the list to show the updated status
                setTimeout(() => {
                    updateJobList();
                    updateDashboard(); // Also refresh summary
                }, 500); // Add a small delay
            })
            .catch(error => {
                console.error(`Error performing action ${action} on job ${schedulerId}:`, error);
                alert(`Action failed for ${schedulerId}. See console for details.`);
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