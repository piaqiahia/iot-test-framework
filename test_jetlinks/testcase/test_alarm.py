import time

import pytest
import allure
import json
from test_jetlinks.common.api_client import AlarmClient

@allure.epic("JetLinks物联网平台")
@allure.feature("告警管理模块")
class TestAlarmManagement:

    @allure.story("告警生命周期管理")
    @allure.title("正常创建并验证告警")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description(
        """
        测试告警的完整生命周期：
        1. 使用 fixture 创建一个新告警。
        2. 验证 fixture 返回的告警 ID 有效。
        3. 测试结束后，由 fixture 自动清理（禁用并删除）告警。
        """
    )
    def test_create_and_verify_alarm_lifecycle(self, api_client, alarm_id):
        """
        测试：正常创建并验证告警
        核心：依赖 alarm_id fixture 完成创建和清理，用例本身只做基础验证
        """
        allure.dynamic.title(f"正常创建并验证告警：（ID：{alarm_id}）")

        with allure.step("验证Fixture创建的告警ID"):
            assert alarm_id is not None, "Fixture未能返回告警ID"
            assert isinstance(alarm_id, str), "告警ID应为字符串类型"
            assert alarm_id.isdigit() and len(alarm_id) > 10, "告警 ID 格式不正确"
            allure.attach(
                f"告警ID：{alarm_id}",
                name = "创建的告警ID",
                attachment_type = allure.attachment_type.TEXT
            )
            print(f"Fixture提供的告警ID：{alarm_id}有效")

        with allure.step("查看告警详情"):
            alarm_client = AlarmClient()
            alarm_client.session = api_client.session
            alarm_client.headers = api_client.headers

            # 使用alarm_client 进行查询
            detail_resp = alarm_client.get_alarm_detail(alarm_id)
            assert detail_resp['message'] == 'success', f"查看告警详情失败：{detail_resp['message']}"
            assert detail_resp['result']['id'] == alarm_id, f"错误，返回的告警ID和查询的不一致！查询的：{alarm_id}，返回的：{detail_resp['result']['id']}"
            print(f"告警详情验证通过，创建成功！")

    @allure.story("告警状态变更")
    @allure.title("手动禁用并验证告警状态")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("测试在测试函数内部手动调用禁用接口，并验证其效果")
    def test_manual_disable_alarm(self, api_client, alarm_id):
        """
        测试：手动禁用告警
        核心：在测试函数内调用 disable_alarm，并（模拟）验证状态
        """
        allure.dynamic.title(f"手动禁用告警（ID：{alarm_id}）")

        # 创建临时的 AlarmClient 实例用于调用方法
        alarm_client = AlarmClient()
        alarm_client.session = api_client.session
        alarm_client.headers = api_client.headers

        with allure.step("手动禁用调用接口"):
            print(f"手动调用禁用接口 for ID：{alarm_id}")
            disable_resp = alarm_client.disable_alarm(alarm_id)

            allure.attach(
                json.dumps(disable_resp, indent = 2, ensure_ascii = False),
                name = "手动禁用响应",
                attachment_type = allure.attachment_type.JSON
            )
            assert disable_resp['status'] == 200
            assert disable_resp['message'] == 'success'
            print(f"告警（ID：{alarm_id}）已成功手动禁用")

        with allure.step("验证告警状态已变更"):
            # 获取告警详情
            detail_resp = alarm_client.get_alarm_detail(alarm_id)
            assert detail_resp['message'] == 'success'
            assert detail_resp['result']['state']['value'] == 'disabled'
            print("验证完成，成功进入禁用状态！（默认启用）")

    @allure.story("告警修改")
    @allure.title("修改告警名称和描述")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("测试修改告警的名称和描述字段")
    def test_update_alarm_name_and_description(self, api_client, alarm_id):
        """
        测试：修改告警名称和描述
        核心：使用 PATCH 接口修改告警配置
        """
        allure.dynamic.title(f"修改告警名称和描述（ID：{alarm_id}）")

        alarm_client = AlarmClient()
        alarm_client.session = api_client.session
        alarm_client.headers = api_client.headers

        with allure.step("先查询告警原始信息"):
            original_detail = alarm_client.get_alarm_detail(alarm_id)
            original_name = original_detail['result']['name']
            original_desc = original_detail['result']['description']

            allure.attach(
                json.dumps(original_detail, indent = 2, ensure_ascii = False),
                name = "修改前告警详情",
                attachment_type = allure.attachment_type.JSON
            )
            print(f"原始名称：{original_name}，原始描述：{original_desc}")

        with allure.step("调用PATCH接口修改告警"):
            new_name = f"name_after_update_{int(time.time() * 1000)}"
            new_desc = "这是修改后的描述信息"
            new_target_type = "product"
            new_level = 1

            update_resp = alarm_client.update_alarm(
                alarm_id = alarm_id,
                name = new_name,
                description = new_desc,
                target_type = new_target_type, # 必要字段
                level = new_level # 必要字段
            )

            allure.attach(
                json.dumps(update_resp, indent = 2, ensure_ascii = False),
                name = "修改告警响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert update_resp['status'] == 200
            assert update_resp['message'] == 'success'
            assert update_resp['result']['updated'] == 1, "期望更新1条记录"
            print(f"告警修改成功，更新了{update_resp['result']['updated']}条记录")

        with allure.step("验证修改结果"):
            update_detail = alarm_client.get_alarm_detail(alarm_id)

            allure.attach(
                json.dumps(update_detail, indent = 2, ensure_ascii = False),
                name = "修改后告警详情",
                attachment_type = allure.attachment_type.JSON
            )

            assert update_detail['result']['name'] == new_name, f"名称未更新，期望：{new_name}"
            assert update_detail['result']['description'] == new_desc, f"描述未更新"
            assert update_detail['result']['targetType'] == new_target_type, f"范围未更新"
            assert update_detail['result']['level'] == new_level, f"紧急等级未更新"
            print(f"验证通过：名称已更新为'{new_name}'，描述已更新为'{new_desc}，范围更新为：'{new_target_type}'，紧急等级更新为：'{new_level}'")

    @allure.story("异常场景")
    @allure.title("删除不存在的告警")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("删除不存在的ID的告警，应返回404")
    def test_delete_nonexistent_alarm(self,api_client):
        """测试删除不存在的告警"""
        alarm_client = AlarmClient()
        alarm_client.session = api_client.session
        alarm_client.headers = api_client.headers

        fake_id = "99999999999999"

        with allure.step("尝试删除不存在的告警"):
            try:
                resp = alarm_client.delete_alarm(fake_id)
                # 如果代码执行到这里，说明没有抛出异常
                # 那么应该检查响应状态码
                allure.attach(
                    json.dumps(resp, indent = 2, ensure_ascii = False),
                    name = "删除不存在告警的响应",
                    attachment_type = allure.attachment_type.JSON
                )

                # 断言异常
                assert resp['status'] == 404, f"期望状态码404，实际得到{resp['status']}"
                assert resp['message'] == '数据不存在', f"期望错误消息'数据不存在'，实际的到：{resp['message']}"
                assert resp['code'] == 'not_found', f"期望错误码'not_found'，实际得到：{resp['code']}"

                print(f"删除不存在的告警返回了预期的404错误")

            except Exception as e:
                # 如果抛出异常，也是预期的行为
                error_msg = str(e)
                allure.attach(
                    error_msg,
                    name = "异常信息",
                    attachment_type = allure.attachment_type.TEXT
                )

                # 验证异常信息中包含关键字
                assert "404" in error_msg or "not_found" in error_msg.lower(), f"异常信息应包含404或not_found，实际：{error_msg}"

                print(f"删除不存在的告警时抛出预期异常：{error_msg}")