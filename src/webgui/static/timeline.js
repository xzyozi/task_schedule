// src/webgui/static/timeline.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = ''; // This will be relative to the current host, or can be set explicitly if needed.

    // DOM element where the Timeline will be attached
    const container = document.getElementById('timeline');

    // Create a DataSet (allows adding / removing data easily)
    const items = new vis.DataSet();

    // Configuration for the Timeline
    const options = {
        // Configuration options for vis.js timeline
        // See: https://visjs.github.io/vis-timeline/docs/timeline/#Configuration_Options
        start: vis.moment().add(-1, 'day'), // Start 1 day ago
        end: vis.moment().add(3, 'day'),   // End 3 days from now
        editable: false,
        zoomMax: 1000 * 60 * 60 * 24 * 30 * 3, // 3 months
        zoomMin: 1000 * 60 * 10, // 10 minutes
        orientation: 'top', // Display items above the axis
        // Implement filtering, zooming, grouping as per gui.md
        // For now, basic setup.
    };

    // Create the Timeline
    const timeline = new vis.Timeline(container, items, options);

    // Function to fetch and render timeline data
    function fetchAndRenderTimelineData() {
        fetch(`${API_BASE_URL}/api/timeline-data`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                items.clear(); // Clear existing items
                // Process data and add to items DataSet
                // Example data structure for vis.js:
                // { id: 1, content: 'Job A', start: '2025-09-20T10:00:00', end: '2025-09-20T10:05:00', type: 'range', className: 'job-completed' }
                // { id: 2, content: 'Job B (Scheduled)', start: '2025-09-22T14:30:00', type: 'point', className: 'job-scheduled' }

                data.forEach(job => {
                    let className = '';
                    let content = job.id; // Default content

                    // Determine class name based on job status/type
                    if (job.status === 'completed') {
                        className = 'job-completed';
                    } else if (job.status === 'failed') {
                        className = 'job-failed';
                    } else if (job.status === 'running') {
                        className = 'job-running';
                        content += ' (Running)';
                    } else if (job.status === 'scheduled') {
                        className = 'job-scheduled';
                        content += ' (Scheduled)';
                    }

                    // Add item to DataSet
                    items.add({
                        id: job.id + '-' + job.start, // Unique ID for each item
                        content: content,
                        start: job.start,
                        end: job.end, // Optional, for range items
                        type: job.end ? 'range' : 'point', // 'range' for completed/failed, 'point' for scheduled/running
                        className: className,
                        title: `Job ID: ${job.id}<br>Status: ${job.status}<br>Function: ${job.func}<br>Start: ${new Date(job.start).toLocaleString()}` + (job.end ? `<br>End: ${new Date(job.end).toLocaleString()}` : '')
                    });
                });

                timeline.fit(); // Adjust timeline to fit all items
            })
            .catch(error => {
                console.error('Error fetching timeline data:', error);
                // Display an error message on the timeline container
                container.innerHTML = '<p class="text-danger">タイムラインデータの読み込みに失敗しました。</p>';
            });
    }

    // Initial fetch and render
    fetchAndRenderTimelineData();

    // Optional: Refresh data periodically
    // setInterval(fetchAndRenderTimelineData, 60000); // Refresh every minute
});
