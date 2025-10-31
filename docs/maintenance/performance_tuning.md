# Performance Tuning Guide

This guide provides comprehensive strategies for optimizing AMSLPR performance across different deployment scenarios.

## Performance Monitoring

### Key Metrics to Monitor

1. **OCR Processing Time:**
   - Average processing time per image
   - 95th percentile processing time
   - Processing time distribution

2. **System Resources:**
   - CPU utilization
   - Memory usage
   - Disk I/O
   - Network bandwidth

3. **Application Metrics:**
   - Request response times
   - Error rates
   - Throughput (requests per second)
   - Queue lengths

### Monitoring Tools

#### Built-in Monitoring

```python
# Enable performance monitoring
from src.utils.monitoring import PerformanceMonitor

monitor = PerformanceMonitor()
monitor.start()

# Get performance metrics
metrics = monitor.get_metrics()
print(f"OCR processing time: {metrics['ocr_avg_time']}ms")
print(f"CPU usage: {metrics['cpu_percent']}%")
print(f"Memory usage: {metrics['memory_percent']}%")
```

#### External Monitoring

```yaml
# Prometheus configuration
scrape_configs:
  - job_name: 'amslpr'
    static_configs:
      - targets: ['localhost:5001']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## OCR Performance Optimization

### Hardware Acceleration

#### Hailo TPU Optimization

```json
{
  "ocr_config": {
    "use_hailo_tpu": true,
    "hailo_batch_size": 4,
    "hailo_async_processing": true,
    "hailo_power_mode": "ultra_performance"
  }
}
```

**Performance Impact:**
- **Without Hailo:** ~500ms per plate
- **With Hailo:** ~50ms per plate
- **Improvement:** 10x faster processing

#### GPU Acceleration

```json
{
  "ocr_config": {
    "use_gpu": true,
    "gpu_device": 0,
    "gpu_memory_fraction": 0.8,
    "gpu_batch_size": 8
  }
}
```

### Software Optimization

#### Tesseract Optimization

```json
{
  "tesseract_config": {
    "psm_mode": 7,
    "oem_mode": 1,
    "tessedit_char_whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "tessedit_pageseg_mode": "7",
    "tessedit_ocr_engine_mode": "1"
  }
}
```

#### Image Preprocessing Optimization

```json
{
  "preprocessing": {
    "resize_factor": 2.0,
    "apply_contrast_enhancement": true,
    "contrast_clip_limit": 2.0,
    "apply_noise_reduction": true,
    "noise_reduction_strength": 7,
    "apply_threshold": true,
    "threshold_method": "adaptive",
    "block_size": 11,
    "c_value": 2
  }
}
```

### Batch Processing

```python
# Implement batch processing for multiple images
from src.recognition.batch_processor import BatchProcessor

processor = BatchProcessor(batch_size=8, num_workers=4)
results = processor.process_batch(image_list)
```

**Performance Benefits:**
- **Batch Size 1:** 500ms per image
- **Batch Size 8:** 125ms per image (4x improvement)
- **Batch Size 16:** 80ms per image (6.25x improvement)

## System Resource Optimization

### CPU Optimization

#### Thread Pool Configuration

```python
import concurrent.futures

# Configure thread pool for CPU-bound tasks
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process_image, img) for img in images]
    results = [future.result() for future in concurrent.futures.as_completed(futures)]
```

#### Process Affinity

```bash
# Pin processes to specific CPU cores
taskset -c 0-3 python run_server.py

# For Docker containers
docker run --cpuset-cpus="0-3" amslpr:latest
```

### Memory Optimization

#### Memory Pool Management

```python
import numpy as np
from src.utils.memory_pool import MemoryPool

# Pre-allocate memory pool
memory_pool = MemoryPool(size_mb=512)
image_buffer = memory_pool.allocate((1080, 1920, 3), dtype=np.uint8)
```

#### Garbage Collection Tuning

```python
import gc

# Tune garbage collection for better performance
gc.set_threshold(700, 10, 10)
gc.disable()  # Disable automatic GC
gc.collect()  # Manual collection when needed
```

### Disk I/O Optimization

#### Asynchronous I/O

```python
import aiofiles
import asyncio

async def save_image_async(image_data, filepath):
    async with aiofiles.open(filepath, 'wb') as f:
        await f.write(image_data)
```

#### File System Optimization

```bash
# Use faster file system (ext4 with optimizations)
tune2fs -o journal_data_writeback /dev/sda1
tune2fs -O ^has_journal /dev/sda1

