import requests
import re

# Start a session to maintain cookies
session = requests.Session()

# First, get the login page to obtain the CSRF token
login_url = 'http://localhost:5000/auth/login'
login_response = session.get(login_url)

# Extract CSRF token from the response
csrf_token = re.search('name="csrf_token" value="(.+?)"', login_response.text).group(1)

# Login with the extracted CSRF token
login_data = {
    'username': 'admin',
    'password': 'admin',
    'csrf_token': csrf_token
}

post_response = session.post(login_url, data=login_data)
print(f"Login response status: {post_response.status_code}")

# Now try to access the users page
users_url = 'http://localhost:5000/auth/users'
users_response = session.get(users_url)
print(f"Users page response status: {users_response.status_code}")
print(f"Users page response length: {len(users_response.text)}")

# Check if we got redirected to the login page
if 'login' in users_response.url:
    print("Redirected to login page")
else:
    print("Successfully accessed users page")
    
    # Print a snippet of the response to verify content
    snippet = users_response.text[:500] + '...' if len(users_response.text) > 500 else users_response.text
    print(f"Response snippet: {snippet}")
