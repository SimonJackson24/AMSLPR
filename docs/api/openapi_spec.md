# AMSLPR OpenAPI Specification

This document contains the OpenAPI 3.0.3 specification for the AMSLPR API.

```yaml
openapi: 3.0.3
info:
  title: AMSLPR API
  description: |
    AMSLPR (Automate Systems License Plate Recognition) API provides comprehensive endpoints for license plate recognition, vehicle management, access control, and system monitoring.
  version: "1.0.0"
  contact:
    name: AMSLPR Support
    email: support@automatesystems.com
  license:
    name: Proprietary
    url: https://www.automatesystems.com/license

servers:
  - url: https://api.amslpr.local/api
    description: Production server
  - url: http://localhost:5000/api
    description: Development server

security:
  - ApiKeyAuth: []
  - BearerAuth: []

components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header
      name: X-API-Key
      description: API key for authentication
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: JWT token for authentication

  schemas:
    Vehicle:
      type: object
      properties:
        plate_number:
          type: string
          description: License plate number
          example: "ABC123"
        description:
          type: string
          description: Vehicle description
          example: "John's Car"
        authorized:
          type: boolean
          description: Whether the vehicle is authorized
          example: true
        valid_from:
          type: string
          format: date-time
          description: Start date for authorization
        valid_until:
          type: string
          format: date-time
          description: End date for authorization
        created_at:
          type: string
          format: date-time
          description: Creation timestamp
        updated_at:
          type: string
          format: date-time
          description: Last update timestamp

    AccessLog:
      type: object
      properties:
        id:
          type: integer
          description: Log entry ID
        plate_number:
          type: string
          description: License plate number
        direction:
          type: string
          enum: [entry, exit]
          description: Access direction
        authorized:
          type: boolean
          description: Whether access was authorized
        access_time:
          type: string
          format: date-time
          description: Timestamp of access
        image_path:
          type: string
          description: Path to captured image

    SystemStatus:
      type: object
      properties:
        status:
          type: string
          enum: [ok, warning, error]
          description: Overall system status
        version:
          type: string
          description: System version
        uptime:
          type: integer
          description: System uptime in seconds
        resources:
          type: object
          properties:
            cpu_percent:
              type: number
              format: float
              description: CPU usage percentage
            memory_percent:
              type: number
              format: float
              description: Memory usage percentage
            disk_percent:
              type: number
              format: float
              description: Disk usage percentage
            cpu_temp:
              type: number
              format: float
              description: CPU temperature in Celsius
        camera_status:
          type: string
          enum: [active, inactive, error]
          description: Camera system status
        barrier_status:
          type: string
          enum: [ready, busy, error]
          description: Barrier system status

    OCRConfig:
      type: object
      properties:
        ocr_method:
          type: string
          enum: [tesseract, deep_learning, hybrid]
          description: OCR method to use
        use_hailo_tpu:
          type: boolean
          description: Whether to use Hailo TPU acceleration
        confidence_threshold:
          type: number
          format: float
          minimum: 0.0
          maximum: 1.0
          description: Minimum confidence threshold
        tesseract_config:
          type: object
          properties:
            psm_mode:
              type: integer
              description: Tesseract PSM mode
            oem_mode:
              type: integer
              description: Tesseract OEM mode
            whitelist:
              type: string
              description: Character whitelist
        preprocessing:
          type: object
          properties:
            resize_factor:
              type: number
              format: float
              description: Image resize factor
            apply_contrast_enhancement:
              type: boolean
              description: Apply contrast enhancement
            apply_noise_reduction:
              type: boolean
              description: Apply noise reduction
            apply_perspective_correction:
              type: boolean
              description: Apply perspective correction

    Error:
      type: object
      properties:
        error:
          type: string
          description: Error message
        code:
          type: integer
          description: Error code

paths:
  # Authentication
  /auth/token:
    post:
      summary: Obtain authentication token
      description: Authenticate user and obtain JWT token
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - username
                - password
              properties:
                username:
                  type: string
                  example: "admin"
                password:
                  type: string
                  example: "password123"
      responses:
        '200':
          description: Authentication successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  token:
                    type: string
                    description: JWT token
                  expires:
                    type: string
                    format: date-time
                    description: Token expiration time
        '401':
          description: Authentication failed
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # System Status
  /system/status:
    get:
      summary: Get system status
      description: Retrieve current system status and resource usage
      security:
        - BearerAuth: []
      responses:
        '200':
          description: System status retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SystemStatus'
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Vehicles
  /vehicles:
    get:
      summary: Get all vehicles
      description: Retrieve list of all vehicles in the system
      security:
        - ApiKeyAuth: []
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 100
          description: Maximum number of vehicles to return
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
          description: Number of vehicles to skip
        - name: authorized
          in: query
          schema:
            type: boolean
          description: Filter by authorization status
      responses:
        '200':
          description: Vehicles retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  vehicles:
                    type: array
                    items:
                      $ref: '#/components/schemas/Vehicle'
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /vehicles/{plate_number}:
    get:
      summary: Get vehicle details
      description: Retrieve details for a specific vehicle
      security:
        - ApiKeyAuth: []
      parameters:
        - name: plate_number
          in: path
          required: true
          schema:
            type: string
          description: License plate number
      responses:
        '200':
          description: Vehicle details retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Vehicle'
        '404':
          description: Vehicle not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Access Logs
  /access-logs:
    get:
      summary: Get access logs
      description: Retrieve access logs with optional filtering
      security:
        - ApiKeyAuth: []
      parameters:
        - name: plate_number
          in: query
          schema:
            type: string
          description: Filter by license plate number
        - name: start_time
          in: query
          schema:
            type: string
            format: date-time
          description: Start time for filtering
        - name: end_time
          in: query
          schema:
            type: string
            format: date-time
          description: End time for filtering
        - name: limit
          in: query
          schema:
            type: integer
            default: 100
          description: Maximum number of logs to return
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
          description: Number of logs to skip
      responses:
        '200':
          description: Access logs retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_logs:
                    type: array
                    items:
                      $ref: '#/components/schemas/AccessLog'
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # OCR Configuration
  /ocr/api/config:
    get:
      summary: Get OCR configuration
      description: Retrieve current OCR configuration settings
      responses:
        '200':
          description: OCR configuration retrieved successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OCRConfig'
    post:
      summary: Update OCR configuration
      description: Update OCR configuration settings
      security:
        - BearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/OCRConfig'
      responses:
        '200':
          description: OCR configuration updated successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  message:
                    type: string
                    example: "OCR configuration updated successfully"
        '400':
          description: Invalid configuration
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: false
                  message:
                    type: string
                    example: "Invalid configuration format"
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /ocr/api/reload:
    post:
      summary: Reload OCR configuration
      description: Reload OCR configuration without changing settings
      security:
        - BearerAuth: []
      responses:
        '200':
          description: OCR configuration reloaded successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  message:
                    type: string
                    example: "OCR configuration reloaded successfully"
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Nayax Integration
  /nayax/request-payment:
    post:
      summary: Request Nayax payment
      description: Request payment from Nayax terminal
      security:
        - ApiKeyAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - amount
                - session_id
                - plate_number
              properties:
                amount:
                  type: number
                  format: float
                  description: Payment amount
                  example: 10.50
                session_id:
                  type: integer
                  description: Session ID
                  example: 123
                plate_number:
                  type: string
                  description: License plate number
                  example: "ABC123"
                payment_location:
                  type: string
                  enum: [entry, exit]
                  default: exit
                  description: Payment location
      responses:
        '200':
          description: Payment request processed
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  message:
                    type: string
                  transaction_id:
                    type: string
        '400':
          description: Invalid request data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /nayax/transaction-status:
    get:
      summary: Get Nayax transaction status
      description: Get current Nayax transaction status
      security:
        - ApiKeyAuth: []
      responses:
        '200':
          description: Transaction status retrieved
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum: [idle, waiting, processing, completed, failed]
                  transaction_id:
                    type: string
                  amount:
                    type: number
                    format: float
                  plate_number:
                    type: string
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /nayax/cancel-transaction:
    post:
      summary: Cancel Nayax transaction
      description: Cancel current Nayax transaction
      security:
        - ApiKeyAuth: []
      responses:
        '200':
          description: Transaction cancelled
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  message:
                    type: string
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Camera Management
  /camera/{camera_id}/settings:
    get:
      summary: Get camera settings
      description: Retrieve settings for a specific camera
      security:
        - ApiKeyAuth: []
      parameters:
        - name: camera_id
          in: path
          required: true
          schema:
            type: string
          description: Camera ID
      responses:
        '200':
          description: Camera settings retrieved
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  camera:
                    type: object
                    properties:
                      id:
                        type: string
                      name:
                        type: string
                      ip:
                        type: string
                      port:
                        type: integer
                      username:
                        type: string
                      enabled:
                        type: boolean
                      detection_area:
                        type: object
                        description: Detection area coordinates
        '404':
          description: Camera not found
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: false
                  error:
                    type: string
                    example: "Camera not found"
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /camera/{camera_id}/test-connection:
    post:
      summary: Test camera connection
      description: Test connection to a specific camera
      security:
        - ApiKeyAuth: []
      parameters:
        - name: camera_id
          in: path
          required: true
          schema:
            type: string
          description: Camera ID
      requestBody:
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                username:
                  type: string
                  description: Camera username (optional, uses stored value if not provided)
                password:
                  type: string
                  description: Camera password (optional, uses stored value if not provided)
      responses:
        '200':
          description: Connection test successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
        '200':
          description: Connection test failed
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: false
                  error:
                    type: string
                    example: "Connection failed"
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Statistics
  /stats/api/daily:
    get:
      summary: Get daily statistics
      description: Retrieve daily traffic statistics
      security:
        - BearerAuth: []
      parameters:
        - name: days
          in: query
          schema:
            type: integer
            default: 7
          description: Number of days to include
      responses:
        '200':
          description: Daily statistics retrieved
          content:
            application/json:
              schema:
                type: object
                properties:
                  dates:
                    type: array
                    items:
                      type: string
                      format: date
                  entry:
                    type: array
                    items:
                      type: integer
                  exit:
                    type: array
                    items:
                      type: integer
                  total:
                    type: array
                    items:
                      type: integer
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /stats/api/hourly:
    get:
      summary: Get hourly statistics
      description: Retrieve hourly traffic statistics
      security:
        - BearerAuth: []
      parameters:
        - name: hours
          in: query
          schema:
            type: integer
            default: 24
          description: Number of hours to include
      responses:
        '200':
          description: Hourly statistics retrieved
          content:
            application/json:
              schema:
                type: object
                properties:
                  hours:
                    type: array
                    items:
                      type: integer
                  entry:
                    type: array
                    items:
                      type: integer
                  exit:
                    type: array
                    items:
                      type: integer
                  total:
                    type: array
                    items:
                      type: integer
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /stats/api/vehicle-types:
    get:
      summary: Get vehicle type statistics
      description: Retrieve statistics by vehicle type
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Vehicle type statistics retrieved
          content:
            application/json:
              schema:
                type: object
                description: Vehicle type statistics object
        '401':
          description: Authentication required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  # Health Check
  /health:
    get:
      summary: Health check
      description: Check if the API is healthy and responding
      responses:
        '200':
          description: API is healthy
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: "healthy"