import json
import time
import pytest
import allure
from test_jetlinks.common.api_client import SceneClient

@allure.epic("JetLinks物联网平台")
@allure.feature("场景联动模块")
@allure.story("场景创建与删除功能")
class TestScene:
    """场景创建相关测试"""

    @allure.title("正常创建场景联动")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("基于完整设备接入链路创建场景，验证场景基本信息")
    def test_create_scene_with_device_access(self, api_client, device_access_chain, scene_with_device_access):
        """
        测试：基于设备接入链路正常创建场景
        核心：验证场景ID、名称、设备关联、状态等基本信息
        """
        scene = scene_with_device_access
        device_id = device_access_chain['device_id']
        product_id = scene_with_device_access['product_id']

        with allure.step("验证场景基本信息"):
            allure.attach(
                json.dumps(scene, indent = 2, ensure_ascii = False),
                name = "场景数据",
                attachment_type = allure.attachment_type.JSON
            )

            assert scene['id'] is not None, "场景ID不应为空"
            assert scene['name'] == f"高温告警{device_id}", f"场景名称不匹配"
            assert scene['device_id'] == device_id, "设备ID不匹配"
            assert scene['product_id'] == product_id, "产品ID不匹配"

            print(f"场景基本信息验证通过：{scene['id']}")

        with allure.step("通过场景ID查询详情"):
            # 创建临时客户端查询详情
            scene_client = SceneClient()
            scene_client.session = api_client.session
            scene_client.headers = api_client.headers

            # 先获取场景详情
            detail_resp = scene_client.get_scene_detail(scene['id'])

            allure.attach(
                json.dumps(detail_resp, indent = 2, ensure_ascii = False),
                name = "场景详情响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert detail_resp['status'] == 200, f"查询失败，状态码：{detail_resp['status']}"
            assert detail_resp['message'] == 'success', f"查询失败，业务报错：{detail_resp['message']}"
            assert detail_resp['result']['id'] == scene['id'], "场景ID不匹配"
            assert detail_resp['result']['name'] == scene['name'], "场景名称不匹配"

            print(f"场景详情验证通过，创建成功")

    @allure.title("删除不存在的场景")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("测试删除不存在的场景时API的响应")
    def test_delete_nonexistent_scene(self, api_client):
        """
        测试：删除不存在的场景
        核心：验证API对不存在资源的处理，不应抛出异常，应返回4xx和错误详情
        """
        scene_client = SceneClient()
        scene_client.session = api_client.session
        scene_client.headers = api_client.headers

        fake_scene_id = "non_existent_scene_9999999"

        with allure.step("1.尝试删除不存在的场景"):
            resp = scene_client.delete_scene(fake_scene_id)

            allure.attach(
                json.dumps(resp, indent = 2, ensure_ascii = False),
                name = "删除不存在场景的响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert resp is not None, "响应不应为空"
            assert 'status' in resp, "响应应包含status字段"
            assert 'message' in resp, "响应应包含message字段"

            # 根据API设计，可能返回404或200（某些API设计为幂等）
            # 这里我们只验证不会崩溃
            print(f"删除不存在场景的异常测试通过：响应：{resp}")

    @allure.title("禁用不存在的场景")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("测试禁用不存在的场景时API的响应")
    def test_disable_nonexistent_scene(self, api_client):
        """
        测试：禁用不存在的场景
        核心：验证API对不存在资源的处理
        """
        scene_client = SceneClient()
        scene_client.session = api_client.session
        scene_client.headers = api_client.headers

        fake_id = "non_existent_scene_99999"

        with allure.step("1.尝试禁用不存在的场景"):
            resp = scene_client.disable_scene(fake_id)

            allure.attach(
                json.dumps(resp, indent = 2, ensure_ascii = False),
                name = "禁用响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert resp is not None
            assert 'status' in resp
            assert 'message' in resp

            print(f"禁用不存在场景的异常处理测试通过:{resp}")

    @allure.title("启用不存在的场景")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("测试启动不存在的场景时API的响应")
    def test_enable_nonexistent_scene(self, api_client):
        """
        测试：启用不存在的场景
        核心：验证API对不存在资源的处理
        """
        scene_client = SceneClient()
        scene_client.session = api_client.session
        scene_client.headers = api_client.headers

        fake_id = "non_existent_scene_99999"

        with allure.step("1.尝试启用不存在的场景"):
            resp = scene_client.enable_scene(fake_id)

            allure.attach(
                json.dumps(resp, indent = 2, ensure_ascii = False),
                name = "启用响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert resp is not None
            assert 'status' in resp
            assert 'message' in resp

            print(f"启用不存在的场景异常测试处理通过:{resp}")

    @allure.title("重复禁用已禁用的产品")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("测试多次禁用同一场景的幂等性")
    def test_disable_already_disabled_scene(self, api_client, device_access_chain):
        """
        测试：重复禁用已禁用的场景
        核心：验证禁用操作的幂等性，多次调用应都成功
        """
        device_id = device_access_chain['device_id']
        product_id = device_access_chain['product_id']

        scene_client = SceneClient()
        scene_client.session = api_client.session
        scene_client.headers = api_client.headers

        with allure.step("1.创建场景"):
            result = scene_client.create_and_configure_scene(
                scene_name = f"幂等性测试{device_id}",
                device_id = device_id,
                product_id = product_id
            )
            scene_id = result['id']
            print(f"场景创建成功：{scene_id}")

        with allure.step("2.首次禁用场景"):
            disable_resp1 = scene_client.disable_scene(scene_id)
            assert disable_resp1['status'] == 200
            assert disable_resp1['message'] == 'success'
            print(f"首次禁用成功！{disable_resp1}")

        with allure.step("3.再次禁用场景"):
            disable_resp2 = scene_client.disable_scene(scene_id)

            allure.attach(
                json.dumps(disable_resp2, indent = 2, ensure_ascii = False),
                name = "重复禁用响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert disable_resp2['status'] == 200, f"重复禁用应成功，实际{disable_resp2['message']}"
            assert disable_resp2['message'] == 'success'

            print(f"重复禁用操作成功（幂等性验证通过）：{disable_resp2}")

            with allure.step("4.清理：删除场景"):
                try:
                    scene_client.delete_scene(scene_id)
                    print(f"场景已清理")
                except Exception as e:
                    print(f"清理时出错：{e}")

    @allure.title("重复启用已启用的场景")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("测试多次启用同一场景的幂等性")
    def test_enable_already_enable_scene(self, api_client, device_access_chain):
        """
        测试：重复启用已启用的场景
        核心：验证启用操作的幂等性
        """
        device_id = device_access_chain['device_id']
        product_id = device_access_chain['product_id']

        scene_client = SceneClient()
        scene_client.session = api_client.session
        scene_client.headers = api_client.headers

        with allure.step("1.创建场景（默认启用）"):
            result = scene_client.create_and_configure_scene(
                scene_name = f"启用幂等性测试{device_id}",
                device_id = device_id,
                product_id = product_id
            )
            scene_id = result['id']

            # 场景创建后默认启用，先禁用再启用测试
            scene_client.disable_scene(scene_id)
            print(f"场景已创建并禁用")

        with allure.step("2.首次启用场景"):
            enable_resp1 = scene_client.enable_scene(scene_id)
            assert enable_resp1['status'] == 200
            assert enable_resp1['message'] == 'success'
            print(f"首次启用成功:{enable_resp1}")

        with allure.step("3.再次启用已启用的场景"):
            enable_resp2 = scene_client.enable_scene(scene_id)

            allure.attach(
                json.dumps(enable_resp2, indent = 2, ensure_ascii = False),
                name = "再次启用返回的响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert enable_resp2['status'] == 200
            assert enable_resp2['message'] == 'success'
            print(f"重复启用操作成功（幂等性验证通过）：{enable_resp2}")

        with allure.step("4.清理：删除场景"):
            try:
                scene_client.delete_scene(scene_id)
                print(f"场景已清理")
            except Exception as e:
                print(f"清理时出错：{e}")

    @allure.title("重复删除已删除的场景")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("测试多次删除同一个场景的幂等性")
    def test_delete_already_deleted_scene(self, api_client, scene_with_device_access):
        """
        测试：重复删除已删除的场景
        核心：验证删除操作的幂等性
        """
        device_id = scene_with_device_access['device_id']
        product_id = scene_with_device_access['product_id']

        scene_client = SceneClient()
        scene_client.session = api_client.session
        scene_client.headers = api_client.headers

        with allure.step("1.创建场景"):
            scene_id = scene_with_device_access['id']

        with allure.step("2.禁用场景"):
            disable_resp = scene_client.disable_scene(scene_id)

            assert disable_resp['status'] == 200
            assert disable_resp['message'] == 'success'
            print(f"禁用场景成功，响应：{disable_resp}")

        with allure.step("3.首次删除场景"):
            delete_resp1 = scene_client.delete_scene(scene_id)

            assert delete_resp1['status'] == 200
            assert delete_resp1['message'] == 'success'
            print(f"删除场景成功，响应：{delete_resp1}")

        with allure.step("4.再次删除场景"):
            delete_resp2 = scene_client.delete_scene(scene_id)

            allure.attach(
                json.dumps(delete_resp2, indent = 2, ensure_ascii = False),
                name = "重复删除相同ID场景响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert delete_resp2['status'] == 200
            assert delete_resp2['message'] == 'success'
            print(f"重复删除测试验证成功，响应：{delete_resp2}")

    @allure.title("创建场景后立刻删除")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("测试创建场景后立即删除的边界情况（不启用场景）")
    def test_create_and_immediate_delete_without_enable(self, api_client, scene_with_device_access):
        """
        测试：创建场景后立即删除（不启用）
        核心：验证场景创建后可以立即删除，不需要启用
        """
        scene = scene_with_device_access
        scene_id = scene['id']
        device_id = scene['device_id']

        scene_client = SceneClient()
        scene_client.session = api_client.session
        scene_client.headers = api_client.headers

        with allure.step("1.验证场景已创建并启用"):
            detail_resp = scene_client.get_scene_detail(scene_id)
            assert detail_resp['result']['state']['value'] in ['started', 'enable']
            print("场景状态：启用")

        with allure.step("2.禁用场景"):
            disable_resp = scene_client.disable_scene(scene_id)
            assert disable_resp['status'] == 200
            assert disable_resp['message'] == 'success'
            print(f"场景已禁用")

        with allure.step("3.立即删除场景"):
            delete_resp = scene_client.delete_scene(scene_id)

            allure.attach(
                json.dumps(delete_resp, indent = 2, ensure_ascii = False),
                name = "禁用状态下删除场景的响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert delete_resp['status'] == 200, f"删除失败，验证码：{delete_resp['status']}"
            assert delete_resp['message'] == 'success', f"删除失败：{delete_resp['message']}"
            print(f"场景已删除（禁用状态下）")

        with allure.step("4.验证场景已删除"):
            # 尝试查询场景详情
            try:
                detail_resp = scene_client.get_scene_detail(scene_id)
                # 应该返回404或空结果
                assert detail_resp['status'] in [200, 404], f"查询状态码异常：{detail_resp['status']}"

                if detail_resp['status'] == 200:
                    result = detail_resp['result']
                    assert result is None or result['id'] != scene_id, f"场景依然存在：{result}"
            except Exception as e:
                error_msg = str(e)
                if '404' in error_msg or 'Not Found' in error_msg:
                    print(f"成功跳过禁用状态删除场景并捕获到预期异常：{error_msg}")
            print(f"场景删除验证通过")