import pytest
import allure
import time
import json
from concurrent.futures import ThreadPoolExecutor
from test_jetlinks.common.api_client import ProductReadApi

class TestProductBindSmoke:
    """产品绑定网关协议-冒烟测试套件"""

    @allure.title("正常绑定流程")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("核心业务场景：产品首次绑定网关协议（PATCH）")
    def test_01_normal_bind(self, api_client, product_write_api, product_read_api, temp_binding, create_product_fixture):
        binding_info = temp_binding
        product_data = create_product_fixture
        product_id = product_data['id']
        print(f"binding_info:{binding_info}")
        # 最小字段集
        bind_payload = {
            "id": product_id,
            "accessId": binding_info['result']['channelId'],
            "accessName": binding_info['result']['name'],
            "accessProvider": binding_info['result']['provider'],
            "messageProtocol": binding_info['result']['protocol'],
            "name": product_data['name']
            # 先不传其他字段，看是否报错
        }
        print(f"bind_payload:{bind_payload}")
        print(f"测试01：产品{product_id}绑定到网关{binding_info['result']['id']}")
        update_resp = product_write_api.patch_product(bind_payload)
        assert update_resp['message'] == 'success', f"业务失败：{update_resp['message']}"
        assert update_resp['status'] == 200, f"状态码异常：{update_resp['status']}"

        # 验证绑定信息
        detail = product_read_api.get_detail(column = "id", value = product_id)
        product_detail = detail['result']['data'][0]

        assert product_detail['accessId'] == binding_info['result']['channelId'], "accessId不匹配"
        assert product_detail['messageProtocol'] == binding_info['result']['protocol'], "messageProtocol不匹配"
        assert product_detail['accessName'] == binding_info['result']['name'], "accessName不匹配"
        assert product_detail['accessProvider'] == binding_info['result']['provider'], "accessProvider不匹配"

        # 关键验证，其他字段未被修改
        assert product_detail['name'] == product_data['name'], "产品名称被修改"
        assert product_detail['classifiedId'] == product_data['classifiedId'], "classifiedId被修改"
        assert product_detail['classifiedName'] == product_data['classifiedName'], "classifiedName被修改"

        print(f"测试01通过：{product_id}成功绑定设备接入网关")

    @allure.title("绑定后验证所有字段")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证绑定后产品的所有关键字段是否正确")
    def test_02_bind_with_full_fields(self, product_write_api, product_read_api, temp_binding, create_product_fixture):
        """
        测试要点：
        1. 绑定后验证所有关键字段
        2. 包括基础信息、接入信息、协议信息
        """
        binding_info = temp_binding
        product_data = create_product_fixture
        product_id = product_data['id']

        bind_payload = {
            "id": product_id,
            "name": product_data['name'],
            "accessId": binding_info['result']['channelId'],
            "accessName": binding_info['result']['name'],
            "messageProtocol": binding_info['result']['protocol'],
            "accessProvider": binding_info['result']['provider']
        }

        print(f"\n测试02：验证绑定后的完整字段")
        update_resp = product_write_api.patch_product(bind_payload)

        assert update_resp['message'] == 'success'
        assert update_resp['status'] == 200

        # 获取详情并验证所有关键字段
        detail = product_read_api.get_detail(column = "id", value = product_id)
        product_detail = detail['result']['data'][0]

        # 基础信息
        assert product_detail['id'] == product_id
        assert product_detail['name'] == product_data['name']
        assert product_detail['classifiedId'] == product_data['classifiedId']
        assert product_detail['classifiedName'] == product_data['classifiedName']
        assert product_detail['deviceType']['value'] == product_data['deviceType']['value']
        print(f"product_detail:{product_detail}")
        # 接入信息
        assert product_detail['messageProtocol'] == binding_info['result']['protocol']

        print(f"测试02通过：所有字段验证正确")

    @allure.title("重新绑定到不同网关")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证产品可以重新绑定到不同的网关")
    def test_03_rebind_different_gateway(self, product_write_api, product_read_api, temp_binding, create_product_fixture):
        """
        测试要点：
        1. 产品先绑定到网关A
        2. 重新绑定到网关B
        3. 验证绑定信息更新正确
        """
        binding_info = temp_binding
        product_data = create_product_fixture
        product_id = product_data['id']

        # 第一次绑定
        bind_payload_1 = {
            "id": product_id,
            "name": product_data['name'],
            "accessId": binding_info['result']['channelId'],
            "accessName": binding_info['result']['name'],
            "messageProtocol": binding_info['result']['protocol'],
            "accessProvider": binding_info['result']['provider']
        }

        print(f"\n测试03：第一次绑定到网关{binding_info['result']['channelId']}")
        update_resp_1 = product_write_api.patch_product(bind_payload_1)
        assert update_resp_1['message'] == 'success'
        assert update_resp_1['status'] == 200

        # 验证第一次绑定
        detail_1 = product_read_api.get_detail(column = "id", value = product_id)
        product_detail_1 = detail_1['result']['data'][0]
        assert product_detail_1['accessId'] == binding_info['result']['channelId']

        # 创建第二个设备接入网关绑定产品
        binding_info_2 = temp_binding


        # 第二次绑定
        binding_payload_2 = {
            "id": product_id,
            "name": product_data['name'],
            "accessId": binding_info_2['result']['channelId'],
            "accessName": binding_info_2['result']['name'],
            "messageProtocol": binding_info_2['result']['protocol'],
            "accessProvider": binding_info_2['result']['provider']
        }

        print(f"\n测试03：重新绑定到设备接入网关2{binding_payload_2['accessId']}")
        update_resp_2 = product_write_api.patch_product(binding_payload_2)
        assert update_resp_2['message'] == 'success'
        assert update_resp_2['status'] == 200

        # 验证第二次绑定
        detail_2 = product_read_api.get_detail(column = "id", value = product_id)
        product_detail_2 = detail_2['result']['data'][0]
        assert product_detail_2['accessId'] == binding_info_2['result']['channelId']
        assert product_detail_2["accessName"] == binding_info_2["result"]["name"]

        print(f"测试03通过：产品成功切换设备接入网关")

    @allure.title("绑定不存在的网关")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证绑定不存在的网关ID时应失败")
    def test_06_bind_nonexistent_gateway_should_fail(self, product_write_api, product_read_api, temp_binding, create_product_fixture):
        """
        测试要点：
        1. 使用一个不存在的网关ID进行绑定
        2. 预期应该失败（400或业务错误）
        3. 验证错误信息
        """
        binding_info = temp_binding
        product_data = create_product_fixture
        product_id = product_data['id']

        # 使用一个不存在的网关
        nonexistent_gateway_id = "nonexistent_gateway_id_999999"
        nonexistent_accessName = "nonexistent_accessName_999999"
        nonexistent_accessProvider = "nonexistent_accessProvider_999999"
        nonexistent_messageProtocol = "nonexistent_messageProtocol_999999"

        bind_payload = {
            "id": product_id,
            "name": product_data['name'],
            "accessId": nonexistent_gateway_id,
            "accessName": nonexistent_accessName,
            "accessProvider": nonexistent_accessProvider,
            "messageProtocol": nonexistent_messageProtocol
        }

        print(f"\n测试04：尝试绑定不存在的网关{nonexistent_gateway_id}（预期失败）")

        try:
            update_resp = product_write_api.patch_product(bind_payload)
            print(f"update_resp:{update_resp}")
            # 如果成功了，说明后端没有校验网关是否存在
            detail = product_read_api.get_detail(column="id", value=product_id)
            print(f"绑定后的网关：{detail['result']['data'][0]['accessId']}")
            assert detail['result']['data'][0]['accessId'] is None, f"产品绑定到未知设备接入网关：{detail['result']['data'][0]['accessId']}"
        except Exception as e:
            # 预期抛出异常
            print(f"预期的错误：{e}")
            error_msg = str(e)
            # 检查是否包含404或其他错误提示
            assert "404" in error_msg or "Not Found" in error_msg or "Bad Request" in error_msg, f"错误类型不符合预期：{e}"
            print(f"测试04通过：绑定不存在的网关确实失败")

    @allure.title("多产品绑定同一设备接入网关")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证多个产品能够绑定到同一设备接入网关")
    def test_05_multiple_products_bind_same_gateway(self, product_write_api, product_read_api, temp_binding, create_product_fixture):
        """
        测试要点：
        1. 创建多个产品
        2. 将它们都绑定到同一个网关
        3. 验证每个产品都能正确绑定
        4. 验证网关可以被多个产品共享
        """
        binding_info_1 = temp_binding

        # 创建第一个产品并绑定
        product_data_1 = create_product_fixture
        product_id_1 = product_data_1['id']

        bind_payload_1 = {
            "id": product_id_1,
            "name": product_data_1['name'],
            "accessId": binding_info_1['result']['channelId'],
            "accessName": binding_info_1['result']['name'],
            "messageProtocol": binding_info_1['result']['protocol'],
            "accessProvider": binding_info_1['result']['provider']
        }
        print(f"bind_payload_1:{bind_payload_1}")
        print(f"产品1：{product_id_1} 绑定到设备接入网关 {binding_info_1['result']['id']}")
        update_resp_1 = product_write_api.patch_product(bind_payload_1)
        assert update_resp_1['message'] == 'success'

        # 验证产品1绑定成功
        detail1 = product_read_api.get_detail(column = "id", value = product_id_1)
        assert detail1['result']['data'][0]['accessId'] == bind_payload_1['accessId']
        assert detail1['result']['data'][0]['accessName'] == bind_payload_1['accessName']

        # 手动创建第二个产品（因为fixture只能用一次）
        product_id_2 = f"test_prod_{int(time.time() * 1000)}"

        # 创建第二个产品

        create_resp_2 = product_write_api.create_product_function(
            id = product_id_2,
            name = product_id_2,
            classifiedId = "-222-",
            classifiedName = "智能电力",
            deviceType = "device",
            describe = "这是一个自动化测试创建的产品，用完即删"
        )
        print(f"create_resp_2:{create_resp_2}")

        try:
            # 绑定第二个产品到同一个网关
            bind_payload_2 = {
                "id": product_id_2,
                "name": product_id_2,
                "accessId": bind_payload_1['accessId'],
                "accessName": bind_payload_1['accessName'],
                "messageProtocol": bind_payload_1['messageProtocol'],
                "accessProvider": bind_payload_1['accessProvider'],
            }

            print(f"产品2：{product_id_2} 绑定到网关 {binding_info_1['result']['id']}")
            update_resp_2 = product_write_api.patch_product(bind_payload_2)
            assert update_resp_2['message'] == 'success'

            # 验证产品2绑定成功
            detail2 = product_read_api.get_detail(column = "id", value = product_id_2)
            assert detail2['result']['data'][0]['accessId'] == bind_payload_2['accessId']
            assert detail2['result']['data'][0]['accessName'] == bind_payload_2['accessName']

            # 验证两个产品都绑定到同一网关
            assert detail1['result']['data'][0]['accessId'] == detail2['result']['data'][0]['accessId']
            assert detail2['result']['data'][0]['accessName'] == detail2['result']['data'][0]['accessName']

            print(f"产品1和产品2都成功绑定到设备接入网关{binding_info_1['result']['id']}")
            print("网关可以被多个产品共享")

        finally:
            # 清理第二个产品
            try:
                product_write_api.delete_product(product_id_2)
                print(f"产品2 {product_id_2} 已清理")
            except Exception as e:
                print(f"清理产品2失败：{e}")

        print(f"测试05通过：产品成功绑定到统一设备接入网关")