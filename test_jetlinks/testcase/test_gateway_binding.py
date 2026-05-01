from pydoc import describe

import pytest
import time
import allure
import json
from typing import Dict

@allure.epic("JetLinks物联网平台")
@allure.story("网关协议绑定功能")
@allure.feature("绑定体管理模块")
class TestGatewayDeviceBinding:

    @allure.title("正常创建网关协议绑定")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证创建网关协议绑定的基本功能")
    def test_01_create_gateway_binding(self, api_client, binding_client, create_mqtt_gateway, protocol_instance):
        """
        测试：创建网关协议绑定
        核心：验证绑定创建成功并包含正确信息
        """
        channel_id = create_mqtt_gateway
        protocol_id = protocol_instance['protocol_id']

        unique_name = f"test_binding_{int(time.time() * 1000)}"

        with allure.step("创建网关协议绑定"):
            created_binding = binding_client.create_binding(
                name = unique_name,
                protocol_id = protocol_id,
                channel_id = channel_id,
                transport = "MQTT",
                description = "自动化测试创建的绑定体"
            )

            allure.attach(
                json.dumps(created_binding, indent = 2, ensure_ascii = False),
                name = "创建响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert created_binding['status'] == 200
            assert created_binding['result']['id'] is not None
            assert created_binding['result']['name'] == unique_name
            assert created_binding['result']['protocol'] == protocol_id
            assert created_binding['result']['channelId'] == channel_id

            binding_id = created_binding['result']['id']
            print(f"创建绑定成功：ID = {binding_id}, Name = {unique_name}")

        with allure.step("验证绑定已持久化"):
            detail = binding_client.get_binding_details(binding_id)
            assert detail is not None
            assert detail['name'] == unique_name
            assert detail['protocol'] == protocol_id
            assert detail['channelId'] == channel_id
            print(f"验证绑定详情通过")

        with allure.step("禁用绑定"):
            # 先禁用绑定
            disable_resp = binding_client.disable_binding(binding_id)
            assert disable_resp is not None
            assert disable_resp['status'] == 200
            assert disable_resp['message'] == 'success'
            print(f"绑定{binding_id}已禁用")

        with allure.step("删除绑定"):
            # 再删除绑定
            delete_resp = binding_client.delete_binding(binding_id)
            assert delete_resp is not None
            assert delete_resp['status'] == 200
            assert delete_resp['message'] == 'success'
            print(f"绑定{binding_id}已禁用")

        with allure.step("验证绑定已删除"):
            detail_after_delete = binding_client.get_binding_details(binding_id)
            assert detail_after_delete is None, f"绑定{binding_id}删除后仍可查到"

            bindings_list = binding_client.list_bindings()['result']['data']
            found = any(b.get('id') == binding_id for b in bindings_list)
            assert not found, f"绑定{binding_id}仍在列表中"
            print(f"绑定删除验证通过")

    @allure.title("查询绑定列表并验证")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证创建的绑定体出现在列表中")
    def test_02_list_bindings_contains_created(self, binding_client, create_mqtt_gateway, protocol_instance):
        """
        测试：验证绑定在列表中正确显示
        """
        channel_id = create_mqtt_gateway
        protocol_id = protocol_instance['protocol_id']

        # 先创建一个绑定
        binding_name = f"test_binding_list_{int(time.time() * 1000)}"
        created_binding = binding_client.create_binding(
            name = binding_name,
            protocol_id = protocol_id,
            channel_id = channel_id,
            transport = "MQTT",
            description = "这是一个自动化测试创建的绑定体"
        )
        binding_id = created_binding['result']['id']

        with allure.step("查询绑定列表"):
            binding_list = binding_client.list_bindings()

            allure.attach(
                json.dumps(binding_list, indent = 2, ensure_ascii = False),
                name = "列表查询响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert binding_list is not None
            assert len(binding_list) > 0

            # 查找创建的绑定
            found = any(b.get('id') == binding_id for b in binding_list['result']['data'])
            assert found, f"绑定 {binding_id} 未在列表中找到"

            # 验证列表中绑定的信息
            list_item = next(b for b in binding_list['result']['data'] if b.get('id') == binding_id)
            assert list_item['name'] == binding_name
            assert list_item['protocol'] == protocol_id
            assert list_item['channelId'] == channel_id

            print(f"列表验证通过：找到绑定{binding_id}")

        with allure.step("清理测试数据"):
            # 测试完成后清理
            binding_client.disable_binding(binding_id)
            binding_client.delete_binding(binding_id)

    @allure.title("绑定生命周期完整测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证绑定的完整生命周期：创建 - 查询 - 禁用 - 删除")
    def test_03_binding_full_lifecycle(self, binding_client, create_mqtt_gateway, protocol_instance):
        """
        测试：绑定完整生命周期
        """
        channel_id = create_mqtt_gateway
        protocol_id = protocol_instance['protocol_id']

        binding_name = f"test_lifecycle_{int(time.time() * 1000)}"

        with allure.step("创建绑定"):
            created_binding = binding_client.create_binding(
                name = binding_name,
                protocol_id = protocol_id,
                channel_id = channel_id,
                transport = "MQTT",
                description = "这是一个自动化测试创建的绑定体"
            )
            binding_id = created_binding['result']['id']
            assert binding_id is not None
            print(f"绑定创建成功：{binding_id}")

        with allure.step("查询绑定详情"):
            detail = binding_client.get_binding_details(binding_id)
            assert detail is not None
            assert detail['name'] == binding_name
            print(f"绑定详情查询成功")

        with allure.step("查询绑定列表"):
            binding_list = binding_client.list_bindings()['result']['data']
            found = any(b.get('id') == binding_id for b in binding_list)
            assert found
            print("绑定体在列表中找到")

        with allure.step("禁用绑定"):
            disable_resp = binding_client.disable_binding(binding_id)
            assert disable_resp is not None
            assert disable_resp['status'] == 200
            assert disable_resp['message'] == 'success'
            print("绑定已禁用")

        with allure.step("解除绑定"):
            delete_resp = binding_client.delete_binding(binding_id)
            assert delete_resp is not None
            assert delete_resp['status'] == 200
            assert delete_resp['message'] == 'success'
            print(f"绑定已删除")

        with allure.step("验证绑定被成功删除"):
            detail_after = binding_client.get_binding_details(binding_id)
            assert detail_after is  None

            binding_list_after = binding_client.list_bindings()['result']['data']
            found_after = any(b.get('id') == binding_id for b in binding_list_after)
            assert not found_after
            print("绑定删除验证通过")
        print("绑定完整生命周期测试通过！")

    @allure.title("删除不存在的绑定（异常测试）")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证删除不存在的绑定时的错误处理")
    def test_04_delete_nonexistent_binding(self, binding_client):
        """
        测试：删除不存在的绑定
        """
        fake_id = "nonexistent_binding_9999999"

        with allure.step("尝试删除不存在的绑定并捕获异常"):
            delete_resp = binding_client.delete_binding(fake_id)

            allure.attach(
                f"捕获到预期异常：{delete_resp}",
                name = "异常信息",
                attachment_type = allure.attachment_type.TEXT
            )

            # 验证异常信息包含404
            assert delete_resp['message'] != 'success'
            assert delete_resp['status'] == 404
            assert delete_resp['code'] == 'not_found'
            print(f"成功捕获到404异常：{delete_resp}")

    @allure.title("禁用不存在的绑定（异常测试）")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证禁用不存在的绑定时的错误处理")
    def test_05_disable_nonexistent_binding(self, binding_client):
        """
        测试：禁用不存在的绑定
        """
        fake_id = "nonexistent_binding_9999999"

        with allure.step("尝试禁用不存在的绑定并捕获异常"):
            disable_resp = binding_client.disable_binding(fake_id)
            print(disable_resp)
            allure.attach(
                f"捕获到预期异常：{disable_resp['message']}",
                name = "异常信息",
                attachment_type = allure.attachment_type.TEXT
            )

            # 验证异常信息包含404
            assert disable_resp['message'] != 'success'
            assert disable_resp['code'] == 'not_found'
            assert disable_resp['status'] == 404
            print(f"成功捕获到404异常：{disable_resp}")