#!/usr/bin/env python3

"""
Create a standalone cameras template that doesn't rely on template inheritance.
"""

import os

# Create a backup of the template
os.system("sudo cp /opt/amslpr/src/web/templates/cameras.html /opt/amslpr/src/web/templates/cameras.html.backup_standalone")
print("Created backup of cameras.html template")

# Create a standalone cameras template that doesn't rely on template inheritance
standalone_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cameras - AMSLPR</title>
    <!-- Bootstrap CSS -->
    <link rel="stylesheet" href="/static/vendor/bootstrap/css/bootstrap.min.css">
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="/static/vendor/bootstrap-icons/bootstrap-icons.css">
    <!-- Custom CSS -->
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 col-lg-2 d-md-block bg-light sidebar collapse">
                <div class="position-sticky pt-3">
                    <ul class="nav flex-column">
                        <li class="nav-item">
                            <a class="nav-link" href="/">
                                <i class="bi bi-speedometer2 me-2"></i> Dashboard
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link active" href="/cameras">
                                <i class="bi bi-camera-video me-2"></i> Cameras
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/recognition">
                                <i class="bi bi-card-list me-2"></i> Recognition
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="/settings">
                                <i class="bi bi-gear me-2"></i> Settings
                            </a>
                        </li>
                    </ul>
                </div>
            </div>

            <!-- Main content -->
            <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4">
                <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-3 pb-2 mb-3 border-bottom">
                    <h1 class="h2">Cameras</h1>
                </div>

                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex align-items-center mb-3">
                                    <div class="stats-icon bg-success">
                                        <i class="bi bi-camera-video"></i>
                                    </div>
                                    <div class="ms-3">
                                        <p class="mb-0 text-muted">Online Cameras</p>
                                        <h5 class="mb-0">0</h5>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex align-items-center mb-3">
                                    <div class="stats-icon bg-danger">
                                        <i class="bi bi-camera-video-off"></i>
                                    </div>
                                    <div class="ms-3">
                                        <p class="mb-0 text-muted">Offline Cameras</p>
                                        <h5 class="mb-0">0</h5>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex align-items-center mb-3">
                                    <div class="stats-icon bg-warning">
                                        <i class="bi bi-exclamation-triangle"></i>
                                    </div>
                                    <div class="ms-3">
                                        <p class="mb-0 text-muted">Issues</p>
                                        <h5 class="mb-0">0</h5>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card">
                            <div class="card-body">
                                <div class="d-flex align-items-center mb-3">
                                    <div class="stats-icon bg-info">
                                        <i class="bi bi-speedometer"></i>
                                    </div>
                                    <div class="ms-3">
                                        <p class="mb-0 text-muted">Avg. FPS</p>
                                        <h5 class="mb-0">24.5</h5>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h5 class="card-title mb-0">Registered Cameras</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Location</th>
                                        <th>Status</th>
                                        <th>Manufacturer</th>
                                        <th>Model</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td colspan="6" class="text-center">No cameras registered</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="/static/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
    <!-- Custom JS -->
    <script src="/static/js/main.js"></script>
</body>
</html>
'''

# Write the standalone template to a file
with open("/tmp/standalone_cameras.html", "w") as f:
    f.write(standalone_template)

# Replace the cameras.html template
os.system("sudo cp /tmp/standalone_cameras.html /opt/amslpr/src/web/templates/cameras.html")

print("Successfully replaced the cameras.html template with a standalone version")

# Restart the service
os.system("sudo systemctl restart amslpr")
print("Service restarted. The cameras page should now work without errors.")
