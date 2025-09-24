// src/webgui/static/logs.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = 'http://127.0.0.1:8000';
    const logListBody = document.getElementById('log-list-body');

    /**
     * Fetches and updates the execution log table.
     */
    function updateLogList() {
        if (!logListBody) return;

        fetch(`${API_BASE_URL}/api/logs?limit=50`) // Fetch the last 50 logs
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(logs => {
                logListBody.innerHTML = ''; // Clear existing rows
                logs.forEach(log => {
                    const startTime = new Date(log.start_time).toLocaleString();
                    const endTime = log.end_time ? new Date(log.end_time).toLocaleString() : '-';
                    
                    let statusBadge;
                    switch (log.status) {
                        case 'COMPLETED':
                            statusBadge = '<span class="badge bg-success">Completed</span>';
                            break;
                        case 'FAILED':
                            statusBadge = '<span class="badge bg-danger">Failed</span>';
                            break;
                        case 'RUNNING':
                            statusBadge = '<span class="badge bg-info">Running</span>';
                            break;
                        default:
                            statusBadge = `<span class="badge bg-secondary">${log.status}</span>`;
                    }

                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${log.id.substring(0, 8)}...</td>
                        <td>${log.job_id}</td>
                        <td>${statusBadge}</td>
                        <td>${startTime}</td>
                        <td>${endTime}</td>
                        <td>${log.exit_code !== null ? log.exit_code : '-'}</td>
                    `;
                    logListBody.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Error fetching execution logs:', error);
                const row = document.createElement('tr');
                row.innerHTML = `<td colspan="6" class="text-center text-danger">Failed to load execution logs.</td>`;
                logListBody.innerHTML = '';
                logListBody.appendChild(row);
            });
    }

    // Initial load
    updateLogList();

    // Set up periodic updates
    setInterval(updateLogList, 7500); // Update every 7.5 seconds
});
