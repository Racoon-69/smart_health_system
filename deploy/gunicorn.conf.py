import multiprocessing
import os

bind = "0.0.0.0:8000"
workers = int(os.getenv("WEB_CONCURRENCY", min(multiprocessing.cpu_count() * 2 + 1, 4)))
worker_class = "sync"
threads = int(os.getenv("GUNICORN_THREADS", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
graceful_timeout = 30
keepalive = 5
max_requests = 1200
max_requests_jitter = 120
accesslog = "-"
errorlog = "-"
capture_output = True
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
