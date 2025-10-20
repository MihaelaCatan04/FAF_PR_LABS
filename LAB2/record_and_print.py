
import threading

import time
stats_lock = threading.Lock()
per_ip_stats = {}


def record_and_print(ip, success):
    now = time.time()
    with stats_lock:
        stat = per_ip_stats.get(ip)
        if stat is None:
            stat = {'success': 0, 'handled': 0, 'start': now}
            per_ip_stats[ip] = stat

        stat['handled'] += 1
        if success:
            stat['success'] += 1

        if stat['handled'] % 10 == 0:
            elapsed = max(1e-6, now - stat['start'])
            succ_per_sec = stat['success'] / elapsed
            print(f"THROUGHPUT [{ip}]: {stat['success']} successful in {elapsed:.2f}s -> {succ_per_sec:.2f} req/s (handled={stat['handled']})")
