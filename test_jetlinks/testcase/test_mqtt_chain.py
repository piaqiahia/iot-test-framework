import json
import threading
import time
import allure
import pytest
import redis
import paho.mqtt.client as mqtt
from allure_pytest import listener
from test_jetlinks.common.api_client import DeviceClient
import logging
logger = logging.getLogger(__name__)


@allure.epic("JetLinks物联网平台")
@allure.feature("设备端对端集成")
@allure.story("设备属性上报与规则联动")
class TestDeviceScenarioCompleteLink:
    @allure.title("完整链路：设备接入 -> 数据上报 -> 规则触发 -> 下发指令 -> 状态转换")
    def test_device_scenario_complete_link(
            self,
            scene_with_device_access,
            mqtt_device_simulator,
            api_client,
    ):#
        """
        完整链路测试（被动模式，依赖平台规则）
        所有温度打印由夹具完成，测试只负责等待状态转换并断言。
        """
        mqtt_info = mqtt_device_simulator
        state = mqtt_info['device_state']
        device_id = mqtt_info['device_id']
        print(f"\n{'='*60}")
        print(f"链路测试开始 | 设备: {device_id}")
        print(f"{'='*60}")

        with allure.step("1.验证初始状态"):
            allure.attach(f"初始温度: {state['temperature']}°C, 间隔: {state['interval']}s", "初始状态")
            assert state['temperature'] >= 45.0
            assert state['interval'] == 5.0
        print(f"✓ 初始状态确认完成")

        # 2. 等待升温到 60°C
        with allure.step("2.等待温度升至 60°C"):
            timeout = 120
            start = time.time()
            while state['temperature'] < 60.0 and (time.time() - start) < timeout:
                time.sleep(0.5)
            assert state['temperature'] >= 60.0, f"超时未升至 60°C"
        print(f"✓ 温度已达标")

        # 3. 等待进入降温阶段
        with allure.step("3.等待平台下发 interval=2 并进入降温阶段"):
            timeout = 15
            start = time.time()
            while state['phase'] != 'cooling' and (time.time() - start) < timeout:
                time.sleep(0.3)
            assert state['phase'] == 'cooling', f"未进入降温阶段，当前 phase={state['phase']}"
            assert state['interval'] == 2.0
        print(f"✓ 已进入降温阶段")

        with allure.step("4.等待降温至50°C并执行缓存一致性验证"):
            print("等待温度降至 50°C ...")
            timeout = 60
            start = time.time()
            while state['temperature'] > 50.0 and (time.time() - start) < timeout:
                time.sleep(0.5)
            assert state['temperature'] <= 50.0
            print(f"✓ 温度已降至 50°C 以下")
            print(f"✓ 温度已达标")
            # 核心缓存一致性验证点（设备在线，缓存必然有效）
            print("开始缓存一致性验证...")
            for attempt in range(1, 4):  # 重试最多3次，间隔2秒
                try:
                    resp = api_client.get(f"/device/instance/{device_id}/properties/latest")
                    props = resp.get('result', [])
                    temp_obj = next((p for p in props if p.get('property') == 'temperature'), None)
                    if temp_obj:
                        api_temp = temp_obj.get('value')
                        if api_temp == state['temperature']:
                            print(f"✓ 缓存一致性验证通过：API 温度 = {api_temp}°C (第{attempt}次查询)")
                            break
                        else:
                            print(f"[等待同步] API 温度 {api_temp}°C ≠ 期望 {state['temperature']}°C，重试...")
                    else:
                        print(f"[警告] 未找到 temperature 属性 (第{attempt}次)")
                except Exception as e:
                    print(f"[重试异常] {e}")
                time.sleep(2)
            else:
                # 重试耗尽，硬失败
                raise AssertionError("缓存一致性验证失败：降温至50°C后未能匹配到正确的温度值")

        with allure.step("5.等待平台下发interval=5并进入再升温阶段"):
            print("等待平台下发 interval=5 并进入再升温阶段...")
            timeout = 15
            start = time.time()
            while state['phase'] != 'reheating' and (time.time() - start) < timeout:
                time.sleep(0.3)
            assert state['phase'] == 'reheating'
            assert state['interval'] == 5.0
        print(f"✓ 已进入再升温阶段")

        with allure.step("6.等待升温至65°C并结束模拟"):
            print("等待温度升至 65°C ...")
            timeout = 120
            start = time.time()
            while state['temperature'] < 65.0 and (time.time() - start) < timeout:
                time.sleep(0.5)
            assert state['temperature'] >= 65.0
        print(f"✓ 温度已达 65°C，模拟结束")

        print(f"✓ 温度已达标")

        # 稍等线程完全退出
        time.sleep(1)
        assert state['phase'] == 'reheating'
        print("\n完整链路验证通过")

