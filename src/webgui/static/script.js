import { fetchConfig, getApiBaseUrl, escapeHtml } from './api_config.js'; // Add this import

document.addEventListener('DOMContentLoaded', async function () {
    // Remove: let API_BASE_URL = ''; // Will be fetched dynamically

    // Remove: Function to fetch configuration
    // Remove: async function fetchConfig() { ... }

    // Fetch config first
    await fetchConfig(); // This now calls the imported fetchConfig

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
        fetch(`${getApiBaseUrl()}/api/dashboard/summary`) // Use getApiBaseUrl()
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (totalJobsElement) totalJobsElement.textContent = data.total_jobs;
                if (runningJobsElement) runningJobsElement.textContent = data.running_jobs;
                if (successfulRunsElement) successfulRunsElement.textContent = data.successful_runs;
                if (failedRunsElement) failedRunsElement.textContent = data.failed_runs;
            })
            .catch(error => {
                console.error('Error fetching dashboard summary:', error);
                // Display a static error message
                if (totalJobsElement) totalJobsElement.textContent = 'N/A';
                if (runningJobsElement) runningJobsElement.textContent = 'N/A';
                if (successfulRunsElement) successfulRunsElement.textContent = 'N/A';
                if (failedRunsElement) failedRunsElement.textContent = 'N/A';
            });
    }

    /**
     * Fetches and updates the job list table.
     */
    function updateJobList() {
        if (!jobListBody) return; // Do nothing if the table body isn't on the page

        fetch(`${getApiBaseUrl()}/api/unified-jobs`) // Use getApiBaseUrl()
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
                    switch (item.status) {
                        case 'enabled':
                            statusBadge = '<span class="badge bg-success">有効</span>';
                            break;
                        case 'disabled':
                            statusBadge = '<span class="badge bg-secondary">無効</span>';
                            break;
                        case 'paused':
                            statusBadge = '<span class="badge bg-warning">一時停止</span>';
                            break;
                        default:
                            statusBadge = `<span class="badge bg-dark">${escapeHtml(item.status)}</span>`;
                    }

                    const idForScheduler = escapeHtml(item.type === 'workflow' ? `workflow_${item.id}` : item.id);
                    const detailUrl = item.type === 'workflow' ? `/workflows/${encodeURIComponent(item.id)}` : `/jobs/${encodeURIComponent(item.id)}`;

                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td><a href="${detailUrl}">${escapeHtml(item.name)}</a></td>
                        <td>${escapeHtml(item.schedule)}</td>
                        <td>${nextRun}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <button class="btn btn-sm btn-primary btn-run" data-id="${idForScheduler}" title="Run Now">Run</button>
                            <button class="btn btn-sm btn-secondary btn-pause" data-id="${idForScheduler}" title="Pause" ${item.status === 'disabled' ? 'disabled' : ''}>Pause</button>
                            <button class="btn btn-sm btn-success btn-resume" data-id="${idForScheduler}" title="Resume" ${item.status === 'disabled' ? 'disabled' : ''}>Resume</button>
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
            fetch(`${getApiBaseUrl()}/scheduler/jobs/${schedulerId}/${action}`, { // Use getApiBaseUrl()
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

    // Ensure API_BASE_URL is set before making initial calls and setting up intervals
    (async () => {
        await fetchConfig(); // Ensure config is loaded before initial updates
        updateDashboard();
        updateJobList();

        // Set up periodic updates
        setInterval(() => {
            updateDashboard();
            updateJobList();
        }, 5000); // Update every 5 seconds
    })();

    // Add single event listener for all job actions
    if (jobListBody) {
        jobListBody.addEventListener('click', handleJobAction);
    }
});