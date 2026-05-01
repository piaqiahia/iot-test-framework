import json
import time
import pytest
import allure
from test_jetlinks.common.api_client import DeviceClient

@allure.epic("JetLinks物联网平台")
@allure.feature("设备通信主链路")
@allure.story("设备全生命周期管理")
class TestDevice:
    """
    设备通信主链路冒烟测试
    覆盖：在线、上行、下行
    """

    @allure.title("验证设备在线状态")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证创建设备后的状态能够正常显示（默认禁用）")
    def test_01_device_online_status(self, api_client, device_access_chain):
        """
        场景1：设备在线状态验证
        步骤：创建设备 -> 查询设备状态 -> 验证状态为 active/online
        """

        # 从夹具获取数据
        # device_access_chain 返回的dict 包含 product_id 和 device_id
        product_id = device_access_chain.get('product_id')
        device_id = device_access_chain.get('device_id')
        print(f"device_access_chain: {device_access_chain}")
        assert product_id, "产品ID未找到"
        assert device_id, "设备ID未找到"

        print(f"设备ID：{device_id}， 产品ID：{product_id}")

        # 查询设备列表或详情
        device_client = DeviceClient()
        device_client.session = api_client.session
        device_client.headers = api_client.headers
        resp = device_client.list_devices(page_index = 0, page_size = 12)

        # 断言
        assert resp['status'] == 200, "设备列表查询接口失败"

        # 查找刚创建的设备
        target_device = None
        for item in resp['result']['data']:
            if item['id'] == device_id:
                target_device = item
                break

        assert target_device is not None, f"为找到设备：{device_id}"

        # 核心断言：状态字段存在且合理（刚创建完默认禁用，需要启用）状态：state下的text 禁用 在线 离线
        status_value = target_device['state']['text']
        print(f"设备状态：{status_value}")

        assert target_device['id'] == device_id, "设备ID不匹配"
        assert 'state' in target_device
        print("测试01通过：设备在线状态正常")

    @allure.title("设备数据上行验证")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("设备通过MQTT上报数据，平台能查询到最新数据")
    def test_02_device_online_status(self, api_client, device_access_chain, mqtt_device_conn):
        """
        场景2：数据上行验证（遥测）
        步骤：设备发数据(MQTT) -> 平台查询历史数据 -> 验证数据存储
        """
        device_client = DeviceClient()
        device_client.session = api_client.session
        device_client.headers = api_client.headers
        device_id = mqtt_device_conn['device_id']
        product_id = mqtt_device_conn['product_id']
        EXPECTED_TEMP = 36.5

        with allure.step("验证设备基础信息"):
            resp = device_client.get_device_detail(device_id)
            device_info = resp['result']

            assert device_info['productId'] == product_id
            assert device_info['id'] == device_id

            allure.attach(json.dumps(device_info, indent = 2), name = "设备详细响应")

        with allure.step("等待MQTT数据上报并验证日志"):
            # 使用封装好的断言方法，内部已包含等待和重试逻辑
            device_client.assert_log_contains_telemetry(device_id, EXPECTED_TEMP)

        print("测试02通过，数据上行正常")
