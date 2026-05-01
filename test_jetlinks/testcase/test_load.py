import time
import threading
import random
import json

import allure
import numpy as np
import pytest
import paho.mqtt.client as mqtt

# 平台常量（实际可从 fixture 动态获取）
DEFAULT_BROKER = "127.0.0.1"
DEFAULT_PORT = 1885
DEFAULT_USERNAME = "1111"
DEFAULT_PASSWORD = "1111"

class LoadStats:
    """线程安全的高精度统计收集器"""
    def __init__(self):
        self.lock = threading.Lock()
        self.success_count = 0
        self.failure_count = 0
        self.latencies = []          # 存储每次成功上报的延迟（毫秒）

    def add_success(self, latency_ms):
        with self.lock:
            self.success_count += 1
            self.latencies.append(latency_ms)

    def add_failure(self):
        with self.lock:
            self.failure_count += 1

    @property
    def total_requests(self):
        return self.success_count + self.failure_count

    def summary(self):
        if not self.latencies:
            return {
                "total": self.total_requests,
                "success": self.success_count,
                "failure": self.failure_count,
                "avg_latency": None,
                "p50": None,
                "p95": None,
                "p99": None,
                "max": None,
                "latencies": []  # 空列表，方便绘图函数检查
            }
        arr = np.array(self.latencies)
        return {
            "total": self.total_requests,
            "success": self.success_count,
            "failure": self.failure_count,
            "avg_latency": np.mean(arr),
            "p50": np.percentile(arr, 50),
            "p95": np.percentile(arr, 95),
            "p99": np.percentile(arr, 99),
            "max": np.max(arr),
            "latencies": self.latencies  # 原始数据
        }

def device_worker(device_id, product_id, duration, stats):
    """单个设备的工作线程：连接 → 循环上报 → 断开"""
    client = mqtt.Client(client_id=device_id)
    client.username_pw_set(DEFAULT_USERNAME, DEFAULT_PASSWORD)

    topic = f"/{product_id}/{device_id}/properties/report"

    try:
        client.connect(DEFAULT_BROKER, DEFAULT_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"[{device_id}] 连接失败: {e}")
        stats.add_failure()
        return

    # 使用 perf_counter 获取高精度计时
    start = time.perf_counter()
    while time.perf_counter() - start < duration:
        temperature = round(45 + 20 * random.random(), 1)
        payload = {
            "properties": {"temperature": temperature, "humidity": random.randint(30, 90)},
            "timestamp": int(time.time() * 1000)
        }
        req_start = time.perf_counter()
        try:
            msg_info = client.publish(topic, json.dumps(payload), qos=1)
            msg_info.wait_for_publish(timeout=3)
            latency = (time.perf_counter() - req_start) * 1000  # 转换为毫秒
            stats.add_success(latency)
        except Exception as e:
            print(f"[{device_id}] 上报失败: {e}")
            stats.add_failure()

        # 随机上报间隔（1~2秒），模拟真实心跳
        time.sleep(random.uniform(1, 2))

    client.disconnect()
    client.loop_stop()

def run_concurrent_load(device_ids, product_id, duration=60):
    """并发执行压测，返回 (LoadStats, 实际耗时秒)"""
    stats = LoadStats()
    threads = []
    start_time = time.perf_counter()
    for did in device_ids:
        t = threading.Thread(target=device_worker, args=(did, product_id, duration, stats))
        threads.append(t)
        t.start()
        time.sleep(0.01)  # 错开启动，避免瞬间冲击

    for t in threads:
        t.join()
    end_time = time.perf_counter()
    actual_duration = end_time - start_time
    return stats, actual_duration

# ---------- 测试用例 ----------
@pytest.mark.slow
def test_mqtt_concurrent_load(batch_devices_for_load, scene_with_device_access):
    device_ids = batch_devices_for_load
    product_id = scene_with_device_access['product_id']
    assert len(device_ids) == 100, f"设备数量不符，期望100，实际{len(device_ids)}"

    stats, actual_dur = run_concurrent_load(device_ids, product_id, duration=60)
    summary = stats.summary()

    tps = summary['success'] / actual_dur if actual_dur > 0 else 0

    # 打印报告（与之前相同）
    print("\n" + "="*60)
    print("MQTT 多线程压测结果")
    print("="*60)
    print(f"实际测试时长: {actual_dur:.2f} s")
    print(f"总请求数: {summary['total']}")
    print(f"成功: {summary['success']}  失败: {summary['failure']}")
    print(f"平均吞吐量 (TPS): {tps:.2f} 次/秒")
    if summary['success'] > 0:
        print(f"平均延迟: {summary['avg_latency']:.2f} ms")
        print(f"P50 延迟: {summary['p50']:.2f} ms")
        print(f"P95 延迟: {summary['p95']:.2f} ms")
        print(f"P99 延迟: {summary['p99']:.2f} ms")
        print(f"最大延迟: {summary['max']:.2f} ms")

    # 断言
    assert summary['failure'] == 0, f"存在 {summary['failure']} 次失败"
    if summary['success'] > 0:
        assert summary['avg_latency'] < 200, f"平均延迟过高: {summary['avg_latency']:.2f} ms"
    else:
        pytest.fail("无成功请求，无法计算延迟")

    # 可选图表
    if summary['latencies']:
        _attach_latency_chart(summary['latencies'])

    perf_data = {
        "test_duration_seconds": round(actual_dur, 2),
        "total_requests": summary['total'],
        "success": summary['success'],
        "failure": summary['failure'],
        "tps": round(tps, 2),
        "avg_latency_ms": round(summary['avg_latency'], 2) if summary['avg_latency'] else None,
        "p50_ms": round(summary['p50'], 2) if summary['p50'] else None,
        "p95_ms": round(summary['p95'], 2) if summary['p95'] else None,
        "p99_ms": round(summary['p99'], 2) if summary['p99'] else None,
        "max_latency_ms": round(summary['max'], 2) if summary['max'] else None,
    }
    allure.attach(
        json.dumps(perf_data, indent=2, ensure_ascii=False),
        name="MQTT压测指标 (JSON)",
        attachment_type=allure.attachment_type.JSON,
    )

def _attach_latency_chart(latencies):
    """辅助函数：生成直方图并附加到 Allure"""
    if not latencies:
        return
    try:
        import matplotlib.pyplot as plt
        import io

        plt.figure()
        plt.hist(latencies, bins=30, alpha=0.7, color='skyblue')
        plt.xlabel('Latency (ms)')
        plt.ylabel('Count')
        plt.title('MQTT Publish Latency Distribution')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        allure.attach(buf.read(), 'Latency_Distribution', allure.attachment_type.PNG)
        plt.close()
    except ImportError:
        pass  # 跳过图表生成，不影响测试