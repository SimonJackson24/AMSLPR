# Kubernetes Deployment Guide

This guide provides comprehensive instructions for deploying VisiGate on Kubernetes clusters.

## Prerequisites

- Kubernetes cluster (v1.19+)
- kubectl configured to access the cluster
- Helm 3.x (optional, for advanced deployments)
- Persistent volume support
- Load balancer or ingress controller

## Quick Start

### Basic Deployment

1. **Create namespace:**
   ```bash
   kubectl create namespace visigate
   ```

2. **Apply manifests:**
   ```bash
   kubectl apply -f k8s/
   ```

3. **Check deployment:**
   ```bash
   kubectl get pods -n visigate
   kubectl get services -n visigate
   ```

4. **Access the application:**
   ```bash
   kubectl port-forward -n visigate svc/visigate-service 8080:80
   # Access at http://localhost:8080
   ```

## Kubernetes Manifests

### 1. Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: visigate
  labels:
    name: visigate
    app: license-plate-recognition
```

### 2. ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: visigate-config
  namespace: visigate
data:
  FLASK_ENV: "production"
  HAILO_ENABLED: "true"
  TZ: "UTC"
  LOG_LEVEL: "INFO"
  REDIS_URL: "redis://redis-service:6379"
  DATABASE_URL: "postgresql://visigate:password@postgres-service:5432/visigate"
```

### 3. Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: visigate-secrets
  namespace: visigate
type: Opaque
data:
  # Base64 encoded values
  postgres-password: <base64-encoded-password>
  redis-password: <base64-encoded-password>
  jwt-secret: <base64-encoded-jwt-secret>
  api-key: <base64-encoded-api-key>
```

### 4. Persistent Volumes

```yaml
# k8s/persistent-volumes.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: visigate-data-pvc
  namespace: visigate
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: standard

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: visigate-logs-pvc
  namespace: visigate
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: visigate-models-pvc
  namespace: visigate
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  storageClassName: standard
```

### 5. PostgreSQL Deployment

```yaml
# k8s/postgres-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: visigate
  labels:
    app: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
        env:
        - name: POSTGRES_DB
          value: "visigate"
        - name: POSTGRES_USER
          value: "visigate"
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: visigate-secrets
              key: postgres-password
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - visigate
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - visigate
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: postgres-service
  namespace: visigate
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

### 6. Redis Deployment

```yaml
# k8s/redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: visigate
  labels:
    app: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command: ["redis-server", "--appendonly", "yes"]
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: visigate
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### 7. VisiGate Application Deployment

```yaml
# k8s/visigate-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: visigate
  namespace: visigate
  labels:
    app: visigate
spec:
  replicas: 2
  selector:
    matchLabels:
      app: visigate
  template:
    metadata:
      labels:
        app: visigate
    spec:
      containers:
      - name: visigate
        image: visigate:latest
        ports:
        - containerPort: 5001
        envFrom:
        - configMapRef:
            name: visigate-config
        - secretRef:
            name: visigate-secrets
        env:
        - name: PORT
          value: "5001"
        volumeMounts:
        - name: data-storage
          mountPath: /app/data
        - name: logs-storage
          mountPath: /app/logs
        - name: config-storage
          mountPath: /app/config
        - name: models-storage
          mountPath: /app/models
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5001
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 5001
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
      volumes:
      - name: data-storage
        persistentVolumeClaim:
          claimName: visigate-data-pvc
      - name: logs-storage
        persistentVolumeClaim:
          claimName: visigate-logs-pvc
      - name: config-storage
        configMap:
          name: visigate-config
      - name: models-storage
        persistentVolumeClaim:
          claimName: visigate-models-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: visigate-service
  namespace: visigate
spec:
  selector:
    app: visigate
  ports:
  - port: 80
    targetPort: 5001
    name: http
  type: ClusterIP
```

### 8. Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: visigate-ingress
  namespace: visigate
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - visigate.example.com
    secretName: visigate-tls
  rules:
  - host: visigate.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: visigate-service
            port:
              number: 80
```

### 9. Horizontal Pod Autoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: visigate-hpa
  namespace: visigate
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: visigate
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### 10. Network Policies

```yaml
# k8s/network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: visigate-network-policy
  namespace: visigate
spec:
  podSelector:
    matchLabels:
      app: visigate
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 5001
  - from:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - from:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to: []
    ports:
    - protocol: TCP
      port: 53
    - protocol: UDP
      port: 53
```

## Advanced Deployment Scenarios

### High Availability Setup

```yaml
# k8s/visigate-ha-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: visigate-ha
  namespace: visigate
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 1
  selector:
    matchLabels:
      app: visigate
  template:
    metadata:
      labels:
        app: visigate
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchLabels:
                app: visigate
            topologyKey: kubernetes.io/hostname
      containers:
      - name: visigate
        image: visigate:latest
        ports:
        - containerPort: 5001
        envFrom:
        - configMapRef:
            name: visigate-config
        - secretRef:
            name: visigate-secrets
        volumeMounts:
        - name: shared-storage
          mountPath: /app/data
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5001
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 5001
          initialDelaySeconds: 30
          periodSeconds: 10
      volumes:
      - name: shared-storage
        persistentVolumeClaim:
          claimName: visigate-shared-pvc
```

