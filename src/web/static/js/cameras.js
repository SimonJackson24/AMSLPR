// Camera management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;

    // Discover cameras
    document.getElementById('discoverCameras').addEventListener('click', async function() {
        try {
            // Show loading spinner
            const resultsContainer = document.getElementById('discoveryResults');
            resultsContainer.innerHTML = `
                <div class="text-center py-4">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-3">Searching for cameras on your network...</p>
                </div>
            `;

            const response = await fetch('/cameras/discover', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({})
            });

            const data = await response.json();
            if (data.success) {
                // Clear spinner
                resultsContainer.innerHTML = '';

                // Add each discovered camera
                if (data.cameras.length === 0) {
                    resultsContainer.innerHTML = `
                        <div class="alert alert-info">
                            No cameras found on the network.
                        </div>
                    `;
                    return;
                }

                const accordion = document.createElement('div');
                accordion.className = 'accordion';
                accordion.id = 'cameraAccordion';

                data.cameras.forEach((camera, index) => {
                    const itemId = `camera-${index}`;
                    const cameraDiv = document.createElement('div');
                    cameraDiv.className = 'accordion-item';
                    cameraDiv.innerHTML = `
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#${itemId}">
                                <div>
                                    <strong>${camera.type}</strong>
                                    <span class="ms-3 text-muted">${camera.ip}${camera.port ? ':' + camera.port : ''}</span>
                                </div>
                            </button>
                        </h2>
                        <div id="${itemId}" class="accordion-collapse collapse" data-bs-parent="#cameraAccordion">
                            <div class="accordion-body">
                                <form class="add-camera-form" data-ip="${camera.ip}" data-port="${camera.port || '80'}">
                                    <div class="row">
                                        <div class="col-md-6">
                                            <div class="mb-3">
                                                <label class="form-label">Username</label>
                                                <input type="text" class="form-control" name="username" required>
                                            </div>
                                        </div>
                                        <div class="col-md-6">
                                            <div class="mb-3">
                                                <label class="form-label">Password</label>
                                                <input type="password" class="form-control" name="password" required>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="text-end">
                                        <button type="submit" class="btn btn-primary">
                                            <i class="bi bi-plus-circle me-2"></i>Add Camera
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    `;
                    accordion.appendChild(cameraDiv);

                    // Add form submit handler
                    const form = cameraDiv.querySelector('form');
                    form.addEventListener('submit', async function(e) {
                        e.preventDefault();
                        const submitBtn = this.querySelector('button[type="submit"]');
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Adding...';

                        const ip = this.dataset.ip;
                        const port = this.dataset.port;
                        const username = this.querySelector('input[name="username"]').value;
                        const password = this.querySelector('input[name="password"]').value;

                        try {
                            const response = await fetch('/cameras/add', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': csrfToken
                                },
                                body: JSON.stringify({
                                    ip: ip,
                                    port: port,
                                    username: username,
                                    password: password
                                })
                            });

                            const result = await response.json();
                            if (result.success) {
                                // Show success message
                                const successAlert = document.createElement('div');
                                successAlert.className = 'alert alert-success mt-3';
                                successAlert.innerHTML = `
                                    <i class="bi bi-check-circle me-2"></i>
                                    Camera added successfully! Reloading page...
                                `;
                                form.appendChild(successAlert);
                                
                                // Reload page after 2 seconds
                                setTimeout(() => window.location.reload(), 2000);
                            } else {
                                throw new Error(result.error);
                            }
                        } catch (error) {
                            console.error('Error:', error);
                            const errorAlert = document.createElement('div');
                            errorAlert.className = 'alert alert-danger mt-3';
                            errorAlert.innerHTML = `
                                <i class="bi bi-exclamation-triangle me-2"></i>
                                ${error.message || 'Error adding camera. Please try again.'}
                            `;
                            form.appendChild(errorAlert);
                            
                            // Re-enable submit button
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = '<i class="bi bi-plus-circle me-2"></i>Add Camera';
                        }
                    });
                });

                resultsContainer.appendChild(accordion);
            } else {
                throw new Error(data.error || 'Failed to discover cameras');
            }
        } catch (error) {
            console.error('Error:', error);
            const resultsContainer = document.getElementById('discoveryResults');
            resultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    ${error.message || 'Error discovering cameras. Please try again.'}
                </div>
            `;
        }
    });
});
