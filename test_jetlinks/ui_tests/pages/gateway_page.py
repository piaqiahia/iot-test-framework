class GatewayPage:
    def __init__(self, page):
        self.page = page
        # 左侧菜单：父菜单“运维管理”展开后，网关管理在下级
        self.link_menu = page.locator("[data-menu-id='/iot/link']")
        self.link_type_submenu = page.locator("[data-menu-id='/iot/link/type']")
        # 新增按钮 plus图标
        self.add_btn = page.locator("button:has(svg[data-icon='plus'])")
        # 表单字段
        self.name_input = page.locator("#basic_name")
        self.name_trigger = page.locator("#basic_type") # 网络类型下拉框触发器
        self.port_trigger = page.locator("#dynamic_form_nest_item_cluster_0_configuration_prot") # 本地端口下拉触发器
        self.public_port_input = page.locator("#dynamic_form_nest_item_cluster_0_configuration_publicPort")
        self.public_host_input = page.locator("#dynamic_form_nest_item_cluster_0_configuration_publicHost")
        self.save_btn = page.locator("button.ant-btn-primary").last  # 弹窗内确定按钮

    def goto_gateway_list(self):
        """进入网关管理列表页"""
        self.link_menu.click()
        self.link_type_submenu.click()
        self.page.wait_for_selector("button:has(svg[data-icon='plus'])", timeout = 5000)

    def create_gateway(self, name, type_index = 2, port = "80", public_port = "80", public_host = "127.0.0.1"):
        """
        创建网关
        :param name: 网关名称
        :param type_index:通信类型（下拉选框）
        :param port:本地端口
        :param public_port:公网端口
        :param public_host:公网地址
        """
        # 点击新增
        self.add_btn.click()
        self.page.wait_for_selector("#basic_name", timeout = 5000)

        # 填写网关名称
        self.name_input.fill(name)

        # 选择网络类型 点击触发器 等待下拉容器 点击索引对应的选项
        self.name_trigger.lick()
        dropdown = self.page.selector(".ant-select-dropdown:not(.ant-select-dropdown-hidden)")
        dropdown.wait_for(state = "visible", timeout = 5000)
