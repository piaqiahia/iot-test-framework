import time

import pytest
import json
import allure

@allure.epic("JetLinks物联网平台")
@allure.feature("产品管理模块")
@allure.story("产品删除功能")
class TestProductDelete:

    @allure.title("正常删除产品(get_detail验证)")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("使用get_detail查询确认产品被删除")
    def test_delete_product_success(self, api_client, product_write_api, product_read_api, temp_product_for_delete):
        """
        测试：正常删除产品
        核心：使用 product_read_api.get_detail 验证删除前后状态
        """
        product_id = temp_product_for_delete

        with allure.step("1.确认产品存在"):
            # 使用 product_read_api.get_detail 查询
            detail_resp = product_read_api.get_detail(column = "id", value = product_id)

            allure.attach(
                json.dumps(detail_resp, indent = 2, ensure_ascii = False),
                name = "删除前-详情响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert detail_resp['status'] == 200
            assert detail_resp['result']['total'] == 1
            assert detail_resp['result']['data'][0]['id'] == product_id
            assert detail_resp['result']['data'][0]['name'] == f"test_product_{product_id}"

            print(f"删除前验证通过：{product_id}存在")

        with allure.step("2.调用删除接口"):
            resp = product_write_api.delete_my_product(product_id)

            allure.attach(
                json.dumps(resp, indent = 2, ensure_ascii = False),
                name = "删除响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert resp['status'] == 200, f"删除失败，状态码：{resp['status']}"
            assert resp['message'] == 'success', f"业务报错：{resp['message']}"
            print(f"用例内删除成功：{product_id}")

        with allure.step("3.通过get_detail确认已删除"):
            # 再次调用get_detail
            detail_resp = product_read_api.get_detail(column = "id", value = product_id)

            allure.attach(
                json.dumps(detail_resp, indent = 2, ensure_ascii = False),
                name = "删除后-详情响应",
                attachment_type = allure.attachment_type.JSON
            )

            # 关键断言：查询结果应该为空
            assert detail_resp['status'] == 200
            assert detail_resp['result']['total'] == 0, f"期望0条数据，实际{detail_resp['result']['total']}条"
            assert detail_resp['result']['data'] == [], "数据列表应为空"

            # 辅助验证：再次查询确认
            detail_resp2 = product_read_api.get_detail(column = "id", value = product_id)
            assert detail_resp2['result']['total'] == 0

            print(f"删除后验证通过：{product_id}已不存在")

    @allure.title("删除不存在的产品")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证删除不存在的产品系统不会崩溃")
    def test_delete_nonexistent_product(self, product_write_api):
        """测试：删除不存在的产品"""
        fake_id = "nonexistent_product_999999"

        with allure.step("尝试删除不存在的产品"):
            resp = product_write_api.delete_my_product(fake_id)

            allure.attach(
                json.dumps(resp, indent = 2, ensure_ascii = False),
                name = "删除响应",
                attachment_type = allure.attachment_type.JSON
            )

        with allure.step("断言错误处理"):
            # 不应该返回 500
            assert resp['status'] == 404, "删除不存在产品不应导致服务器崩溃"

            # 应返回404或其他业务错误
            if resp['status'] == 404:
                allure.attach("返回 404 Not Found", name = "状态码", attachment_type = allure.attachment_type.TEXT)
                print(f"删除不存在的产品返回404（预期行为）")
            elif resp['message'] == 'success':
                print("删除不存在的产品message错误返回success")
            else:
                pytest.fail(f"删除不存在的产品成功！响应：{resp}")

    @allure.title("创建产品后删除")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证创建产品后可正常删除")
    def test_delete_product_after_creation(self, api_client, product_write_api, product_read_api):
        """
        测试：创建产品后删除
        优势：不会污染截图中的真实产品数据，测试更安全
        """
        # 生成唯一ID
        unique_id = f"test_del_{int(time.time() * 1000)}"

        product_data = {
            "name": "test_del_product_{unique_id}",
            "classifiedId": "-222-",
            "classifiedName": "智能电力",
            "deviceType": "device",
            "describe": "一个创完就删的测试产品",
            "id": unique_id
        }

        created_id = None

        try:
            with allure.step(f"1.创建测试产品{unique_id}"):
                # 使用api_client的创建方法
                created_product = api_client.create_product_function(**product_data)
                created_id = created_product.get('id')

                assert created_id is not None, "产品创建失败"
                assert created_id == unique_id, f"ID不匹配：{created_id} ！= {unique_id}"

                print(f"已创建产品：{created_id}")

                # 验证创建成功
                detail_resp = product_read_api.get_detail(column = "id", value = created_id)
                assert detail_resp['status'] == 200
                assert detail_resp['result']['total'] == 1
                assert detail_resp['result']['data'][0]['name'] == product_data['name']

                allure.attach(
                    json.dumps(detail_resp, indent = 2, ensure_ascii = False),
                    name = "创建后的产品详情",
                    attachment_type = allure.attachment_type.JSON
                )

            with allure.step(f"2.开始删除"):
                resp = product_write_api.delete_my_product(created_id)
                assert resp['message'] == 'success', f"删除失败：{resp['message']}"
                print(f"已删除产品：{created_id}")

                allure.attach(
                    json.dumps(resp, indent = 2, ensure_ascii = False),
                    name = "删除响应",
                    attachment_type = allure.attachment_type.JSON
                )

            with allure.step(f"3.验证删除状态"):
                detail_resp = product_read_api.get_detail(column = "id", value = created_id)

                allure.attach(
                    json.dumps(detail_resp, indent = 2, ensure_ascii = False),
                    name = "删除后的响应查询",
                    attachment_type = allure.attachment_type.JSON
                )

                # 关键断言
                assert detail_resp['status'] == 200
                assert detail_resp['result']['total'] == 0, f"期望0条数据，但实际有{detail_resp['result']['total']}条"
                assert detail_resp['result']['data'] == [], "数据列表应为空"

                print(f"产品：{created_id}已成功删除")

            with allure.step("4.验证列表查询"):
                # 查询列表，确认产品不在列表中
                search_resp = product_read_api.search()
                product_ids = [item['id'] for item in search_resp['result']['data']]

                print(product_ids)
                assert created_id not in product_ids, f"产品{created_id}不应在列表中"
                print(f"列表查询验证通过")

            print(f"\n 测试通过：产品{created_id}创建->删除流程工作正常")

        finally:
            # 清理：如果测试中途失败，确保产品被删除
            if created_id:
                try:
                    check_resp = product_read_api.get_detail(column = "id", value = created_id)
                    if check_resp['result']['total'] == 1:
                        product_write_api.delete_mt_product(created_id)
                        print(f"[finally]清理：已删除产品：{created_id}")
                except Exception as e:
                    print(f"[finally]错误：{e}")

    @allure.title("删除后重新创建相同ID(ID回收验证)")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证删除后可以重新创建相同ID的产品(ID回收)")
    def test_delete_and_recreate_same_id(self, api_client, product_write_api, product_read_api):
        """测试：删除后重新创建相同ID"""
        # 生成唯一ID
        unique_id = f"test_del_{int(time.time() * 1000)}"

        # 第一次创建
        with allure.step("1.第一次创建产品"):
            product1 = api_client.create_product_function(
                name="first_create",
                classifiedId =  "-222-",
                classifiedName = "智能电力",
                deviceType = "device",
                describe = "第一次创建",
                id = unique_id
            )
            assert product1['id'] == unique_id
            print(f"第一次创建：{unique_id}")

        # 验证第一次创建
        with allure.step("2.验证第一次创建"):
            detail1 = product_read_api.get_detail(column = "id", value = unique_id)
            assert detail1['result']['total'] == 1
            assert detail1['result']['data'][0]['id'] == unique_id
            allure.attach(
                json.dumps(detail1, indent = 2, ensure_ascii = False),
                name = "第一次创建详情",
                attachment_type = allure.attachment_type.JSON
            )

        # 删除
        with allure.step("3.删除产品"):
            resp = product_write_api.delete_my_product(unique_id)
            assert resp['message'] == 'success'
            print(f"已确认删除")

        # 验证删除
        with allure.step("4.验证已删除"):
            detail_after_delete = product_read_api.get_detail(column = "id", value = unique_id)
            assert detail_after_delete['result']['total'] == 0
            print(f"已确认删除")

        # 再次创建相同ID
        with allure.step("5.重新创建相同ID的产品"):
            product2 = api_client.create_product_function(
                name = "第二次创建",
                classifiedId = "-222-",
                classifiedName = "智能电力",
                deviceType = "device",
                describe = "第二次创建测试产品",
                id = unique_id
            )
            assert product2['id'] == unique_id
            assert product2['name'] == "第二次创建"
            print(f"第二次创建：{unique_id}")

        # 验证第二次创建
        with allure.step("6.验证第二次创建"):
            detail2 = product_read_api.get_detail(column = "id", value = unique_id)
            assert detail2['result']['total'] == 1
            assert detail2['result']['data'][0]['name'] == "第二次创建"
            assert detail2['result']['data'][0]['describe'] == "第二次创建测试产品"

            allure.attach(
                json.dumps(detail2, indent = 2, ensure_ascii = False),
                name = "第二次创建详情",
                attachment_type = allure.attachment_type.JSON
            )

        with allure.step("7.最终清理"):
            product_write_api.delete_my_product(unique_id)

        print(f"ID回收测试通过")