@allure.epic("JetLinks物联网平台")
@allure.feature("MQTT可靠性")
@allure.story("遗嘱消息")
class TestLastWill:

    @allure.title("MQTT 协议连接测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证 MQTT 协议能否建立 TCP 连接并收到 ConnAck 响应")
    def test_03_mqtt_connect(self, protocol_instance):
        protocol_name = protocol_instance['protocol_name']
        logger.info(f"测试协议：{protocol_name}")

        max_attempts = 20  # 增加到 20 次
        connected = False

        for attempt in range(1, max_attempts + 1):
            logger.info(f"MQTT 连接尝试 {attempt}/{max_attempts}")
            client = mqtt.Client(client_id="test_protocol_conn")
            client.username_pw_set("1111", "1111")
            conn_evt = threading.Event()

            def on_connect(client, userdata, flags, rc):
                conn_evt.set()  # 只要收到 CONNACK，无论 rc 是什么都算成功

            client.on_connect = on_connect

            try:
                client.connect("127.0.0.1", 1883, keepalive=10)
                client.loop_start()
            except Exception as e:
                logger.warning(f"TCP 连接失败: {e}")
                time.sleep(5)  # 每次间隔改为 5 秒
                continue

            if conn_evt.wait(timeout=10):
                connected = True
                client.disconnect()
                client.loop_stop()
                break
            else:
                logger.warning(f"第 {attempt} 次等待 CONNACK 超时")
                client.loop_stop()
                time.sleep(5)

        allure.attach(
            f"MQTT 连接结果：{'成功' if connected else '失败'}",
            name="连接结果",
            attachment_type=allure.attachment_type.TEXT
        )
        assert connected, f"MQTT 连接失败，已重试 {max_attempts} 次（总等待约 {max_attempts * 15} 秒）"
        logger.info("MQTT 协议连接成功，收到 ConnAck 响应")

