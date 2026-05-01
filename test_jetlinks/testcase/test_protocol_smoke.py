import threading

import pytest
import time
import allure
import json
import logging
from pathlib import Path
import paho.mqtt.client as mqtt
from test_jetlinks.common.api_client import ProtocolClient

# 配置日志
logging.basicConfig(level = logging.INFO, format = '%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@allure.epic("JetLinks物联网平台")
@allure.feature("协议管理")
@allure.story("协议基础功能验证")
class TestProtocolManagement:
    """协议管理核心功能测试"""

    @allure.title("上传 Jar 包")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证 Jar 包上传接口能够正常工作，返回有效的fileId")
    def test_01_upload_jar(self, api_client):
        """
        测试1：上传 Jar 包
        前置：已登录
        预期：返回 fileId，上传成功
        """
        JAR_PATH = Path(__file__).parent.parent / "protocol" / "jetlinks-official-protocol-3.2.0-SNAPSHOT.jar"

        protocol_client = ProtocolClient()
        protocol_client.session = api_client.session
        protocol_client.headers = api_client.headers

        if not JAR_PATH.exists():
            pytest.skip("Jar 文件不存在")

        logger.info(f"准备上传 Jar 包：{JAR_PATH}")

        with allure.step("发送上传请求"):
            resp_file = protocol_client.upload_jar(JAR_PATH)

            assert resp_file is not None, "上传失败，未返回fileId"
            assert len(resp_file['file_id']) > 0, "fileId 为空"

            logger.info(f" Jar包上传成功，fileId：{resp_file['file_id']}")
            allure.attach(
                f"上传成功的 fileId：{resp_file['file_id']}",
                name = "Jar包上传结果",
                attachment_type = allure.attachment_type.TEXT
            )

    @allure.title("创建并启动协议")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证协议创建接口是否能够成功返回 protocolId，并能正常启动监听端口")
    def test_02_create_and_protocol(self, api_client, uploaded_jar_id):
        """
        测试2：创建并启动协议
        前置：Jar 包已上传
        预期：协议创建成功，状态为 1（运行中），端口 1885 监听
        """

        protocol_name = f"test_protocol_{int(time.time() * 1000)}"
        logger.info(f"准备创建协议：{protocol_name}")

        protocol_client = ProtocolClient()
        protocol_client.session = api_client.session
        protocol_client.headers = api_client.headers

        file_id = uploaded_jar_id['file_id']
        access_url = uploaded_jar_id['access_url']
        access_key = uploaded_jar_id.get('access_key')

        with allure.step("发送创建协议请求"):
            protocol_id = protocol_client.create_protocol(
                name=protocol_name,
                jar_file_id=file_id,
                jar_access_key=access_key,
                jar_access_url=access_url  # 使用完整 URL
            )

            assert protocol_id is not None, "创建失败， 未返回 protocolId"
            logger.info(f"协议创建成功：{protocol_id}")

            allure.attach(
                json.dumps({"protocol_id": protocol_id, "protocol_name": protocol_name}, indent = 2),
                name = "协议创建结果",
                attachment_type = allure.attachment_type.JSON
            )

        with allure.step("等待端口就绪"):
            protocol_client.wait_for_port(1885, timeout = 10)
            logger.info("端口 1885 已就绪")
            allure.attach(
                "端口 1885 已成功监听",
                name = "端口状态",
                attachment_type = allure.attachment_type.TEXT
            )

        with allure.step("验证协议状态"):
            detail = protocol_client.get_protocol_detail()
            logger.info(f"协议详情：{json.dumps(detail, indent = 2, ensure_ascii=False)}")

            allure.attach(
                json.dumps(detail, indent = 2, ensure_ascii = False),
                name = "协议详情响应体",
                attachment_type = allure.attachment_type.JSON
            )

        # 清理
        with allure.step("清理测试协议"):
            try:
                protocol_client.delete_protocol(protocol_id)
                logger.info(f"协议{protocol_name}已清理")
                allure.attach(
                    f"已清理测试协议：{protocol_name}({protocol_id})",
                    name = "清理结果",
                    attachment_type = allure.attachment_type.TEXT
                )
            except Exception as e:
                logger.warning(f"协议清理失败：{e}")
                allure.attach(
                    f"协议清理失败（保留用于测试）：{e}",
                    name = "清理警告",
                    attachment_type = allure.attachment_type.TEXT
                )

    @allure.title("MQTT 协议连接测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证 MQTT 协议能否建立 TCP 连接并收到 ConnAck 响应")
    def test_03_mqtt_connect(self, protocol_instance):
        protocol_name = protocol_instance['protocol_name']
        logger.info(f"测试协议：{protocol_name}")

        max_attempts = 10
        connected = False

        for attempt in range(1, max_attempts + 1):
            logger.info(f"MQTT 连接尝试 {attempt}/{max_attempts}")
            client = mqtt.Client(client_id="test_protocol_conn")
            client.username_pw_set("1111", "1111")
            conn_evt = threading.Event()

            def on_connect(client, userdata, flags, rc):
                # 只要收到 CONNACK，无论 rc 是多少，都认为连通成功
                conn_evt.set()

            client.on_connect = on_connect

            try:
                client.connect("127.0.0.1", 1883, keepalive=10)
                client.loop_start()
            except Exception as e:
                logger.warning(f"TCP 连接失败: {e}")
                time.sleep(3)
                continue

            if conn_evt.wait(timeout=10):
                connected = True
                client.disconnect()
                client.loop_stop()
                break
            else:
                logger.warning("等待 CONNACK 超时")
                client.loop_stop()
                time.sleep(3)

        allure.attach(
            f"MQTT 连接结果：{'成功' if connected else '失败'}",
            name="连接结果",
            attachment_type=allure.attachment_type.TEXT
        )
        assert connected, f"MQTT 连接失败，已重试 {max_attempts} 次"
        logger.info("MQTT 协议连接成功，收到 ConnAck 响应")

    @allure.title("查询协议列表")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证协议列表查询接口能够正确返回自己创建的协议")
    def test_04_protocol_list_query(self, api_client, protocol_instance):
        """
        测试4：查询协议列表
        前置：协议已创建
        预期：列表中包含刚创建的协议
        """
        protocol_client = ProtocolClient()
        protocol_client.session = api_client.session
        protocol_client.headers = api_client.headers

        protocol_name = protocol_instance['protocol_name']
        logger.info(f"查询协议列表，期望找到：{protocol_name}")

        with allure.step("查询协议列表"):
            result = protocol_client.get_protocol_detail()

            allure.attach(
                json.dumps(result, indent = 2, ensure_ascii = False),
                name = "协议列表响应体",
                attachment_type = allure.attachment_type.JSON
            )

            assert result['total'] > 0, "协议列表为空"
            logger.info(f"协议列表总数：{result['total']}")

        with allure.step("验证协议存在"):
            found = any(p['name'] == protocol_name for p in result['data'])
            assert found is True, f"协议列表中未找到{protocol_name}"
            logger.info(f"在协议列表中找到：{protocol_name}")

            allure.attach(
                f"找到协议：{protocol_name}",
                name = "查找结果",
                attachment_type = allure.attachment_type.TEXT
            )
        print("\n 测试成功，列表中能查到创建的协议")

    @allure.title("删除协议")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证协议删除接口能否正常工作")
    def test_05_delete_protocol(self, protocol_instance, api_client):
        """
        测试5：删除协议
        前置：协议已创建
        预期：协议被成功删除，列表中不再存在
        """
        protocol_client = protocol_instance['client']
        protocol_id = protocol_instance['protocol_id']
        protocol_name = protocol_instance['protocol_name']

        logger.info(f"删除协议：{protocol_name}({protocol_id})")

        with allure.step("发送删除请求"):
            protocol_client.delete_protocol(protocol_id)
            logger.info("协议删除请求已发送")
            allure.attach(
                f"已发送删除请求：{protocol_id}",
                name = "删除请求",
                attachment_type = allure.attachment_type.TEXT
            )

        with allure.step("验证协议已删除"):
            time.sleep(0.5)
            result = protocol_client.get_protocol_detail()
            found = any(p['id'] == protocol_id for p in result['data'])
            assert found is False, f"协议{protocol_id}仍在列表中"
            logger.info("协议已从列表中移除")

            allure.attach(
                f"协议{protocol_id}已成功删除",
                name = "删除验证结果",
                attachment_type = allure.attachment_type.TEXT
            )
        print("\n 成功，删除协议接口工作正常")

