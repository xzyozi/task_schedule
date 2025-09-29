document.addEventListener('DOMContentLoaded', function() {
    const API_BASE_URL = 'http://127.0.0.1:8000';
    const workflowId = document.getElementById('workflow-id-hidden').value;

    function fetchWorkflowDetails() {
        fetch(`${API_BASE_URL}/api/workflows/${workflowId}`)
            .then(response => response.json())
            .then(workflow => {
                document.getElementById('workflow-name').textContent = workflow.name;
                document.getElementById('workflow-description').textContent = workflow.description || '';
                document.getElementById('workflow-schedule').textContent = workflow.schedule || 'N/A';
                document.getElementById('workflow-status').innerHTML = `<span class="badge bg-${workflow.is_enabled ? 'success' : 'secondary'}">${workflow.is_enabled ? '有効' : '無効'}</span>`;

                const stepsBody = document.getElementById('workflow-steps-body');
                stepsBody.innerHTML = '';
                workflow.steps.sort((a, b) => a.step_order - b.step_order).forEach(step => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${step.step_order}</td>
                        <td>${step.name}</td>
                        <td><span class="badge bg-info">${step.job_type}</span></td>
                        <td><code>${step.target}</code></td>
                    `;
                    stepsBody.appendChild(row);
                });
            })
            .catch(error => console.error('Error fetching workflow details:', error));
    }

    // TODO: Implement fetchWorkflowRuns() to get execution history

    fetchWorkflowDetails();
});
