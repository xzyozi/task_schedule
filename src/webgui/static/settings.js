import { fetchConfig, getApiBaseUrl } from './api_config.js'; // Add this import

document.addEventListener('DOMContentLoaded', async function() { 
    // Remove: const API_BASE_URL = 'http://127.0.0.1:8000'; // This will be relative to the current host, or can be set explicitly if needed.
    // const API_BASE_URL = "http://localhost:8000"; // Ensure this matches your backend API URL

    await fetchConfig(); // Fetch config first

    // --- Scheduler Control ---
    const pauseSchedulerBtn = document.getElementById('pauseScheduler');
    const schedulerStatusDiv = document.getElementById('schedulerStatus');

    if (pauseSchedulerBtn) {
        pauseSchedulerBtn.addEventListener('click', function() {
            fetch(`${getApiBaseUrl()}/api/scheduler/pause`, { // Use getApiBaseUrl()
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                schedulerStatusDiv.textContent = data.message || 'Scheduler paused.';
                schedulerStatusDiv.style.color = 'green';
            })
            .catch(error => {
                console.error('Error pausing scheduler:', error);
                schedulerStatusDiv.textContent = 'Error pausing scheduler.';
                schedulerStatusDiv.style.color = 'red';
            });
        });
    }

    // --- jobs.yaml Management ---
    const downloadJobsYamlBtn = document.getElementById('downloadJobsYaml');
    const jobsYamlStatusDiv = document.getElementById('jobsYamlStatus');

    if (downloadJobsYamlBtn) {
        downloadJobsYamlBtn.addEventListener('click', function() {
            fetch(`${getApiBaseUrl()}/api/jobs_yaml`) // Use getApiBaseUrl()
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json(); // Expecting JSON with a 'content' field
                })
                .then(data => {
                    const content = data.content;
                    const blob = new Blob([content], { type: 'text/yaml' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'jobs.yaml';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    jobsYamlStatusDiv.textContent = 'jobs.yaml downloaded successfully.';
                    jobsYamlStatusDiv.style.color = 'green';
                })
                .catch(error => {
                    console.error('Error downloading jobs.yaml:', error);
                    jobsYamlStatusDiv.textContent = 'Error downloading jobs.yaml.';
                    jobsYamlStatusDiv.style.color = 'red';
                });
        });
    }
});
