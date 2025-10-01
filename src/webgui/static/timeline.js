// src/webgui/static/timeline.js

document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = 'http://127.0.0.1:8000'; // This will be relative to the current host, or can be set explicitly if needed.

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
        fetch(`${API_BASE_URL}/api/timeline-items`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                const groups = new vis.DataSet();
                const uniqueGroupIds = [...new Set(data.map(item => item.group).filter(g => g))];
                
                uniqueGroupIds.forEach(groupId => {
                    const representativeItem = data.find(item => item.group === groupId);
                    let groupContent = groupId;
                    if (representativeItem) {
                        if (groupId.startsWith('workflow_')) {
                            const wfName = representativeItem.content.split('.')[0];
                            groupContent = `WF: ${wfName}`;
                        } else {
                            groupContent = `Job: ${groupId}`;
                        }
                    }
                    groups.add({ id: groupId, content: groupContent });
                });

                timeline.setGroups(groups);

                items.clear();
                items.add(
                    data.map(item => ({
                        id: item.id,
                        content: item.content,
                        start: item.start,
                        end: item.end,
                        group: item.group,
                        className: `job-${item.status}`,
                        type: item.end ? 'range' : 'point',
                        title: `<b>${item.content}</b><br>Status: ${item.status}<br>Start: ${new Date(item.start).toLocaleString()}` + (item.end ? `<br>End: ${new Date(item.end).toLocaleString()}` : '')
                    }))
                );

                timeline.fit(); // Adjust timeline to fit all items
            })
            .catch(error => {
                console.error('Error fetching timeline data:', error);
                container.innerHTML = '<p class="text-danger">タイムラインデータの読み込みに失敗しました。</p>';
            });
    }

    // Initial fetch and render
    fetchAndRenderTimelineData();

    // Optional: Refresh data periodically
    // setInterval(fetchAndRenderTimelineData, 60000); // Refresh every minute
});