# Mount options for better performance
mount -o noatime,nodiratime,data=writeback /dev/sda1 /app/data
```

## Caching Strategies

### Redis Caching

```python
from redis import Redis
from src.cache.redis_cache import RedisCache

# Configure Redis cache
cache = RedisCache(
    host='localhost',
    port=6379,
    db=0,
    ttl=3600,
    max_memory='512mb',
    policy='allkeys-lru'
)

# Cache OCR results
@cache.cached(timeout=3600)
def recognize_plate(image):
    return detector.recognize(image)
```

### Multi-Level Caching

```python
from src.cache.multi_level_cache import MultiLevelCache

# Configure multi-level cache
cache = MultiLevelCache(
    l1_cache=MemoryCache(size_mb=128),
    l2_cache=RedisCache(host='localhost', port=6379),
    l3_cache=FileCache(path='/app/cache')
)
```

### Cache Performance Metrics

- **Memory Cache Hit Rate:** 95%
- **Redis Cache Hit Rate:** 85%
- **File Cache Hit Rate:** 70%
- **Overall Hit Rate:** 92%

## Database Optimization

### Connection Pooling

```python
from src.database.connection_pool import ConnectionPool

# Configure connection pool
pool = ConnectionPool(
    min_connections=5,
    max_connections=20,
    connection_timeout=30,
    idle_timeout=300
)
```

### Query Optimization

```sql
-- Create optimized indexes
CREATE INDEX idx_access_logs_plate_time ON access_logs(plate_number, access_time);
CREATE INDEX idx_access_logs_time_direction ON access_logs(access_time, direction);

-- Use EXPLAIN to analyze queries
EXPLAIN QUERY PLAN SELECT * FROM access_logs WHERE plate_number = ? AND access_time > ?;
```

### Database Maintenance

```bash
# Regular maintenance tasks
sqlite3 data/amslpr.db "VACUUM;"
sqlite3 data/amslpr.db "REINDEX;"
sqlite3 data/amslpr.db "ANALYZE;"

# Backup with compression
sqlite3 data/amslpr.db ".backup backup.db"
gzip backup.db
```

## Network Optimization

### HTTP/2 Configuration

```python
from flask import Flask
from werkzeug.middleware.http2 import HTTP2Middleware

app = Flask(__name__)
app.wsgi_app = HTTP2Middleware(app.wsgi_app)
```

### Connection Pooling

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure connection pooling
session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

### WebSocket Optimization

```python
from flask_socketio import SocketIO

# Configure SocketIO for real-time updates
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e8
)
```

## Load Balancing and Scaling

### Horizontal Scaling

```yaml
# Kubernetes HPA configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: amslpr-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: amslpr
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Load Balancer Configuration

```yaml
# NGINX load balancer configuration
upstream amslpr_backend {
    least_conn;
    server amslpr-1:5001;
    server amslpr-2:5001;
    server amslpr-3:5001;
}

server {
    listen 80;
    location / {
        proxy_pass http://amslpr_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Performance Benchmarking

### Benchmarking Tools

```python
from src.utils.benchmark import PerformanceBenchmark

# Run performance benchmarks
benchmark = PerformanceBenchmark()
results = benchmark.run_benchmarks(
    test_cases=['ocr_single', 'ocr_batch', 'api_endpoints', 'database_queries'],
    iterations=100,
    concurrency=4
)

print(f"Average OCR time: {results['ocr_single']['avg_time']}ms")
print(f"P95 OCR time: {results['ocr_single']['p95_time']}ms")
print(f"Throughput: {results['ocr_batch']['throughput']} images/sec")
```

### Performance Baselines

| Component | Baseline | Optimized | Improvement |
|-----------|----------|-----------|-------------|
| OCR Processing | 500ms | 50ms | 10x |
| API Response | 200ms | 50ms | 4x |
| Database Query | 100ms | 20ms | 5x |
| Image Processing | 300ms | 80ms | 3.75x |

## Monitoring and Alerting

### Performance Alerts

```yaml
# Prometheus alerting rules
groups:
  - name: amslpr_performance
    rules:
      - alert: HighOCRProcessingTime
        expr: amslpr_ocr_processing_time > 500
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High OCR processing time detected"
          description: "OCR processing time is {{ $value }}ms"

      - alert: HighCPUUsage
        expr: rate(cpu_usage_percent[5m]) > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is {{ $value }}%"
