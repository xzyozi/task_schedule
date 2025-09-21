document.addEventListener('DOMContentLoaded', function() {
    // Populate Summary Cards
    document.getElementById('total-jobs').innerText = summaryData.total_jobs;
    document.getElementById('running-jobs').innerText = summaryData.running_jobs;
    document.getElementById('successful-runs').innerText = summaryData.successful_runs;
    document.getElementById('failed-runs').innerText = summaryData.failed_runs;

    const timelineElement = document.getElementById('job-timeline');
    const filterStatusSelect = document.getElementById('timeline-filter-status');
    const filterJobIdInput = document.getElementById('timeline-filter-job-id');
    const applyFiltersButton = document.getElementById('apply-timeline-filters');
    const zoomLevelSelect = document.getElementById('timeline-zoom-level');

    // Create a DataSet for items and groups
    const items = new vis.DataSet();
    const groups = new vis.DataSet();

    // Map backend timelineData to vis.js items
    // Each event will be a vis.js item
    // We'll use groups to achieve the alternating top/bottom display
    // For simplicity, let's create two groups: 'top' and 'bottom'
    groups.add([
        {id: 'top', content: 'Top Lane'},
        {id: 'bottom', content: 'Bottom Lane'}
    ]);

    console.log("Raw timelineData:", timelineData);
    let itemCounter = 0;
    timelineData.forEach(event => {
        const group = (itemCounter % 2 === 0) ? 'top' : 'bottom'; // Alternate groups for visual separation
        itemCounter++;

        const startDate = new Date(event.timestamp);
        if (isNaN(startDate.getTime())) {
            console.error("Invalid timestamp for event:", event);
            return; // Skip this event if timestamp is invalid
        }

        let className = '';
        switch (event.status) {
            case 'upcoming':
                className = 'timeline-item-upcoming';
                break;
            case 'completed':
                className = 'timeline-item-completed';
                break;
            case 'failed':
                className = 'timeline-item-failed';
                break;
            case 'running':
                className = 'timeline-item-running';
                break;
            default:
                className = 'timeline-item-unknown';
        }

        items.add({
            id: event.job_id + '-' + event.timestamp, // Unique ID for each item
            group: group,
            start: new Date(event.timestamp),
            content: `
                <div class="timeline-content-wrapper">
                    <div class="timeline-title">${event.job_id}</div>
                    <div class="timeline-time">${new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                    <span class="badge bg-${className.split('-')[2]}">${event.status}</span>
                    <div class="timeline-description">${event.description || event.func}</div>
                </div>
            `,
            className: className,
            // Store original event data for filtering
            originalEvent: event 
        });
    });

    // Configuration for the Timeline
    const options = {
        orientation: { axis: 'both', item: 'top' }, // Display axis on both sides, items on top
        zoomMin: 1000 * 60 * 30, // 30 minutes
        zoomMax: 1000 * 60 * 60 * 24 * 30, // 30 days
        start: new Date(new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString()), // Start 24 hours ago (UTC)
        end: new Date(new Date(Date.now() + 1000 * 60 * 60 * 24 * 2).toISOString()), // End 2 days from now (UTC)
        showCurrentTime: true,
        stack: true, // Stack items to prevent overlap
        margin: {
            item: {
                horizontal: 10,
                vertical: 10
            }
        },
        height: '400px',
        editable: false,
        moveable: true,
        zoomable: true,
        // Grouping options (for clustering)
        groupOrder: function (a, b) {
            return a.id - b.id;
        },
        groupTemplate: function(group) {
            return `<div class="vis-group-label">${group.content}</div>`;
        },
        // New clustering options
        cluster: {
            maxItems: 5, // Cluster if more than 5 items overlap
            clusterCriteria: function (itemA, itemB) {
                // Cluster items if their start times are within 30 minutes of each other
                const timeDiff = Math.abs(new Date(itemA.start).getTime() - new Date(itemB.start).getTime());
                return timeDiff < (1000 * 60 * 30); // 30 minutes
            }
        }
    };

    // Create the Timeline
    if (timelineData.length === 0) {
        console.warn("timelineData is empty. Timeline will not display any events.");
    }
    console.log("Timeline options:", options);
    const timeline = new vis.Timeline(timelineElement, items, groups, options);

    // Function to filter timeline items
    function filterTimelineItems() {
        const statusFilter = filterStatusSelect.value;
        const jobIdFilter = filterJobIdInput.value.toLowerCase();

        const filteredItems = timelineData.filter(event => {
            const matchesStatus = statusFilter === 'all' || event.status === statusFilter;
            const matchesJobId = jobIdFilter === '' || 
                                 event.job_id.toLowerCase().includes(jobIdFilter) ||
                                 (event.description && event.description.toLowerCase().includes(jobIdFilter)) ||
                                 (event.func && event.func.toLowerCase().includes(jobIdFilter));
            return matchesStatus && matchesJobId;
        });

        // Clear existing items and add filtered ones
        items.clear();
        let filteredItemCounter = 0;
        filteredItems.forEach(event => {
            const group = (filteredItemCounter % 2 === 0) ? 'top' : 'bottom';
            filteredItemCounter++;

            let className = '';
            switch (event.status) {
                case 'upcoming':
                    className = 'timeline-item-upcoming';
                    break;
                case 'completed':
                    className = 'timeline-item-completed';
                    break;
                case 'failed':
                    className = 'timeline-item-failed';
                    break;
                case 'running':
                    className = 'timeline-item-running';
                    break;
                default:
                    className = 'timeline-item-unknown';
            }

            items.add({
                id: event.job_id + '-' + event.timestamp,
                group: group,
                start: new Date(event.timestamp),
                content: `
                    <div class="timeline-content-wrapper">
                        <div class="timeline-title">${event.job_id}</div>
                        <div class="timeline-time">${new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                        <span class="badge bg-${className.split('-')[2]}">${event.status}</span>
                        <div class="timeline-description">${event.description || event.func}</div>
                    </div>
                `,
                className: className,
                originalEvent: event
            });
        });
    }

    // Event Listener for zoom select
    zoomLevelSelect.addEventListener('change', function() {
        const zoomLevel = zoomLevelSelect.value;
        let newStart, newEnd;
        const now = new Date();

        switch (zoomLevel) {
            case 'day':
                newStart = new Date(new Date(now.getTime() - 1000 * 60 * 60 * 12).toISOString()); // 12 hours before now (UTC)
                newEnd = new Date(new Date(now.getTime() + 1000 * 60 * 60 * 36).toISOString()); // 36 hours after now (total 2 days) (UTC)
                break;
            case 'hour':
                newStart = new Date(new Date(now.getTime() - 1000 * 60 * 30).toISOString()); // 30 minutes before now (UTC)
                newEnd = new Date(new Date(now.getTime() + 1000 * 60 * 90).toISOString()); // 90 minutes after now (total 2 hours) (UTC)
                break;
            case 'minute':
                newStart = new Date(new Date(now.getTime() - 1000 * 60 * 5).toISOString()); // 5 minutes before now (UTC)
                newEnd = new Date(new Date(now.getTime() + 1000 * 60 * 15).toISOString()); // 15 minutes after now (total 20 minutes) (UTC)
                break;
            default: // Default to a wider view
                newStart = new Date(new Date(now.getTime() - 1000 * 60 * 60 * 24).toISOString()); // 24 hours before now (UTC)
                newEnd = new Date(new Date(now.getTime() + 1000 * 60 * 60 * 24 * 2).toISOString()); // 2 days after now (UTC)
                break;
        }
        timeline.setWindow(newStart, newEnd);
    });

    // Event Listeners for filters
    applyFiltersButton.addEventListener('click', filterTimelineItems);
    filterStatusSelect.addEventListener('change', filterTimelineItems);
    filterJobIdInput.addEventListener('keyup', function(event) {
        if (event.key === 'Enter') {
            filterTimelineItems();
        }
    });

    // Initial filter and zoom application
    filterTimelineItems(); // Apply initial filters
    zoomLevelSelect.value = 'day'; // Set initial zoom level to 'day'
    zoomLevelSelect.dispatchEvent(new Event('change')); // Trigger change event to apply zoom
});