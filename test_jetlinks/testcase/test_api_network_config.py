import logging
import pytest
from test_jetlinks.common.api_client import NetworkConfigApi
import allure
import json
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@allure.epic("JetLins物联网平台")
@allure.feature("网络配置/网关管理")
@allure.story("网关基础功能验证")
class TestNetworkConfig:
    """
    【接口功能验证测试】
    验证 NetworkConfigApi 封装的每个方法是否能正常请求、响应结构是否正确。
    不依赖复杂的业务逻辑，只测“通断”和“基础契约”。
    """

    @allure.title("正常创建MQTT网关")
    def test_01_create_mqtt_gateway_success(self, api_client):
        """
        测试点：创建网关接口是否能成功返回 200 且包含 ID
        """
        gw_api = NetworkConfigApi()
        gw_api.session = api_client.session
        gw_api.headers = api_client.headers

        # 使用随机名称避免冲突
        gw_name = f"SMOKE_TEST_{int(time.time() * 1000)}"

        logger.info(f"创建网关：{gw_name}")

        with allure.step("发送创建请求"):
            resp = gw_api.create_mqtt_gateway(name = gw_name)

            # 附加响应体到报告
            allure.attach(
                json.dumps(resp, indent = 2, ensure_ascii = False),
                name = "创建网关响应体",
                attachment_type = allure.attachment_type.JSON
            )

            # 基础校验
            print(f"resp = {resp}")
            assert resp['status'] == 200, f"期望状态200，实际{resp['status']}"
            assert resp['message'] == 'success', f"期望message == success，实际{resp['message']}"

            # 结构校验
            assert 'result' in resp, "响应缺少 result 字段"
            assert 'id' in resp['result'], "result 缺少id字段"

            gateway_id = resp['result']['id']
            logger.info(f"创建成功，Gateway ID:{gateway_id}")
            allure.attach(f"创建成功的Gateway ID:{gateway_id}",name = "网关ID", attachment_type = allure.attachment_type.TEXT)

        with allure.step("清理现场（删除网关）"):
            # 创建完成就删除避免污染数据
            delete_success = gw_api.delete_gateway(gateway_id)
            assert delete_success is True, "清理失败：删除网关失败"
            logger.info(f"已清理网关：{gateway_id}")
            allure.attach(f"已清理测试网关:{gateway_id}", name = "清理结果", attachment_type = allure.attachment_type.TEXT)

    @allure.title("成功禁用网关")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证禁用网关接口是否返回 success message")
    def test_02_shutdown_gateway_success(self, create_mqtt_gateway, api_client):
        """测试点：禁用网关接口是否返回 success message"""

        gw_api = NetworkConfigApi()
        gw_api.session = api_client.session
        gw_api.headers = api_client.headers

        gateway_id = create_mqtt_gateway
        logger.info(f"尝试禁用网关：{gateway_id}")

        with allure.step("发送禁用请求"):
            resp = gw_api.shutdown_gateway(gateway_id)

            allure.attach(
                json.dumps(resp, indent = 2, ensure_ascii = False),
                name = "禁用网关响应体",
                attachment_type = allure.attachment_type.JSON
            )

            assert resp['status'] == 200
            assert resp['message'] == 'success'
            logger.info("禁用指令发送成功")


    @allure.title("正常删除网关")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证删除网关接口能否正常工作")
    def test_03_delete_gateway_success(self, api_client, create_mqtt_gateway):
        """测试点：删除网关接口是否返回成功"""

        gw_api = NetworkConfigApi()
        gw_api.session = api_client.session
        gw_api.headers = api_client.headers

        gateway_id = create_mqtt_gateway
        logger.info(f"尝试删除网关：{gateway_id}")

        with allure.step(f"执行删除操作"):
            success = gw_api.delete_gateway(gateway_id)
            assert success is True
            logger.info("删除操作成功")

        with allure.step("验证资源已不存在"):
            with pytest.raises(Exception, match = "404|获取失败|Not Found") as exc_info:
                gw_api.get_gateway_detail(gateway_id)
            error_msg = str(exc_info.value)
            allure.attach(f"捕获到预期异常：{error_msg}", name = "删除验证异常", attachment_type = allure.attachment_type.TEXT)
            logger.info("资源已不存在")

    @allure.title("获取网关详情 - 结构验证")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证获取详情接口是否返回正确数据结构")
    def test_04_get_gateway_detail_success(self, api_client, create_mqtt_gateway):
        """测试点：获取详情接口是否返回正确的数据结构"""

        gw_api = NetworkConfigApi()
        gw_api.session = api_client.session
        gw_api.headers = api_client.headers

        gateway_id = create_mqtt_gateway
        logger.info(f"获取网关详情：{gateway_id}")

        with allure.step("获取详情"):
            resp = gw_api.get_gateway_detail(gateway_id)

            allure.attach(
                json.dumps(resp, indent = 2, ensure_ascii = False),
                name = "详情响应体",
                attachment_type = allure.attachment_type.JSON
            )

            assert resp['status'] == 200
            assert resp['message'] == 'success'

            result = resp['result']
            required_fields = ['id', 'name', 'type', 'description', 'state']
            for field in required_fields:
                assert field in result, f"详情响应缺少字段：{field}"

            assert result['id'] == gateway_id
            assert result['type'] == "MQTT_SERVER"
            assert 'port' in result['configuration']
            logger.info("详情接口返回的结构正常")

    @allure.title("删除不存在的网关 - 幂等性验证")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证删除不存在的网关ID，接口如何处理")
    def test_05_delete_nonexistent_gateway_idempotent(self, api_client):
        """测试点：删除不存在的网关ID，接口应如何处理"""

        gw_api = NetworkConfigApi()
        gw_api.session = api_client.session
        gw_api.headers = api_client.headers

        fake_id = "fake_id_9999999"
        logger.info(f"尝试删除不存在的网关：{fake_id}")

        with allure.step(f"删除不存在的资源"):
            success = gw_api.delete_gateway(fake_id)
            assert success is True
            logger.info("幂等性测试通过")

    @allure.title("创建同名网关 - 唯一性约束测试")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证创建同名网关的业务逻辑（名称可重复，ID唯一）")
    def test_06_create_gateway_with_duplicate_name(self, api_client):
        """
        测试点：创建同名网关
        业务逻辑：网关名称可以重复，系统通过内部ID区分
        验证：两次创建都成功，但返回不同的ID
        """

        gw_api = NetworkConfigApi()
        gw_api.session = api_client.session
        gw_api.headers = api_client.headers

        name = "DUPLICATE_TEST_GW"

        with allure.step("第一次创建"):
            resp1 = gw_api.create_mqtt_gateway(name = name)
            assert resp1['status'] == 200, f"第一次创建失败：{resp1}"
            assert resp1['message'] == 'success', f"第一次创建网关失败：{resp1}"
            gw_id_1 = resp1['result']['id']
            logger.info(f"第一次创建成功 - ID：{gw_id_1}，Name：{name}")

            allure.attach(
                json.dumps(resp1, indent = 2, ensure_ascii = False),
                name = "第一次创建响应",
                attachment_type = allure.attachment_type.JSON
            )

        with allure.step("第二次创建同名网关"):
            resp2 = gw_api.create_mqtt_gateway(name = name)
            assert resp2['message'] == 'success', "第二次创建响应为空"
            assert resp2['status'] == 200, f"第二次创建状态码异常：{resp2.get('status')}"

            # 关键验证：两次创建都成功，但ID不同
            gw_id_2 = resp2['result']['id']
            logger.info(f"第二次创建成功 - ID：{gw_id_2}，Name：{name}")

            allure.attach(
                json.dumps(resp2, indent = 2, ensure_ascii = False),
                name = "第二次创建响应",
                attachment_type = allure.attachment_type.JSON
            )

            # 核心断言：两个ID必须不同（系统生成的唯一标识）
            assert gw_id_1 != gw_id_2, f"两次创建返回了相同ID：{gw_id_1}"
            logger.info(f"验证通过：同名网关创建了不同的ID：{gw_id_1} != {gw_id_2}")

            # 记录测试结果
            if gw_id_1 != gw_id_2:
                allure.attach(
                    f"同名网关测试结果：\n"
                    f"- 网关1 ID：{gw_id_1}\n"
                    f"- 网关2 ID：{gw_id_2}\n"
                    f"- 名称：{name}\n"
                    f"- 结论：系统允许重名，通过ID区分",
                    name = "重名测试结论",
                    attachment_type = allure.attachment_type.TEXT
                )

        with allure.step("验证两个网关都能正常查询"):
            """验证两个同名网关都能独立查询和操作"""
            detail1 = gw_api.get_gateway_detail(gw_id_1)
            detail2 = gw_api.get_gateway_detail(gw_id_2)

            assert detail1['status'] == 200
            assert detail2['status'] == 200
            assert detail1['result']['name'] == detail2['result']['name'] == name
            logger.info(f"两个同名网关都能独立查询")

        with allure.step("清理测试数据"):
            """清理创建的测试网关"""
            delete_status1 = gw_api.delete_gateway(gw_id_1)
            delete_status2 = gw_api.delete_gateway(gw_id_2)

            assert delete_status1, f"删除网关1失败：{gw_id_1}"
            assert delete_status2, f"删除网关2失败：{gw_id_2}"
            logger.info(f"已清理两个测试网关")

            allure.attach(
                f"清理结果：\n"
                f"- 网关1 {gw_id_1}：{'成功' if delete_status1 else '失败'}"
                f"- 网关2 {gw_id_2}：{'成功' if delete_status2 else '失败'}",
                name = "清理结果",
                attachment_type = allure.attachment_type.TEXT
            )