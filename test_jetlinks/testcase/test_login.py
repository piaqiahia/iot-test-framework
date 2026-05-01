import pytest
import json
from test_jetlinks.common.api_client import APIClient
import time
import allure

USERNAME = "admin"
PASSWORD = "123456Qwe"

@allure.feature("登录模块")
@allure.story("登录功能测试")
@allure.epic("JetLinks系统测试")
class TestLogin:

    @allure.title("正常登录测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证用户使用正确的用户名和密码能正常登录并获取Token")
    @allure.testcase("https://test-case-url/login-success", "正常登录测试用例")
    def test_login_success(self, api_client):
        """正常登录"""
        # 前置条件已由 fixture 完成（api_client 已经登录）
        # 直接验证 Token 存在且有效
        assert api_client.token is not None
        assert len(api_client.token) == 32 # JWT 长度检查

        # 进一步验证：用 Token 访问受保护接口
        resp = api_client.get(endpoint = "/authorize/me")
        assert resp['status'] == 200
        assert resp['result']['user']['username'] == USERNAME
        print("正常登录用例通过")

    @allure.title("登录失败场景测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("测试各种登录失败场景，包括错误密码，空值，不存在用户等")
    @pytest.mark.parametrize(
        "case_name, username, password, expected",
        [
            ("wrong_password", USERNAME, "wrong_pwd", "错误"),
            ("empty_username", "", PASSWORD, "用户名不能为空"),
            ("empty_password", USERNAME, "", "密码不能为空"),
            ("non_existent_user", "nouser", "123", "错误"),
            ("sql_injection_basic", f"{USERNAME}' OR '1' = '1", "123", "错误")
        ]
    )
    def test_login_failed_scenarios(self, case_name, username, password, expected):
        """
        L1: 登录失败的各种场景 - 参数化测试
        不使用 fixture，每个用例独立创建客户端
        """
        client = APIClient()
        with pytest.raises(Exception, match = expected): # 报错的内容必须包含match = 的内容
            client.login(username, password)
        print(f"异常测试通过：{case_name}")

    @allure.title("字段健壮性测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("测试系统对各种长度输入的处理能力，包括边界值和攻击长度")
    @pytest.mark.parametrize(
        "field, test_values, category",
        [
            ("username", [""], "空值"),
            ("username", ["a", "ab", "abc"], "极短"),
            ("username", ["a" * 10, "a" * 20, "a" * 30], "正常范围"),
            ("username", ["a" * 50, "a" * 64, "a" * 100], "可疑长度"),
            ("username", ["a" * 500, "a" * 1000, "a" * 5000], "攻击长度"),

            # 密码长度探测
            ("password", [""], "空值"),
            ("password", ["a", "ab", "abc"], "极短"),
            ("password", ["a" * 10, "a" * 20, "a" * 30], "正常范围"),
            ("password", ["a" * 50, "a" * 64, "a" * 100], "可疑长度"),
            ("password", ["a" * 1000, "a" * 5000, "a" * 10000], "攻击长度")
        ])
    def test_field_length_robustness(self, field, test_values, category):
        """
        L2: 通用字段长度健壮性测试
        测试系统对各种长度输入的处理能力
        """
        print(f"\n --- [{category:8s}]测试{field}长度 ---")

        for value in test_values:
            length = len(value)
            client = APIClient()
            if field == "username":
                username = value
                password = PASSWORD
            else: # password
                username = USERNAME
                password = value

            try:
                # 记录开始时间
                start = time.time()
                token = client.login(username, password)
                elapsed = time.time() - start

                # 成功的情况
                print(f"成功，{field:10s}长度{length:5d}:允许：(耗时：{elapsed:.3f}s)")

                #性能警告
                if length > 1000 and elapsed > 1.5:
                    print(f"警告，{field:10s}长度{length:5d}允许(耗时：{elapsed:.3f}s)")

            except Exception as e:
                error_msg = str(e)

                # 不能返回500
                assert "500" not in error_msg, f"错误，{field}长度{length}：导致了服务器崩溃！错误码：500"

                # 获取状态码
                status_code = None
                if hasattr(e, 'response') and e.response: # 先查找e中是否有response
                    if hasattr(e.response, 'status_code'): # 查找e.response中是否有‘status_code’
                        status_code = e.response.status_code
                    elif hasattr(e.response, 'status'):
                        status_code = e.response.status

                if "timeout" in error_msg.lower():
                    print(f" {field:10s}长度{length:5d}：超时(DoS防护)")
                else:
                    # 只要不是500就算通过
                    if status_code:
                        assert status_code != 500, f"错误，{field}长度{length}返回500！"
                    print(f"{field:10s}长度{length:5d}：被拒绝（状态：{status_code or 'N/A'}）")

    @allure.title("安全注入测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("测试系统对SQL注入，XSS，命令注入等安全攻击的防护能力")
    @allure.label("安全测试", "注入攻击")
    @pytest.mark.security
    @pytest.mark.parametrize(
        "case_name, payload",
        [
            ("sql_injection", {"username" : "admin' OR '1' = '1", "password" : "123"}),
            ("xss", {"username" : "<script>alert(1)</script>", "password" : "123"}),
            ("command_injection", {"username" : "admin; ls", "password" : "123"}),
            ("special_chars", {"username" : "admin!@#$%^&*(){}:<>?:", "password" : "123"}),
        ]
    )
    def test_security_payloads(self, case_name, payload):
        """L2: 安全注入测试"""
        client = APIClient()
        resp = client.session.post(f"{client.base_url}/authorize/login", json = payload)

        # 核心断言：不能崩溃
        assert resp.status_code != 500, f"安全漏洞{case_name}导致500错误"

        # 应该返回客户端错误（400/401/403/422）
        assert resp.status_code in [400,403], f"安全测试失败：{case_name}返回了意外状态码：{resp.status_code}"

        print(f"{case_name:20s} - Status:{resp.status_code}")

    @allure.title("未授权访问测试")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.description("验证系统能正确拒绝未携带Token的请求")
    @allure.label("安全测试", "授权验证")
    @pytest.mark.security
    def test_access_without_token(self):
        """L1: 未携带Token访问受保护接口"""
        client = APIClient()

        # 明确期望抛出异常
        with pytest.raises(Exception) as exc_info:
            client.get("/authorize/me")

        # 验证异常信息包含 401 或 Unauthorized
        error_msg = str(exc_info.value)
        assert "401" in error_msg or "Unauthorized" in error_msg, f"期望异常包含401或Unauthorized，实际：{error_msg}"

        print(f"未授权访问通过：{error_msg}")