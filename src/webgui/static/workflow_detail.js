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

                const runsBody = document.getElementById('workflow-runs-body');
                runsBody.innerHTML = '';
                workflow.runs.sort((a, b) => new Date(b.start_time) - new Date(a.start_time)).forEach(run => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${run.id}</td>
                        <td><span class="badge bg-${run.status === 'COMPLETED' ? 'success' : run.status === 'FAILED' ? 'danger' : 'warning'}">${run.status}</span></td>
                        <td>${new Date(run.start_time).toLocaleString()}</td>
                        <td>${run.end_time ? new Date(run.end_time).toLocaleString() : 'N/A'}</td>
                        <td><button class="btn btn-sm btn-primary btn-view-run-logs" data-run-id="${run.id}">ログ表示</button></td>
                    `;
                    runsBody.appendChild(row);
                });

                // Log Viewer Modal elements
                const logViewerModal = new bootstrap.Modal(document.getElementById('logViewerModal'));
                const logContentPre = document.getElementById('log-content');

                // Event listener for "ログ表示" buttons
                document.getElementById('workflow-runs-body').addEventListener('click', function(event) {
                    if (event.target.classList.contains('btn-view-run-logs')) {
                        const runId = event.target.dataset.runId;
                        fetch(`${API_BASE_URL}/api/workflow-runs/${runId}/logs`) // 新しいAPIエンドポイントを想定
                            .then(response => response.json())
                            .then(logs => {
                                logContentPre.textContent = logs.map(log => {
                                    const statusBadge = log.status === 'COMPLETED' ? '✅' : log.status === 'FAILED' ? '❌' : '⏳';
                                    return `${statusBadge} [${new Date(log.start_time).toLocaleString()}] ${log.command}\nSTDOUT:\n${log.stdout || '(なし)'}\nSTDERR:\n${log.stderr || '(なし)'}\n---`;
                                }).join('\n\n');
                                logViewerModal.show();
                            })
                            .catch(error => {
                                console.error('Error fetching run logs:', error);
                                alert('実行ログの取得に失敗しました。');
                            });
                    }
                });

            })
            .catch(error => console.error('Error fetching workflow details:', error));
    }

    // TODO: Implement fetchWorkflowRuns() to get execution history

    fetchWorkflowDetails();
});
