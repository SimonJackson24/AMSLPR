// Camera management JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;

    // Discover cameras
    document.getElementById('discoverCameras').addEventListener('click', async function() {
        try {
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
                // Clear existing results
                const resultsContainer = document.getElementById('discoveryResults');
                resultsContainer.innerHTML = '';

                // Add each discovered camera
                data.cameras.forEach(camera => {
                    const cameraDiv = document.createElement('div');
                    cameraDiv.className = 'card mb-3';
                    cameraDiv.innerHTML = `
                        <div class="card-body">
                            <h5 class="card-title">${camera.type}</h5>
                            <p class="card-text">IP: ${camera.ip}</p>
                            <p class="card-text">Port: ${camera.port}</p>
                            <form class="add-camera-form" data-ip="${camera.ip}" data-port="${camera.port}">
                                <div class="mb-3">
                                    <label class="form-label">Username</label>
                                    <input type="text" class="form-control" name="username" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Password</label>
                                    <input type="password" class="form-control" name="password" required>
                                </div>
                                <button type="submit" class="btn btn-primary">Add Camera</button>
                            </form>
                        </div>
                    `;
                    resultsContainer.appendChild(cameraDiv);

                    // Add form submit handler
                    const form = cameraDiv.querySelector('form');
                    form.addEventListener('submit', async function(e) {
                        e.preventDefault();
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
                                alert('Camera added successfully!');
                                // Optionally refresh the page or update the UI
                                window.location.reload();
                            } else {
                                alert('Error adding camera: ' + result.error);
                            }
                        } catch (error) {
                            console.error('Error:', error);
                            alert('Error adding camera. Please try again.');
                        }
                    });
                });

                // Show the modal
                const discoveryModal = new bootstrap.Modal(document.getElementById('discoveryModal'));
                discoveryModal.show();
            } else {
                alert('Error discovering cameras: ' + data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error discovering cameras. Please try again.');
        }
    });
});
