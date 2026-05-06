from playwright.sync_api import expect
import time
import allure

@allure.epic("JetLinks 物联网平台")
@allure.feature("设备管理 - UI 自动化")
@allure.story("调试辅助")
@allure.title("设备列表页渲染检查（调试截图）")
@allure.severity(allure.severity_level.MINOR)
def test_debug_screenshot_manual(device_list_page):
    """【调试】打开列表页，停留长时间，打印文字内容并截图"""
    # 先给页面充足时间加载
    time.sleep(5)  # 等 5 秒，确保后端数据返回
    device_list_page.page.wait_for_timeout(3000)

    # 打印当前页面标题
    print("当前页面标题:", device_list_page.page.title())

    # 尝试打印所有 .card-content-top-line 中的设备名
    cards = device_list_page.page.locator(".card-content-top-line")
    count = cards.count()
    print(f"卡片数量: {count}")

    # 打印所有设备名（span[style*='font-weight: 600']）
    names = device_list_page.page.locator("span[style*='font-weight: 600']").all_inner_texts()
    print("页面上所有加粗的设备名：", names)

    # 截图
    device_list_page.page.screenshot(path="screenshots/debug_manual.png", full_page=True)
    print("截图已保存: screenshots/debug_manual.png")

    # 如果需要肉眼观看，可以再加30秒
    time.sleep(10)

@allure.epic("JetLinks 物联网平台")
@allure.feature("设备管理 - UI 自动化")
@allure.story("设备列表页")
@allure.title("验证设备卡片状态显示")
@allure.severity(allure.severity_level.CRITICAL)
def test_device_status_in_list(device_list_page, test_product_and_device):
    """验证状态显示"""
    status = device_list_page.get_device_status(test_product_and_device["device_name"])
    print(f"设备状态: {status}")
    assert status == "禁用", f"预期禁用，实际: {status}"


@allure.epic("JetLinks 物联网平台")
@allure.feature("设备管理 - UI 自动化")
@allure.story("设备列表页")
@allure.title("验证设备名称在卡片上展示")
@allure.severity(allure.severity_level.NORMAL)
def test_device_name_in_list(device_list_page, test_product_and_device):
    """【列表层】验证设备名称在卡片上展示"""
    device_name = test_product_and_device["device_name"]
    card = device_list_page.get_device_card_by_name(device_name)
    expect(card.locator("span[style*='font-weight: 600']")).to_have_text(device_name)


@allure.epic("JetLinks 物联网平台")
@allure.feature("设备管理 - UI 自动化")
@allure.story("设备详情页")
@allure.title("验证产品名称绑定显示")
@allure.severity(allure.severity_level.CRITICAL)
def test_device_detail_product_binding(device_detail_page, test_product_and_device):
    """【详情层】验证产品名称绑定显示正确"""
    expect(device_detail_page.device_name).to_have_text(test_product_and_device["device_name"])
    expect(device_detail_page.product_name).to_have_text(test_product_and_device["product_name"])