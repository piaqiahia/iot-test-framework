import time

import pytest
import allure
import json

@allure.epic("JetLinks物联网平台")
@allure.story("产品编辑功能")
@allure.feature("产品管理模块")
class TestProductUpdate:

    @allure.title("正常修改产品名称")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证修改产品名称功能")
    def test_update_product_name(self, api_client, product_write_api, product_read_api, create_product_for_update):
        """
        测试：修改产品名称
        核心：修改前后对比验证
        """
        product_id = create_product_for_update
        new_name = f"change_name_{product_id}"

        with allure.step("确认产品存在并记录原始名称"):
            detail_resp = product_read_api.get_detail(column = "id", value = product_id)

            allure.attach(
                json.dumps(detail_resp, indent = 2, ensure_ascii = False),
                name = "修改前-详情响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert detail_resp['status'] == 200
            assert detail_resp['result']['total'] == 1
            original_name = detail_resp['result']['data'][0]['name']
            assert "test_update_product" in original_name

            print(f"修改前验证通过：{product_id} 名称={original_name}")

        with allure.step("修改产品名称"):
            update_data = {
                "id": product_id,
                "name": new_name,
                "classifiedId": "-222-",
                "classifiedName": "智能电力",
                "deviceType": "device",
                "describe": "这是一个自动化用例创建的产品，用完即删"
            }

            resp = product_write_api.update_product(product_id, update_data)

            allure.attach(
                json.dumps(resp, indent = 2, ensure_ascii = False),
                name = "修改响应",
                attachment_type = allure.attachment_type.JSON
            )

            print(f"resp:{resp}")
            assert resp['status'] == 200
            assert resp['result'] is True
            assert resp['message'] == 'success'
            print(f"修改成功：{product_id}")

        with allure.step("验证名称已修改"):
            detail_resp = product_read_api.get_detail(column = "id", value = product_id)

            allure.attach(
                json.dumps(detail_resp, indent = 2, ensure_ascii = False),
                name = "修改后-详情响应",
                attachment_type = allure.attachment_type.JSON
            )

            assert detail_resp['status'] == 200
            assert detail_resp['result']['total'] == 1
            assert detail_resp['result']['data'][0]['name'] == new_name
            assert detail_resp['result']['data'][0]['id'] == product_id

            print(f"修改后通过验证：{product_id} 名称：{new_name}")

    @allure.title("修改多个字段（名称+分类+描述）")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证同时修改多个字段，基于新创建的产品")
    def test_update_multiple_fields(self, api_client, product_write_api, product_read_api, create_product_for_update):
        """
        测试：同时修改多个字段
        """
        product_id = create_product_for_update

        new_data = {
            "name": "new_name_multiple_update",
            "classifiedID": "-333-",
            "classifiedName": "智能家居",
            "describe": "修改后的描述",
        }

        with allure.step("记录原始数据"):
            detail_before = product_read_api.get_detail(column = "id", value = product_id)
            original_name = detail_before['result']['data'][0]['name']
            original_classified = detail_before['result']['data'][0]['classifiedName']
            original_desc = detail_before['result']['data'][0]['describe']

            print(f"原始数据：名称={original_name}，分类={original_classified}，描述={original_desc}")

        with allure.step("执行多字段修改"):
            update_data = {
                "id": product_id,
                "name": new_data['name'],
                "classifiedID": new_data['classifiedID'],
                "classifiedName": new_data['classifiedName'],
                "deviceType": "device",
                "describe": new_data['describe']
            }

            resp = product_write_api.update_product(product_id, update_data)
            print(f"resp:{resp}")
            assert resp['message'] == 'success'
            print(f"多字段修改成功")

        with allure.step("验证所有字段已修改"):
            detail_after = product_read_api.get_detail(column = "id", value = product_id)

            assert detail_after['result']['data'][0]['name'] == new_data['name']
            assert detail_after['result']['data'][0]['classifiedName'] == new_data['classifiedName']
            assert detail_after['result']['data'][0]['describe'] == new_data['describe']

            # 验证未修改的字段保持不变
            assert detail_after['result']['data'][0]['deviceType']['value'] == "device"

            print(f"所有字段验证通过")

            allure.attach(
                json.dumps({
                    "修改前":{
                        "name": original_name,
                        "classifiedName": original_classified,
                        "describe": original_desc
                    },
                    "修改后":{
                        "name": detail_after['result']['data'][0]['name'],
                        "classifiedName": detail_after['result']['data'][0]['classifiedName'],
                        "describe": detail_after['result']['data'][0]['describe'],
                    }
                }, indent = 2, ensure_ascii = False),
                name = "修改前后对比",
                attachment_type = allure.attachment_type.JSON
            )

    @allure.title("修改不存在的产品")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证修改不存在的产品时的错误处理")
    def test_update_nonexistent_product(self, product_write_api):
        """
        测试：修改不存在的产品
        注意：此用例不依赖 created_product_for_update，因为它需要一个确定的不存在的ID
        """
        fake_id = "nonexistent_product_9999999"

        update_data = {
            "id": fake_id,
            "name": "none_existent_product"
        }

        with allure.step("尝试修改不存在的产品并捕获异常"):
            # 使用 pytest.raises 捕获 Exception
            # 如果 update_product 抛出了 Exception，且异常信息包含 "404"，则测试通过
            # 如果没有抛出异常，或者抛出的异常信息不包含 "404"，则测试失败
            with pytest.raises(Exception) as exc_info:
                product_write_api.update_product(fake_id, update_data)

        # 验证异常信息
        error_msg = str(exc_info.value)
        allure.attach(f"捕获到预期异常：{error_msg}", name = "异常信息", attachment_type = allure.attachment_type.TEXT)

        # 断言异常中包含404
        assert '404' in error_msg or 'Not Found' in error_msg

        print(f"成功捕获到404异常：{error_msg}，系统防御成功")

    @allure.title("修改产品后验证产品列表查询")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证修改后的产品在列表中正确显示")
    def test_update_product_list_query(self, api_client, product_write_api, product_read_api, create_product_for_update):
        """
        测试：修改产品后列表查询验证
        """
        product_id = create_product_for_update
        new_name = f"list_verify_{product_id}"

        with allure.step("修改产品名称"):
            update_data = {"id": product_id, "name": new_name}
            resp = product_write_api.update_product(product_id, update_data)
            assert resp['message'] == 'success'

        with allure.step("查询列表"):
            search_resp = product_read_api.search(page_size = 96)

            found_product = next((item for item in search_resp['result']['data'] if item['id'] == product_id), None)

            assert found_product is not None, f"产品{product_id}不在产品列表中"
            assert found_product['name'] == new_name, f"列表中名称未更新：{found_product['name']}"

            print(f"列表查询验证通过：{product_id}名称={new_name}")

    @allure.title("修改产品描述（特殊字符）")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证描述字段可以包含特殊字符")
    def test_update_product_with_special_chars(self, api_client, product_write_api, product_read_api, create_product_for_update):
        """
        测试：修改产品描述包含特殊字符
        """
        product_id = create_product_for_update

        special_desc = "这是一段包含特殊字符的描述：!@#$%^&*()_+{}|:-=[]\;',.//\\中文"

        with allure.step("修改描述为特殊字符"):
            update_data = {
                "id": product_id,
                "describe": special_desc
            }

            resp = product_write_api.update_product(product_id, update_data)

            assert resp['message'] == 'success'
            print(f"特殊字符描述修改成功")

        with allure.step("验证特殊字符正确保存"):
            detail_resp = product_read_api.get_detail(column = "id", value = product_id)

            assert detail_resp['result']['data'][0]['describe'] == special_desc
            print(f"特殊字符验证通过")

            allure.attach(
                json.dumps({
                    "原始描述": detail_resp['result']['data'][0]['describe'],
                    "特殊字符测试": "通过"
                }, indent = 2, ensure_ascii = False),
                name = "特殊字符测试结果",
                attachment_type = allure.attachment_type.JSON
            )

    @allure.title("修改产品为空字符串（边界测试）")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证必填字段不能为空")
    def test_update_product_with_empty_name(self, api_client, product_write_api, product_read_api, create_product_for_update):
        """
        测试：尝试将产品名称修改为空字符串
        """
        product_id = create_product_for_update

        with allure.step("尝试修改名称为空字符串"):
            update_data = {
                "id": product_id,
                "name": "" # 空字符串
            }

        resp = product_write_api.update_product(product_id, update_data)
        allure.attach(
            json.dumps(resp, indent = 2, ensure_ascii = False),
            name = "修改响应",
            attachment_type = allure.attachment_type.JSON
        )

        with allure.step("断言业务状态"):
            if resp['message'] == 'success':
                verify = product_read_api.get_detail(column="id", value=product_id)
                # 如果后端允许空字符串，记录但不失败
                assert verify['result']['data'][0]['name'] != '', f"错误，接口传递参数导致产品的name为空！：{verify}"
                allure.attach("警告：后端允许接口传递的名称内容为空", name = "注意", attachment_type = allure.attachment_type.TEXT)
                print("警告：后端允许接口传递的名称内容为空")
            else:
                print(f"传递产品名称为空值的请求被成功拦截！")

    @allure.title("验证修改后的数据持久化")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证修改后的数据能够正确持久化")
    def test_update_product_persistence(self, api_client, product_write_api, product_read_api, create_product_for_update):
        """
        测试：验证修改后数据持久化
        通过多次查询验证数据一致性
        """
        product_id = create_product_for_update
        new_name = f"persistence_test_{product_id}"
        print(product_id)
        with allure.step("修改产品名称"):
            update_data = {
                "id": product_id,
                "name": new_name
            }
            resp = product_write_api.update_product(product_id, update_data)
            assert resp['message'] == 'success'

        with allure.step("立即查询验证"):
            detail1 = product_read_api.get_detail(column = "id", value = product_id)
            assert detail1['result']['data'][0]['name'] == new_name
            print("立刻查询验证通过")

        with allure.step("延迟后再次查询"):
            time.sleep(1)
            detail2 = product_read_api.get_detail(column = "id", value = product_id)
            assert detail2['result']['data'][0]['name'] == new_name
            print("延迟查询验证通过")
        with allure.step("通过列表查询验证"):
            search_resp = product_read_api.search(page_size = 96)
            product_list = None
            for item in search_resp['result']['data']:
                print(item['id'], product_id)
                if item['id'] == product_id:
                    product_list = item
                    break


        assert product_list is not None
        assert product_list['name'] == new_name
        print("列表查询验证通过")

        print("数据持久化验证通过")