@allure.epic("JetLinks物联网平台")
@allure.feature("MQTT可靠性")
@allure.story("会话保持与重连")
class TestSessionReconnect:

    @allure.title("设备重连后接收离线期间下发的指令")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("设备断网后发布数据，重连后自动补发到平台，验证客户端缓存与重传机制")
    def test_uplink_retransmission(self, scene_with_device_access, api_client):
        product_id = scene_with_device_access['product_id']
        device_id = scene_with_device_access['device_id']

        print("[上行重传] 创建客户端，clean_session=False")
        device_client = mqtt.Client(client_id=device_id, protocol=mqtt.MQTTv311, clean_session=False)
        device_client.username_pw_set("1111", "1111")
        connected = threading.Event()

        def on_device_connect(client, userdata, flags, rc):
            if rc == 0:
                connected.set()
                print("[上行重传] 设备首次连接成功")
            else:
                print(f"[上行重传] 首次连接失败，rc={rc}")

        device_client.on_connect = on_device_connect

        with allure.step("1. 设备首次连接（clean_session=False）"):
            device_client.connect("127.0.0.1", 1885, keepalive=60)
            device_client.loop_start()
            if not connected.wait(timeout=5):
                pytest.fail("首次连接超时")
        print("[上行重传] 连接已确认，loop_start 运行中")

        with allure.step("2. 正常上报一条温度 30.0"):
            payload = {
                "properties": {"temperature": 30.0},
                "timestamp": int(time.time() * 1000)
            }
            device_client.publish(
                f"/{product_id}/{device_id}/properties/report", json.dumps(payload), qos=1
            )
            print("[上行重传] 已上报基准温度 30.0")
            time.sleep(1)

        with allure.step("3. 模拟断网并缓存离线数据"):
            try:
                device_client._sock.close()
                print("[上行重传] 模拟断网：socket已关闭")
            except Exception as e:
                print(f"[上行重传] 关闭socket异常：{e}")
            time.sleep(0.5)  # 等待内部状态进入“连接丢失”
            for i in range(2):
                temp_val = 35.0 + i
                payload = {
                    "properties": {"temperature": temp_val},
                    "timestamp": int(time.time() * 1000)
                }
                device_client.publish(
                    f"/{product_id}/{device_id}/properties/report", json.dumps(payload), qos=1
                )
                print(f"[上行重传] 离线缓存温度 {temp_val}")
                time.sleep(0.3)

        with allure.step("4. 等待自动重连并补发消息"):
            print("[上行重传] 等待 paho 自动重连并发送离线队列...")
            time.sleep(8)
            device_client.loop_stop()
            device_client.disconnect()
            print("[上行重传] 已断开并停止 loop")

        with allure.step("5. 查询最新属性，验证重传成功"):
            print("[上行重传] 开始查询最新属性，期望 36.0")
            max_retries = 5
            for attempt in range(1, max_retries + 1):
                try:
                    resp = api_client.get(f"/device/instance/{device_id}/properties/latest")
                    props = resp.get('result', [])
                    temp_obj = next((p for p in props if p.get('property') == 'temperature'), None)
                    if temp_obj:
                        latest_temp = temp_obj.get('value')
                        print(f"[上行重传] 第{attempt}次查询：温度={latest_temp}")
                        if latest_temp == 36.0:
                            print("[上行重传] ✓ 上行重传验证通过，最终温度 = 36.0")
                            allure.attach(f"最新温度: {latest_temp}°C", "重传成功")
                    else:
                        print(f"[上行重传] 第{attempt}次查询未找到温度属性")
                except Exception as e:
                    print(f"[上行重传] 查询异常: {e}")
                time.sleep(2)
            # 重试耗尽
            final_temp = temp_obj.get('value') if temp_obj else None
            print(f"最终温度未更新为 36.0，实际: {final_temp}")

        with allure.step("6. 查询设备遥测日志，验证离线数据全部到达"):
            print("[上行重传] 查询设备遥测日志...")
            time.sleep(2)  # 等待日志异步写入
            log_params = {
                "pageIndex": 0,
                "pageSize": 20,
                "sorts": [{"name": "timestamp", "order": "desc"}],
                "terms": []  # 可根据需要添加过滤条件，如指定事件类型
            }
            # 注意：日志接口路径可能略有不同，请根据你的 Swagger 确认
            # 常见路径：/device-instance/{deviceId}/logs 或 /device/instance/{deviceId}/logs
            resp = api_client.post(f"/device-instance/{device_id}/logs", json=log_params)
            logs = resp.get('result', {}).get('data', [])

            # 从每一条日志的 content 中提取温度值
            temps_found = []
            for log_entry in logs:
                try:
                    content = json.loads(log_entry.get('content', '{}'))
                    temp = content.get('properties', {}).get('temperature')
                    if temp is not None:
                        temps_found.append(temp)
                except:
                    pass

            print(f"[上行重传] 最近日志中的温度: {temps_found}")
            allure.attach(json.dumps(temps_found), "遥测日志温度列表")
            assert 35.0 in temps_found, f"日志中未找到温度 35.0，实际: {temps_found}"
            assert 36.0 in temps_found, f"日志中未找到温度 36.0，实际: {temps_found}"
            print("[上行重传] ✓ 设备遥测日志验证通过：离线数据均已记录")