```

### Performance Dashboards

```yaml
# Grafana dashboard configuration
dashboard:
  title: AMSLPR Performance
  panels:
    - title: OCR Processing Time
      type: graph
      targets:
        - expr: amslpr_ocr_processing_time
          legendFormat: "OCR Time"

    - title: System Resources
      type: graph
      targets:
        - expr: cpu_usage_percent
          legendFormat: "CPU %"
        - expr: memory_usage_percent
          legendFormat: "Memory %"
        - expr: disk_usage_percent
          legendFormat: "Disk %"
```

## Capacity Planning

### Resource Requirements

| Load Level | CPU Cores | Memory (GB) | Storage (GB) | Network (Mbps) |
|------------|-----------|-------------|--------------|----------------|
| Light (100 plates/day) | 2 | 4 | 50 | 10 |
| Medium (1000 plates/day) | 4 | 8 | 200 | 50 |
| Heavy (10000 plates/day) | 8 | 16 | 1000 | 200 |
| Extreme (50000 plates/day) | 16 | 32 | 2000 | 500 |

### Scaling Guidelines

1. **Vertical Scaling:**
   - Increase CPU cores for CPU-bound workloads
   - Add memory for larger datasets
   - Use faster storage for I/O intensive operations

2. **Horizontal Scaling:**
   - Deploy multiple instances behind load balancer
   - Use shared database with connection pooling
   - Implement distributed caching

3. **Auto-scaling:**
   - Set up HPA based on CPU/memory metrics
   - Configure minimum and maximum replica counts
   - Monitor scaling events and adjust thresholds

## Maintenance Tasks

### Regular Performance Maintenance

```bash
# Daily tasks
#!/bin/bash
# Clear old cache entries
redis-cli KEYS "amslpr:*" | xargs redis-cli DEL

# Optimize database
sqlite3 data/amslpr.db "VACUUM;"

# Rotate logs
logrotate /etc/logrotate.d/amslpr

# Weekly tasks
#!/bin/bash
# Full database optimization
sqlite3 data/amslpr.db "REINDEX;"
sqlite3 data/amslpr.db "ANALYZE;"

# Clean old images
find /app/data/images -type f -mtime +30 -delete

# Monthly tasks
#!/bin/bash
# Performance benchmarking
python scripts/benchmark.py

# Security updates
pip install --upgrade -r requirements.txt

# Backup verification
python scripts/verify_backup.py
```

### Performance Troubleshooting

#### Slow OCR Performance

1. **Check Hardware Utilization:**
   ```bash
   nvidia-smi  # GPU usage
   hailortcli scan  # Hailo TPU status
   htop  # CPU/memory usage
   ```

2. **Profile Application:**
   ```python
   import cProfile
   cProfile.run('recognize_plate(image)', 'profile_output.prof')

   # Analyze profile
   import pstats
   p = pstats.Stats('profile_output.prof')
   p.sort_stats('cumulative').print_stats(20)
   ```

3. **Database Query Analysis:**
   ```sql
   EXPLAIN QUERY PLAN SELECT * FROM access_logs WHERE plate_number = ?;
   .timer ON
   SELECT COUNT(*) FROM access_logs WHERE access_time > datetime('now', '-1 hour');
   ```

#### Memory Leaks

1. **Monitor Memory Usage:**
   ```python
   import tracemalloc
   tracemalloc.start()

   # Take snapshot
   snapshot = tracemalloc.take_snapshot()
   top_stats = snapshot.statistics('lineno')

   for stat in top_stats[:10]:
       print(stat)
   ```

2. **Garbage Collection Analysis:**
   ```python
   import gc
   gc.set_debug(gc.DEBUG_STATS)

   # Force garbage collection
   collected = gc.collect()
   print(f"Objects collected: {collected}")
   ```

## Best Practices

### Performance Optimization Checklist

- [ ] Enable hardware acceleration (Hailo TPU/GPU)
- [ ] Configure appropriate batch sizes
- [ ] Implement caching strategies
- [ ] Optimize database queries and indexes
- [ ] Configure connection pooling
- [ ] Set up monitoring and alerting
- [ ] Implement load balancing
- [ ] Configure auto-scaling
- [ ] Regular performance benchmarking
- [ ] Capacity planning and resource allocation

### Monitoring Checklist

- [ ] CPU, memory, and disk usage
- [ ] Application response times
- [ ] Error rates and throughput
- [ ] Database query performance
- [ ] Cache hit rates
- [ ] Network latency and bandwidth
- [ ] OCR processing times
- [ ] System resource utilization

### Maintenance Checklist

- [ ] Regular software updates
- [ ] Database optimization and vacuuming
- [ ] Log rotation and cleanup
- [ ] Cache clearing and optimization
- [ ] Backup verification
- [ ] Security patching
- [ ] Performance benchmarking
- [ ] Hardware health checks