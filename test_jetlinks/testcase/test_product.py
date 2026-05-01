import pytest
import time
import uuid
import allure

@allure.epic("JetLinks物联网平台")
@allure.feature("产品管理模块")
@allure.suite("产品创建接口测试")
class TestProductCreate:
    """产品创建相关测试"""

    @allure.title("正常创建产品")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.description("验证合法参数能创建产品，并校验返回字段的正确性")
    def test_create_success(self, api_client, create_product_fixture):
        """测试：正常创建产品"""
        data = create_product_fixture

        # 直接断言返回的字段
        assert data['id'] is not None
        assert data['name'] == f"自动化测试产品_{data['id']}"
        assert data['classifiedName'] == "智能电力"
        assert data['deviceType']['value'] == "device"  # 注意看你的返回，deviceType是个对象
        assert data['creatorName'] == "Administrator"

        print(f"创建返回数据完整，ID: {data['id']}")

    @allure.title("创建产品-字段边界值测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("测试ID 名称 描述字段的长度 边界 空值 极值情况")
    @pytest.mark.parametrize(
        "id_len, name_len, desc_len, should_pass",
        [
            # --- 所有字段正常 ---
            (10, 10, 50, True),
            (64, 64, 200, True),
            # --- 单个字段超限（其他字段正常） ---
            (65, 10, 50, False),
            (10, 65, 50, False),
            (10, 10, 201, False),
            # --- 极端情况 ---
            (100, 100, 500, False),
            (0, 10, 50, True),
            (10, 0, 50, False),
            (10, 10, 0, True),
        ]
    )
    def test_create_all_fields_boundary(self, api_client, id_len, name_len, desc_len, should_pass):
        """
        综合测试：ID、名称、描述的边界值（三个一起测）
        用时间戳+随机数保证唯一性，避免重复
        """
        # 构造测试数据
        timestamp = str(int(time.time() * 1000))
        if id_len > 10:
            if len(timestamp) < id_len:
                unique_id = timestamp + 'a' * (id_len - len(timestamp))
            else:
                unique_id = timestamp[:id_len]
        else:
            unique_id = None

        test_name = 'b' * name_len if name_len > 0 else None
        test_desc = 'c' * desc_len if desc_len > 0 else None

        print(f"\n 测试ID：{unique_id},名称:{test_name}，描述：{test_desc} -》 {'通过' if should_pass else '失败'}")

        created_id = None  # 记录创建的ID，用于清理

        # 执行创建
        try:
            result = api_client.create_product_function(
                id = unique_id,
                name = test_name,
                classifiedId = "-222-",
                classifiedName = "智能电力",
                deviceType = "device",
                describe = test_desc
            )

            created_id = result.get('id')

            # 断言
            if should_pass:
                assert result['id'] is not None
                assert len(result['id']) <= 64
                assert len(result['name']) <= 64
                assert len(result.get('describe', '')) <= 200
                print(f"创建成功，ID={result['id']}")
            else:
                assert False, f"预期失败但成功创建！ID={result['id']}"

        except Exception as e:
            error_msg = str(e)
            if not should_pass:
                assert "长度" in error_msg or "请" in error_msg or "重复" in error_msg
                print(f"成功拦截-{error_msg[:40]}")
            else:
                # 预期成功但失败
                print(f"预期成功但创建失败：{e}")
                # 统一抛出异常
                raise

        finally:
            # 清理
            if created_id and should_pass is True:
                print(f"\n 正在执行用例内部的产品删除，目标ID：{created_id}")
                try:
                    api_client.delete_product(created_id)
                    print(f"产品{created_id}已清理")
                except Exception as e:
                    print(f"清理失败：{e}")

    @allure.title("创建产品-安全注入与异常值测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("测试系统对XSS，SQL注入，特殊字符，空值的防护能力")
    @allure.label("安全测试", "注入攻击")
    @pytest.mark.security
    @pytest.mark.parametrize(
        "special_id, special_name, special_desc, should_pass",
        [
            # === 安全注入 ===
            ("safe_test_001", "test<script>", "normal", False), # XSS
            ("safe_test_002", "normal", "' OR '1' = '1", False), # SQL注入
            ("safe_test_003", "normal", "'; DROP TABLE;", False),

            # === 空格 ===
            ("space_test_001", "test ", "normal", True), # 末尾空格
            ("space_test_002", " test", "normal", True), # 开头空格
            ("space_test_003", " ", "normal", False), # 全空格

            # === 特殊字符 ===
            ("special_@_001", "normal", "normal", False), # @符号
            ("special_/_002", "normal", "normal", False), # /符号
            ("special_\\_003", "normal", "normal", False),# \\符号

            # === Unicode ===
            ("产品_001", "产品名称", "正常", False), # 中文
            ("unicode_002", "test", "normal", True),   # 英文

            # === 空值 ===
            ("null_001", None, "normal", False),
            ("null_002", "", "normal", False),
        ]
    )
    def test_create_product_security(self, api_client, special_id, special_name, special_desc, should_pass):
        """安全注入和异常值"""
        created_id = None

        try:
            result = api_client.create_product_function(
                id = special_id,
                name = special_name,
                classifiedId = "-222-",
                classifiedName = "智能电力",
                deviceType = "device",
                describe = special_desc
            )
            created_id = result.get('id')

            if should_pass:
                assert result['id'] is not None
                print(f"创建成功")
            else:
                assert False, f"预期失败但创建成功,ID:{created_id}" # 前面没抛出异常走到这里说明有问题直接assert False抛出异常

        except Exception as e:
            error_msg = str(e)
            if not should_pass:
                # 预期失败的情况下，需要确认两件事：
                # 1. 确实报错了（符合预期）
                # 2. 产品没有被创建（没有数据污染）

                if created_id:
                    # 虽然报错了，但产品已经创建了
                    raise AssertionError(f"虽然接口报错，但产品已创建！ID={created_id}")
                else:
                    # 报错了，且没创建产品，拦截成功
                    print(f"符合预期：被拦截")
            else:
                print(f"预期成功但失败：{e}")
                raise

        finally:
            if created_id and should_pass:
                try:
                    api_client.delete_product(created_id)
                except:
                    pass

    @allure.title("创建产品-重复ID测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证系统能正确拦截重复的产品的ID，确保数据唯一性")
    def test_create_duplicate_id(self, api_client, create_product_fixture):
        """测试：重复创建相同ID的产品"""
        data = create_product_fixture
        product_id = data['id']

        # 尝试用相同ID再次创建
        with pytest.raises(Exception) as exc_info: # 允许抛出Exception不终止程序（崩溃）
            api_client.create_product_function(
                id = product_id,
                name = "重复测试",
                classifiedId = "-222-",
                classifiedName = "智能电力",
                deviceType = "device",
                describe = "重复测试"
            )

        # 断言错误信息包含“重复”或“已存在”
        assert "重复" in str(exc_info.value) or "已存在" in str(exc_info.value) or "被占用" in str(exc_info.value)
        print("成功拦截重复ID")

    @allure.title("创建产品-分类ID无效场景测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证分类ID的存在性校验，格式校验，长度限制和异常值")
    @pytest.mark.parametrize(
        "classified_id, classified_name, should_pass, expected_error_keyword",
        [
            ("-222-", "智能电力", True, None),
            ("-99999-", "不存在的分类", False, "不存在"),
            ("12345", "数字分类", False, "格式"),
            ("invalid_id@", "特殊字符", False, "格式"),
            ("", "空分类id", False, "为空"),
            ("a" * 100, "超长ID", False, "Internal Server Error"),
            ("<script>alert(1)</script>", "xss注入", False, "Bad Request"),
            ("' OR '1' = '1", "SQL注入", False, "Bad Request"),
            ("'; DROP TABLE;", "SQL注入2", False, "Bad Request"),
        ]
    )
    def test_create_invalid_classified_id(self, api_client, classified_id, classified_name, should_pass, expected_error_keyword):
        """
        测试：分类ID无效场景
        重点验证后端是否校验关联数据的存在性和合法性
        """
        print(f"\n 测试分类ID:{classified_id}预期：{'成功' if should_pass else '失败'}")

        # 构造唯一ID避免干扰
        test_id = f"test_class_{classified_id[:10]}_{int(time.time() * 1000)}"

        if should_pass:
            # 预期成功的情况：直接调用并断言
            try:
                result = api_client.create_product_function(
                    id = test_id,
                    name = "测试产品",
                    classifiedId = classified_id,
                    classifiedName = classified_name,
                    deviceType = "device",
                    describe = "test"
                )
                assert result['id'] is not None
                print(f"创建成功，分类ID通过验证")

                # 清理
                api_client.delete_product(result['id'])

            except Exception as e:
                # 如果预期成功但失败了，需要看具体错误
                pytest.fail(f"预期创建成功， 但失败了：{e}")

        else:
            # 预期失败的情况：使用 pytest.raises
            with pytest.raises(Exception) as exc_info:
                api_client.create_product_function(
                    id = test_id,
                    name = "测试产品",
                    classifiedId = classified_id,
                    classifiedName = classified_name,
                    deviceType = "device",
                    describe = "test"
                )

            # 获取错误信息
            error_msg = str(exc_info.value)
            print(f"捕获到异常：{error_msg[:60]}")

            # 校验错误关键词（根据后端实际返回调整）
            if expected_error_keyword:
                assert expected_error_keyword in error_msg, f"错误信息不匹配！期望包含'{expected_error_keyword}',实际：{error_msg}"

            print(f"符合预期，{classified_name}成功被拦截")

    @allure.title("创建产品-设备类型安全测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("测试设备类型字段的枚举白名单校验及注入防护")
    @pytest.mark.parametrize(
        "device_type, should_pass, inject_type",
        [
            # --- 基础枚举（必须通过） ---
            ("device", True, None),
            ("gateway", True, None),
            ("childrenDevice", True, None),

            # --- 非法枚举（必须拦截） ---
            ("xixixi", False, None),

            # --- 安全注入测试,即使格式不对，也要看后端怎么处理 ---
            # SQL注入
            ("' OR '1' = '1", False, "sql"),
            ("'; DROP TABLE;", False, "sql"),

            # XSS注入
            ("<script>alert(1)</script>", False, "xss"),
            ("test<script>", False, "xss"),

            # 特殊字符
            ("!@#$%^&*(){}|:?><\\/+-*.", False, "char"),
            ("../../etc/passwd", False, "path"),

            # 空值
            ("", False, None),
            (" ", False, None),
        ]
    )
    def test_create_device_type_security(self, api_client, device_type, should_pass, inject_type):
        """
        测试设备类型的安全性：不仅测业务逻辑，还要测注入防护
        """
        test_id = f"test_sec_{device_type[:10]}_{int(time.time() * 1000)}"

        try:
            result = api_client.create_product_function(
                id = test_id,
                name = "安全测试",
                classifiedId = "-222-",
                classifiedName = "智能电力",
                deviceType = device_type,
                describe = "test"
            )

            # 如果 should_pass=False 但创建成功了 -> Bug
            if should_pass:
                assert result['id'] is not None
                print(f"枚举值：[{device_type}]正常")

                # 正常数据需要清理，避免干扰其他测试
                try:
                    api_client.delete_product(result['id'])
                    print(f"正常数据已清理")
                except Exception as e:
                    print(f"正常数据清理失败，需手动清理：{e}")

            else:
                # 预期失败但创建成功了,存在安全漏洞
                error_msg = "预期失败但创建成功"
                pytest.fail(error_msg)

        except Exception as e:
            error_msg = str(e)

            if not should_pass:
                if "400" in error_msg or "500" in error_msg or "error" in error_msg.lower():
                    print(f"安全拦截成功：[{device_type}]被拒绝({error_msg[:50]})")
                else:
                    # 报错了但不是HTTP错误，可能是网络问题，标记为警告
                    print(f"报错但类型不明：{error_msg[:50]}")
            else:
                # 预期成功但报错了 -> 功能Bug
                pytest.fail(f"基准功能异常：正常枚举[{device_type}]创建失败：{error_msg}")


        except Exception as e:
            error_msg = str(e)

            if not should_pass:
                # 预期失败，且确实报错了
                # 检查是否是因为“非法枚举”报错，而不是因为“SQL语法错误”导致的500
                if "500" in error_msg or "SQL" in error_msg.upper():
                    print(f"后端报错， 但可能是漏洞触发了崩溃：{error_msg[:50]}")
                else:
                    print(f"安全拦截：类型[{device_type}]被拒绝")
            else:
                # 预期成功但失败了
                pytest.fail(f"正常枚举值[{device_type}]创建失败：{e}")

    @allure.title("创建产品-设备类型安全测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("测试设备类型字段的枚举白名单校验及注入防护")
    @pytest.mark.parametrize(
        "classified_name, should_pass, inject_type, desc",
        [
            # --- 基础功能 ---
            ("智能电力", True, None, "正常名称"),
            ("", True, None, "空名称"),
            (" ", True, None, "纯空格"),

            # --- 长度边界 ---
            ("a" * 50, True, None, "50字符正常"),
            ("a" * 101, True, None, "超长101字符"),  # 假设限制100

            # --- 【重点】存储型 XSS ---
            # 这些值如果被存库，在前端列表展示时会执行JS
            ("<script>alert('XSS')</script>", False, "xss", "XSS脚本标签"),
            ("<img src=x onerror=alert(1)>", False, "xss", "XSS图片标签"),
            ("javascript:alert(1)", False, "xss", "JS协议"),

            # --- 【重点】SQL 注入（虽然是名称，但也要防） ---
            ("' OR '1'='1", False, "sql", "SQL注入尝试"),

            # --- 特殊字符与格式 ---
            ("分类/名称", True, None, "包含斜杠"),  # 看业务是否允许
            ("分类\\名称", False, None, "包含反斜杠"),
            ("分类<>名称", False, None, "包含尖括号"),
        ]
    )
    def test_create_classified_name_security(self, api_client, classified_name, should_pass, inject_type, desc):
        """
        测试：分类名称的安全性与边界值
        重点：防 XSS、长度校验
        """
        # 生成唯一ID，避免和其他测试冲突
        test_id = f"test_name_{inject_type or 'normal'}_{int(time.time() * 1000)}"

        # 固定用一个合法的 ID，只变 Name
        fixed_classified_id = "-222-"

        try:
            result = api_client.create_product_function(
                id=test_id,
                name="测试产品",
                classifiedId=fixed_classified_id,
                classifiedName=classified_name,  # 只改这个字段
                deviceType="device",
                describe="test"
            )

            created_id = result.get('id')

            if should_pass:
                assert created_id is not None
                # 额外断言：返回的 classifiedName 应该和传入的一致（或者被清洗后的）
                # 注意：有些后端会自动清洗特殊字符，这里先假设原样返回
                assert result['classifiedName'] == classified_name or "script" not in str(
                    result['classifiedName']).lower()
                print(f"名称 [{desc}] 测试通过")

                # 清理
                api_client.delete_product(created_id)
            else:
                # 预期失败但成功了 -> 漏洞
                pytest.fail(f"安全漏洞：分类名称 [{classified_name}] 本应被拦截，却创建成功！ID={created_id}")

        except Exception as e:
            error_msg = str(e)

            if not should_pass:
                # 预期失败，且确实报错了
                # 只要不是 200 OK，就算过
                if "400" in error_msg or "500" in error_msg or "Error" in error_msg:
                    print(f"安全拦截：[{desc}] 被拒绝 ({error_msg[:40]})")
                else:
                    # 如果是连接超时等非业务错误，标记一下
                    print(f"报错类型不明：[{desc}] - {error_msg[:40]}")
            else:
                # 预期成功但失败了
                pytest.fail(f"基准失败：正常名称 [{classified_name}] 创建失败: {e}")