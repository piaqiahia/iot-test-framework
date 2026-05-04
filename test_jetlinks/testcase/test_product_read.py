import pytest
import allure

@allure.feature("产品管理模块")
@allure.story("产品查询功能")
@allure.epic("JetLinks物联网平台")
class TestProductOperations:
    """
    产品模块 Read 操作测试
    覆盖搜索、列表、详情、字典
    """

    @allure.title("产品名称模糊搜索")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.description("验证通过产品名称模糊匹配能正确返回结果")
    def test_search_by_name_like(self, product_read_api):
        """测试：名称模糊搜索"""
        terms = [
            {"column": "name", "termType": "like", "value": "%prod%", "type": "or"}
        ]
        resp = product_read_api.search(terms = terms)

        assert resp['status'] == 200
        assert resp['result']['total'] == 6
        print(f"搜索到{resp['result']['total']}条数据")

    @allure.title("产品ID精确搜索")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证通过产品ID能精确匹配并返回唯一结果")
    def test_search_by_id_exact(self, product_read_api):
        """测试：ID 精确搜索"""
        terms = [
            {"column": "id", "termType": "eq", "value": "prod_001", "type": "or"}
        ]
        resp = product_read_api.search(terms = terms)

        assert resp['result']['total'] == 1
        assert resp['result']['data'][0]['id'] == "prod_001"
        assert resp['result']['data'][0]['name'] == "prod_001"
        print("查找通过")

    @allure.title("组合条件搜索")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证组合字段搜索产品，要求能返回满足条件的所有产品")
    def test_search_combination(self, product_read_api):
        """测试：组合条件 (网关类型=MQTT 且 状态=正常)"""
        # 组合条件通常是多个 terms 在一个数组里，且 type=and (取决于后端实现)
        # 这里是两组条件的 AND 关系
        terms = [
            {
                "terms":[
                    {"column": "gatewayType", "termType": "eq", "value": "MQTT直接连入", "type": "or"}
                ]
            },
            {
                "terms":[
                    {"column": "state", "termType": "eq", "value": "1", "type": "or"}
                ],
                "type": "and"
            }
        ]

        resp = product_read_api.search(terms = terms)
        # 应该只有 prod_001 符合
        assert resp['result']['total'] == 1
        assert resp['result']['data'][0]['id'] == "prod_001"
        assert resp['result']['data'][0]['name'] == "prod_001"
        print("组合查找通过")

    @allure.title("查看产品详情")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("查看某个产品详情，返回的产品信息要与请求ID的产品一致")
    def test_get_detail_by_id(self, product_read_api):
        """测试：查看产品详情"""
        resp = product_read_api.get_detail(column = "id", value = "prod_001")

        assert resp['status'] == 200
        assert resp['result']['data'][0]['id'] == "prod_001" # 硬编码 可能报错
        assert resp['result']['data'][0]['name'] == "prod_001"
        assert resp['result']['data'][0]['state'] == 1

    @allure.title("默认产品列表分页")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证指定分页大小返回预期显示数量")
    def test_list_all_pagination(self, product_read_api):
        """测试：默认列表分页"""
        resp = product_read_api.list_all(page_index = 0, page_size = 12)
        assert resp['result']['total'] == 6

    @allure.title("获取搜索下拉框")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("获取网关类型字典，要求与预期内容一致")
    def test_get_dict_gateway_type(self, product_read_api):
        """测试：获取网关类型字典"""
        resp = product_read_api.get_dict()

        assert resp['status'] == 200

        # 打印看看返回结构
        print(f"响应体结构：{resp}")
        # 简单断言：返回了数据且是列表
        assert isinstance(resp.get('result', []), list)
        assert resp['result'][0]['name'] == "MQTT直连接入"
        print("字典验证成功")

    @allure.title("空搜索返回所有产品")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证空搜索（不选择/填入内容，返回所有产品）")
    def test_search_with_existing_id(self, product_read_api):
        """
        测试：验证搜索结果是否包含所有已知 ID
        """
        prod_id = [
            "prod_001",
            "prod_002",
            "prod_003",
            "prod_004",
            "prod_005",
            "2043274755711934464"
        ]
        # 搜所有
        resp = product_read_api.search()
        returned_ids = [item['id'] for item in resp['result']['data']]

        # 检查截图中的 ID 是否都在返回结果里 (可能有新增的，所以用子集判断)
        # 或者检查总数是否大于等于 6
        assert resp['result']['total'] == 6

        # 抽查几个
        for pid in ["prod_001", "prod_004"]:
            assert pid in returned_ids
        print("验证产品列表通过")

