# User Management System

## Overview

The AMSLPR system includes a comprehensive user management system that provides role-based access control (RBAC) to the application. This system ensures that only authorized users can access specific features and functionality based on their assigned roles and permissions.

## Features

### User Authentication

- Secure login with username and password
- Password hashing with salt for enhanced security
- Session management for authenticated users
- Automatic logout on session expiration

### User Management

- Create, update, and delete user accounts
- Assign roles to users
- Manage user profiles including name and email
- Change passwords with proper verification

### Role-Based Access Control

- Three predefined roles: Admin, Operator, and Viewer
- Granular permissions for different system functions
- Permission-based access to sensitive operations
- Role-specific UI elements and navigation

## Roles and Permissions

### Admin

- **Description**: Administrator with full access to all system features
- **Permissions**: view, edit, admin
- **Capabilities**:
  - Manage users (create, update, delete)
  - Configure system settings
  - Manage cameras and recognition settings
  - Access all reports and statistics
  - Manage vehicle database
  - Configure notification settings

### Operator

- **Description**: Operator with limited access to system features
- **Permissions**: view, edit
- **Capabilities**:
  - Manage vehicle database
  - View and generate reports
  - Configure cameras and recognition settings
  - View statistics and logs
  - Cannot manage users or system settings

### Viewer

- **Description**: Viewer with read-only access to system features
- **Permissions**: view
- **Capabilities**:
  - View camera feeds and recognition results
  - View vehicle database
  - View reports and statistics
  - View logs
  - Cannot make any changes to the system

## Implementation Details

### User Data Storage

User data is stored in a JSON file located at `/config/users.json`. This file contains user information including:

- Username
- Hashed password and salt
- Role
- Name
- Email
- Creation timestamp
- Last login timestamp

The file is secured with appropriate permissions to prevent unauthorized access.

### Authentication Flow

1. User enters username and password on the login page
2. System hashes the provided password with the stored salt
3. System compares the hashed password with the stored hash
4. If matched, user is authenticated and session is created
5. Session contains user information including username, role, and permissions

### Security Considerations

- Passwords are never stored in plain text
- PBKDF2 with SHA-256 is used for password hashing
- 100,000 iterations are used for password hashing to prevent brute force attacks
- User configuration file has restricted permissions (readable only by owner)
- Default admin password is randomly generated on first run

## Usage

### Login

Access the login page at `/auth/login`. Enter your username and password to authenticate.

### User Profile

Access your user profile at `/auth/profile`. Here you can:

- Update your name and email
- Change your password

### User Management (Admin Only)

Access the user management page at `/auth/users`. Here you can:

- View all users and their roles
- Add new users
- Edit existing users
- Delete users

## API Reference

### Authentication Decorators

The following decorators are available for securing routes:

- `@login_required`: Requires the user to be authenticated
- `@permission_required(permission)`: Requires the user to have a specific permission
- `@role_required(role)`: Requires the user to have a specific role

### User Manager API

The `UserManager` class provides the following methods:

- `add_user(username, password, role, name=None, email=None)`: Add a new user
- `update_user(username, **kwargs)`: Update an existing user
- `delete_user(username)`: Delete a user
- `authenticate(username, password)`: Authenticate a user
- `get_users()`: Get all users
- `get_user(username)`: Get a specific user
- `get_roles()`: Get all roles
- `get_permissions(role)`: Get permissions for a role
- `has_permission(username, permission)`: Check if a user has a specific permission

## Troubleshooting

### Default Admin Account

If you forget your admin password, you can delete the `/config/users.json` file and restart the application. A new default admin account will be created with a randomly generated password, which will be logged in the application logs.

### Permission Issues

If you're unable to access certain features, check your assigned role and permissions. Contact your system administrator if you need additional permissions.

### Session Expiration

If your session expires, you will be redirected to the login page. This is a security feature to prevent unauthorized access.
