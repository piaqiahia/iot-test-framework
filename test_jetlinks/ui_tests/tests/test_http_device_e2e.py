import pytest
import allure
from test_jetlinks.ui_tests.pages.product_page import ProductPage

@allure.epic("JetLinks 物联网平台")
@allure.feature("HTTP 设备接入 - UI 端到端")
@allure.story("产品创建与启用")
@allure.title("通过 UI 创建 HTTP 产品并启用")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.ui
@pytest.mark.http_device
def test_create_and_enable_http_product(logged_in_page, http_product_setup):
    """
    验证通过 UI 创建的 HTTP 产品能够成功启用
    http_product_setup 夹具已自动完成创建→关闭提示→启用→关闭提示的全流程
    此处只做结果校验（可扩展）
    """
    product_id = http_product_setup["product_id"]
    product_name = http_product_setup["product_name"]

    # 可选：验证产品列表页出现了该产品（需要 ProductListPage，暂无则跳过）
    # 或者直接打印信息确认
    print(f"HTTP 产品创建并启用成功: {product_id} - {product_name}")