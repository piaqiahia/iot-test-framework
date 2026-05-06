import pytest
import sys
import os
import time
import uuid

# 将项目根目录加入 sys.path，确保能导入 common 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from test_jetlinks.common.api_client import APIClient, DeviceClient

from test_jetlinks.ui_tests.pages.login_page import LoginPage
from test_jetlinks.ui_tests.pages.navigation import Navigation
from test_jetlinks.ui_tests.pages.device_list_page import DeviceListPage
from test_jetlinks.ui_tests.pages.device_details_page import DeviceDetailsPage

# 全局配置
BASE_URL = os.getenv("BASE_URL", "http://localhost:8848")
TEST_USER = os.getenv("TEST_USER", "admin")
TEST_PASS = os.getenv("TEST_PASS", "123456Qwe")

# API 客户端夹具（UI层专用，不依赖接口层的 Fixture）
@pytest.fixture(scope="session")
def api_client_ui():
    """
    UI 测试专用的 API 客户端（Session 级别，复用 Token）
    与接口层的 api_client 完全独立，不交叉引用
    """
    client = APIClient(base_url=BASE_URL)
    client.login(TEST_USER, TEST_PASS)  # 假设 APIClient 有 login 方法
    return client

@pytest.fixture(scope="session")
def init_jetlinks_if_needed(page):
    page.goto(f"{BASE_URL}/login")
    page.wait_for_timeout(2000)

    if "/init-home" not in page.url:
        return   # 已初始化，直接跳过

    # 1. 系统名称
    page.fill("#form_item_title", "TestOrg")
    page.click("button.ant-btn-primary.btn-style")
    page.wait_for_timeout(2000)

    # 2. base-path
    page.fill("#form_item_base-path", "http://local-host.cn:8848")
    page.click("button.ant-btn-primary.btn-style")   # 再次点击 确 定
    page.wait_for_timeout(2000)

    # 3. （如果页面需要设置管理员密码，请手动填完这一步找到密码输入框的 id）
    # page.fill("#form_item_password", "admin1234")   # 待确认

    page.click("button.ant-btn-primary")   # 保存修改
    page.wait_for_timeout(3000)

    assert "/init-home" not in page.url

# 造数夹具 只创建产品和设备
@pytest.fixture
def test_product_and_device(api_client_ui):
    device_client = DeviceClient()
    device_client.session = api_client_ui.session
    device_client.headers = api_client_ui.headers
    device_client.token = api_client_ui.token

    # 创建产品
    unique_id = f"ui_test_prod_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    product_data = {
        "name": f"UI测试产品_{unique_id}",
        "classifiedId": "-222-",
        "classifiedName": "智能电力",
        "deviceType": "device",
        "describe": "UI自动化测试用，用完即删"
    }
    product_result = api_client_ui.create_product_function(
        id=unique_id,
        **product_data
    )
    product_id = product_result['id']   # 产品 ID 是直接返回的
    product_name = product_result.get('name', product_data['name'])

    # 创建设备
    device_name = f"ui_test_device_{int(time.time())}"
    create_resp = device_client.create_device(
        device_id=device_name,   # 第一个参数就是设备 ID
        name=device_name,
        product_id=product_id
    )
    # 不依赖返回值，直接用我们传入的 device_name 作为设备 ID
    device_id = device_name
    print(f"设备创建成功，设备ID: {device_id}")

    data = {
        "product_id": product_id,
        "product_name": product_name,
        "device_id": device_id,
        "device_name": device_name
    }
    yield data

    # 清理：先禁用设备，再删除设备，最后删除产品
    # 设备可能未部署，但 undeploy 不会报错；delete 可能 404，忽略
    try:
        device_client.undeploy_device(device_id)
        time.sleep(0.3)
    except Exception:
        pass
    try:
        device_client.delete_device(device_id)
        print(f"设备 {device_id} 已删除")
    except Exception as e:
        print(f"设备删除异常（可忽略）: {e}")
    try:
        api_client_ui.delete_product(product_id)
        print(f"产品 {product_id} 已删除")
    except Exception as e:
        print(f"产品删除异常: {e}")

# 登录夹具
@pytest.fixture
def logged_in_page(page):
    login_page = LoginPage(page)
    login_page.goto(BASE_URL)
    try:
        login_page.login(TEST_USER, TEST_PASS)
    except Exception as e:
        # 打印登录页 HTML 到控制台
        print("===== LOGIN PAGE HTML (START) =====")
        print(page.content())
        print("===== LOGIN PAGE HTML (END) =====")
        page.screenshot(path="/tmp/login_failed.png")
        raise e
    yield page

# 导航到设备列表页
@pytest.fixture
def device_list_page(logged_in_page, test_product_and_device):
    """
    已登录并已创建测试数据后，再导航到设备列表页。
    确保列表页加载时，测试设备已经存在。
    """
    nav = Navigation(logged_in_page)
    list_page = nav.goto_device_list()
    # 额外加一点等待，防止前端异步渲染未完成
    logged_in_page.wait_for_timeout(2000)
    return list_page

# 进入设备详情页
@pytest.fixture
def device_detail_page(device_list_page, test_product_and_device, ui_labels):
    device_name = test_product_and_device["device_name"]
    return device_list_page.click_device(device_name, ui_labels)

@pytest.fixture
def ui_labels():
    """根据环境变量决定使用中文或英文标签"""
    lang = os.getenv("UI_LANG", "zh")  # 默认中文
    if lang == "en":
        return {
            "product_name": "Product Name",
            "running_status": "Running Status",
            "temperature": "Temperature",
            "humidity": "Humidity"
        }
    else:
        return {
            "product_name": "产品名称",
            "running_status": "运行状态",
            "temperature": "温度",
            "humidity": "湿度"
        }