### GPU-Enabled Deployment

```yaml
# k8s/visigate-gpu-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: visigate-gpu
  namespace: visigate
spec:
  replicas: 1
  selector:
    matchLabels:
      app: visigate-gpu
  template:
    metadata:
      labels:
        app: visigate-gpu
    spec:
      nodeSelector:
        accelerator: nvidia-tesla-k80
      containers:
      - name: visigate
        image: visigate:gpu
        ports:
        - containerPort: 5001
        env:
        - name: NVIDIA_VISIBLE_DEVICES
          value: all
        - name: HAILO_ENABLED
          value: "false"
        - name: GPU_ENABLED
          value: "true"
        resources:
          limits:
            nvidia.com/gpu: 1
        volumeMounts:
        - name: data-storage
          mountPath: /app/data
      volumes:
      - name: data-storage
        persistentVolumeClaim:
          claimName: visigate-data-pvc
```

## Helm Chart

### Chart Structure

```
visigate/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── pvc.yaml
│   └── hpa.yaml
└── charts/
```

### Installation

```bash
# Add repository
helm repo add visigate https://charts.automatesystems.com
helm repo update

# Install with default values
helm install visigate visigate/visigate

# Install with custom values
helm install visigate visigate/visigate -f my-values.yaml
```

### Custom Values

```yaml
# values.yaml
replicaCount: 3

image:
  repository: visigate
  tag: "latest"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: visigate.example.com
      paths:
        - path: /
          pathType: Prefix

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi

persistence:
  enabled: true
  size: 50Gi

postgresql:
  enabled: true
  postgresqlUsername: visigate
  postgresqlDatabase: visigate

redis:
  enabled: true
```

## Monitoring and Observability

### Prometheus Metrics

```yaml
# k8s/monitoring.yaml
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: visigate-monitor
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: visigate
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
```

### Logging

```yaml
# k8s/logging.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: visigate
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush         5
        Log_Level     info
        Daemon        off

    [INPUT]
        Name              tail
        Path              /app/logs/*.log
        Parser            docker
        Tag               visigate.*
        Refresh_Interval  5

    [OUTPUT]
        Name  elasticsearch
        Match visigate.*
        Host  elasticsearch
        Port  9200
        Index visigate
```

## Security

### Pod Security Standards

```yaml
# k8s/security.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: visigate-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'persistentVolumeClaim'
    - 'secret'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  supplementalGroups:
    rule: 'MustRunAs'
    ranges:
    - min: 1
      max: 65535
  fsGroup:
    rule: 'MustRunAs'
    ranges:
    - min: 1
      max: 65535
```

### Network Policies

```yaml
# k8s/network-security.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: visigate-security
  namespace: visigate
spec:
  podSelector:
    matchLabels:
      app: visigate
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to: []
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
```

## Backup and Recovery

### Database Backup

```yaml
# k8s/backup.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: visigate-backup
  namespace: visigate
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - /bin/sh
            - -c
            - |
              pg_dump -h postgres-service -U visigate visigate > /backup/backup-$(date +%Y%m%d-%H%M%S).sql
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: visigate-secrets
                  key: postgres-password
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

## Troubleshooting

### Common Issues

1. **Pods not starting:**
   ```bash
   kubectl describe pod <pod-name> -n visigate
   kubectl logs <pod-name> -n visigate
   ```

2. **Service not accessible:**
   ```bash
   kubectl get endpoints -n visigate
   kubectl describe service visigate-service -n visigate
   ```

3. **Persistent volume issues:**
   ```bash
   kubectl get pvc -n visigate
   kubectl describe pvc <pvc-name> -n visigate
   ```

4. **Resource constraints:**
   ```bash
   kubectl top pods -n visigate
   kubectl top nodes
   ```

### Debug Commands

```bash
# Check pod status
kubectl get pods -n visigate -o wide

# View pod logs
kubectl logs -f <pod-name> -n visigate

# Execute commands in pod
kubectl exec -it <pod-name> -n visigate -- /bin/bash

# Check events
kubectl get events -n visigate --sort-by=.metadata.creationTimestamp

# Check resource usage
kubectl top pods -n visigate
kubectl top nodes
```

## Best Practices

1. **Use resource limits and requests** for all containers
2. **Implement health checks** for all services
3. **Use ConfigMaps and Secrets** for configuration
4. **Implement proper RBAC** policies
5. **Use network policies** to restrict traffic
6. **Implement backup strategies** for data persistence
7. **Monitor resource usage** and adjust accordingly
8. **Use rolling updates** for zero-downtime deployments
9. **Implement proper logging** and monitoring
10. **Regularly update images** for security patches

## Support

For additional support or questions about Kubernetes deployment:

- Check the [troubleshooting guide](../troubleshooting/kubernetes_issues.md)
- Review the [configuration reference](../deployment/configuration.md)
- Contact support at support@visigate.com