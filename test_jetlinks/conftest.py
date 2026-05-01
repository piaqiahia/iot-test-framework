import sys
import json
import random
import uuid
import time
import pytest
import allure
import threading
from queue import Queue
from pathlib import Path
import paho.mqtt.client as mqtt
import redis
from common.api_client import APIClient
from test_jetlinks.common.api_client import ProductReadApi, ProductWriteApi, NetworkConfigApi, ProtocolClient, GatewayDeviceBindingClient, DeviceClient, AlarmClient, SceneClient

BASE_URL = "http://localhost:8848"
USERNAME = "admin"
PASSWORD = "123456Qwe"
JAR_PATH = Path(__file__).parent / "protocol" / "jetlinks-official-protocol-3.2.0-SNAPSHOT.jar"

@pytest.fixture(scope = "session")
def api_client():
    """
    Session 级夹具：整个测试会话只登录一次，所有用例共享 Token
    适合：功能测试、冒烟测试
    """
    client = APIClient(BASE_URL)
    client.login(USERNAME, PASSWORD)
    yield client
    # Teardown: 测试结束后可以做清理，如登出（如果有接口）
    print("\n 测试会话结束")

@pytest.fixture(scope = "session")
def product_read_api(api_client):
    """
    产品读操作 API Fixture (Session 级)
    自动登录，所有测试用例共享此实例
    """
    # 直接实例化 ProductReadApi，传入基础 URL 和账号密码
    # __init__ 会自动调用 login
    api = ProductReadApi(base_url = BASE_URL, username = USERNAME, password = PASSWORD)

    # 校验登录是否成功
    assert api.token is not None, "ProductReadApi 登录失败！"
    print(f"[setup]ProductReadApi初始化成功,Token:{api.token[:20]}...")

    yield api

    print("[Teardown] ProductReadApi 销毁")

@pytest.fixture(scope = 'session')
def product_write_api(api_client):
    """
    产品写操作 API Fixture（Session 级）
    """
    api = ProductWriteApi(base_url = api_client.base_url)
    api.token = api_client.token
    api.headers["Authorization"] = api_client.headers["Authorization"]
    yield api

@pytest.fixture
def fresh_login():
    """
    Function 夹具：每个测试函数都重新登录一次
    适合：需要隔离状态的测试（如并发登录测试）
    """
    client = APIClient(BASE_URL)
    yield client
    client.token = None
    client.headers.pop("Authorization", None)


@pytest.fixture
def temp_product_for_delete(api_client, product_write_api, product_read_api):
    """
    创建临时产品用于删除测试（自动清理）
    使用 product_read_api.get_detail 验证创建和删除状态
    """
    unique_id = f"test_del_{int(time.time() * 1000)}"

    product_data = {
        "name": f"test_product_{unique_id}",
        "classifiedId": "-222-",
        "classifiedName": "智能电力",
        "deviceType": "device",
        "describe": "测试产品",
        "id": unique_id
    }

    created_id = None

    try:
        # 创建产品
        created_product = api_client.create_product_function(**product_data)
        created_id = created_product.get('id')

        assert created_id is not None, "创建产品失败"
        assert created_id == unique_id, f"ID不匹配：{created_id} != {unique_id}"

        print(f"\n [Setup]创建测试产品：{created_id}")

        # 验证创建结果
        detail_resp = product_read_api.get_detail(column = "id", value = created_id)

        assert detail_resp['status'] == 200
        assert detail_resp['result']['total'] == 1
        assert detail_resp['result']['data'][0]['id'] == created_id
        assert detail_resp['result']['data'][0]['name'] == product_data['name']

        print(f"创建通过：{created_id}")

        yield created_id

    finally:
        # Teardown 自动删除
        if created_id:
            try:
                check_resp = product_read_api.get_detail(column="id", value=created_id)

                if check_resp['result']['total'] == 1:
                    # 查得到则删除
                    product_write_api.delete_my_product(created_id)
                    print(f"[Teardown] 已删除测试产品：{created_id}")
                else:
                    print(f"[Teardown] 产品{created_id} 已不存在（可能被其他测试删除）")
            except Exception as e:
                print(f"[Teardown] 清理警告：{e}")

@pytest.fixture
def invalid_token():
    """提供一个无效的 Token 字符串"""
    return "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJhZG1pbiJ9.INVALID_SIGNATURE"

@pytest.fixture
def create_product_fixture(api_client):
    """
    函数/用例级Fixture：创建一个产品，用例结束后自动删除
    scope="function" 表示每个用例都会重新创建和删除
    """
    print("\n---------正在创建测试产品--------")

    # 准备数据 为了防止ID冲突 用时间戳随机
    unique_id = f"test_prod_{int(time.time())}_{uuid.uuid4().hex[:4]}"

    product_data = {
        "name" : f"自动化测试产品_{unique_id}",
        "classifiedId" : "-222-",
        "classifiedName" : "智能电力",
        "deviceType" : "device",
        "describe" : "这是一个自动化用例创建的产品，用完即删"
    }

    # 调用封装方法创建产品
    result_data = None
    try:
        result_data = api_client.create_product_function(
            id = unique_id,
            **product_data
        )

        print(f"产品创建成功：{result_data.get('id')}")

        yield result_data

    finally:
        # 后置清理 不管用例成功还是失败，都要删除
        if result_data:
            product_id = result_data.get('id')
            print(f"\n -----[Teardown]正在清理测试产品ID：{result_data.get('id')}-----")
            try:
                api_client.delete_product(result_data.get('id'))
                print(f"产品{result_data.get('id')}已删除")
            except Exception as e:
                # 如果产品已经被删除了（比如用例里又删了一次），不算错误
                print(f"清理时提示:{e}")

@pytest.fixture
def temp_product_for_update(api_client, product_write_api, product_read_api):
    """
    创建临时产品用于编辑测试（自动清理）
    """
    unique_id = f"test_update_{int(time.time() * 1000)}"

    product_data = {
        "name": f"original_name_{unique_id}",
        "classifiedId": "-222-",
        "classifiedName": "智能电力",
        "deviceType": "device",
        "describe": "初始描述",
        "id": unique_id
    }

    created_id = None

    try:
        created_product = api_client.create_product_function(**product_data)
        created_id = created_product.get('id')

        assert created_id is not None
        assert created_id == unique_id

        print(f"\n [Setup]已创建测试产品：{created_id}")

        # 验证创建成功
        detail_resp = product_read_api.get_detail(column = "id", value = created_id)
        assert detail_resp['status'] == 200
        assert detail_resp['result']['total'] == 1
        assert detail_resp['result']['data'][0]['id'] == created_id
        assert detail_resp['result']['data'][0]['name'] == product_data['name']

        yield created_id

    finally:
        # 清理
        if created_id:
            try:
                check_resp = product_read_api.get_detail(column = "id", value = created_id)
                if check_resp['result']['total'] == 1:
                    product_write_api.delete_my_product(created_id)
                    print(f"[Teardown] 已删除测试用品：{created_id}")
            except Exception as e:
                print(f"[Teardown] 清理警告：{e}")

@pytest.fixture
def create_product_for_update(api_client):
    """
    函数级Fixture：为每个测试用例创建一个全新的产品，并在用例结束后自动删除。
    scope="function": 每个测试函数都会执行一次此fixture的创建和销毁。
    yield: 将创建的产品ID传递给测试函数。
    finally: 无论测试成功或失败，都会执行清理操作。
    """
    product_id = None

    # 准备唯一的产品数据
    unique_id = f"test_update_{int(time.time() * 1000)}"
    product_name = f"test_update_product"
    product_id = unique_id

    product_data = {
        "id": product_id,
        "name": product_name,
        "classifiedId": "-222-",
        "classifiedName": "智能电力",
        "deviceType": "device",
        "describe": "这是一个自动化测试创建的产品，用完即删"
    }

    # 调用API创建产品
    try:
        create_resp = api_client.create_product_function(**product_data)

        # 创建状态断言
        assert create_resp['name'] == product_name, f"产品创建失败：{create_resp}"
        assert create_resp.get('state') is not None, f"创建响应中缺少result：{create_resp}"

        print(f"[Fixture] 产品创建成功：ID={product_id}, name={product_name}")

        # 传递产品ID给用例
        yield product_id

    finally:
        # 后置清理：无论测试是否通过，都要删除
        if product_id:
            print(f"\n [Fixture] 进入删除阶段")
            try:
                delete_resp = api_client.delete_product(product_id)
                if delete_resp and delete_resp.get('success') is True:
                    print(f"[Fixture] 产品：{product_id}删除成功")
                else:
                    print(f"[Fixture] 警告：删除产品{product_id}时可能出现错误，响应：{delete_resp}")
            except Exception as e:
                # 如果删除失败，例如产品已不存在不应影响测试结果，仅作记录
                print(f"[Fixture] 清理时发生异常(可能被其他夹具/函数删除)，但不影响结果：{e}")

@pytest.fixture
def create_mqtt_gateway(api_client):
    # 函数级夹具：为每个测试函数创建一个新的MQTT网关，并在测试结束后自动清理（先禁用再删除）
    gw_api = NetworkConfigApi()
    gw_api.session = api_client.session
    gw_api.headers = api_client.headers

    gateway_name = f"Gateway_{int(time.time() * 1000)}"
    gateway_id = None

    # 创建资源
    try:
        create_resp = gw_api.create_mqtt_gateway(name = gateway_name)
        gateway_id = create_resp['result']['id']
        print(f"网关创建成功ID：{gateway_id}，Name：{gateway_name}")

        # 网关ID传递给用例
        yield gateway_id

    except Exception as e:
        print(f"[Fixture] 网关创建失败，测试无法执行：{e}")
        # 如果创建失败，直接抛出异常，跳过测试执行
        pytest.fail(f"Fixture Setup Failed:Cannot create gateway for test")

    # Teardown 清理资源
    finally:
        if gateway_id:
            print(f"正在清理网关：{gateway_id}")
            try:
                # 禁用网关（创建后默认开启，需要先禁用才能删除网关）
                shutdown_resp = gw_api.shutdown_gateway(gateway_id)
                assert shutdown_resp['message'] == 'success', f"[Teardown] 禁用网关失败"
                time.sleep(0.5)
                # 删除网关
                delete_success = gw_api.delete_gateway(gateway_id)
                if delete_success:
                    print(f"[Teardown] 网关{gateway_id}清理完成")
                else:
                    # delete_gateway 在资源不存在时返回 True，其他失败情况会抛异常
                    # 所以这里理论上不会执行到，除非有特殊逻辑
                    print(f"[Teardown] 网关{gateway_id}清理状态未知")
            except Exception as e:
                # Teardown 失败不应中断测试套件，但需要明确记录
                print(f"[Teardown] 网关{gateway_id}清理失败：{e}")

@pytest.fixture
def mqtt_gateway_id_only(api_client):
    # 仅返回网关ID，不包含自动清理逻辑。
    gw_api = NetworkConfigApi()
    gw_api.session = api_client.session
    gw_api.headers = api_client.headers

    gateway_name = f"Gateway_{int(time.time() * 1000)}"

    try:
        create_resp = gw_api.create_mqtt_gateway(name = gateway_name)
        return create_resp['result']['id']
    except Exception as e:
        pytest.fail(f"创建网关失败：{e}", pytrace = True)

@pytest.fixture(scope = 'module')
def uploaded_jar_id(api_client):
    """
    Module 级：整个测试模块只上传一次 Jar
    适合：一个测试文件里的所有用例共享同一个 Jar
    """
    protocol_client = ProtocolClient()
    protocol_client.session = api_client.session
    protocol_client.headers = api_client.headers

    if not JAR_PATH.exists():
        pytest.skip(f"Jar 文件不存在: {JAR_PATH}")

    upload_result = protocol_client.upload_jar(str(JAR_PATH))

    yield upload_result

@pytest.fixture
def protocol_instance(api_client, uploaded_jar_id, request):
    """
    Function 级：每个测试独立创建协议
    使用 request.node.name 动态生成协议名，确保唯一性
    """
    protocol_api = ProtocolClient()
    protocol_api.session = api_client.session
    protocol_api.headers = api_client.headers

    protocol_name = f"test_protocol_{int(time.time() * 1000)}"

    file_id = uploaded_jar_id['file_id']

    # 创建协议
    protocol_id = protocol_api.create_protocol(
        name=protocol_name,
        jar_file_id=file_id,  # 传入字符串 file_id
        jar_access_key=uploaded_jar_id.get('access_key'),
        jar_access_url=uploaded_jar_id.get('access_url')
    )

    # 等待端口就绪
    protocol_api.wait_for_port(1885)

    # 传递协议 ID 给测试用例（通过 fixture 返回或属性）
    request.addfinalizer(lambda: cleanup_protocol(protocol_api, protocol_id, protocol_name))

    return {
        "client": protocol_api,
        "protocol_id": protocol_id,
        "protocol_name": protocol_name
    }

def cleanup_protocol(protocol_api, protocol_id, protocol_name):
    """清理协议的辅助函数"""
    try:
        protocol_api.delete_protocol(protocol_id)
        print(f"协议 ‘{protocol_name}’ {protocol_id}已清理")
    except Exception as e:
        # 如果是 CI 环境或强制清理模式，打印警告但不抛异常
        print(f"协议清理失败（保留用于调试）：{e}")
        # raise  # 如果需要严格清理，取消注释

@pytest.fixture
def binding_client(api_client):
    # 创建 GatewayDeviceBindingClient 实例，并复用 api_client 的 session 和 headers
    binding_client = GatewayDeviceBindingClient()
    binding_client.session = api_client.session
    binding_client.headers = api_client.headers
    binding_client.token = api_client.token

    print("[Fixture] GatewayDeviceBindingClient instance created")
    yield binding_client
    # Teardown: 会话结束时执行
    print("[Fixture] GatewayDeviceBindingClient session finished.")

@pytest.fixture
def temp_binding(binding_client, create_mqtt_gateway, protocol_instance):
    """
    Function 级夹具：创建一个临时的网关绑定用于测试。
    自动创建所需的依赖资源（网关、协议），然后创建绑定。
    - 测试前：创建网关 -> 创建协议 -> 创建绑定
    - 测试后：自动删除绑定（网关和协议由各自的夹具清理）
    - 每个测试函数都会获得一个全新的、独立的绑定
    """
    global created_binding
    print("\n[Fixture] Creating a temporary binding with auto-created resources...")

    channel_id = create_mqtt_gateway # 网关ID作为channel_id
    protocol_id = protocol_instance['protocol_id']

    # 唯一名称
    unique_name = f"test_binding_{int(time.time() * 1000)}"
    # --- 创建绑定 ---
    # 需要提供有效的 protocol_id 和 channel_id

    created_binding = None
    try:
        # 创建绑定
        created_binding = binding_client.create_binding(
            name = unique_name,
            protocol_id = protocol_id,
            channel_id = channel_id,
            transport = "MQTT",
            description = "这是一个自动化测试创建的绑定体"
        )
        print(f"created binding:{created_binding}")
        binding_id = created_binding.get('result', {}).get('id')
        assert binding_id, "Failed to create binding, no ID return"
        print(f"[Fixture] 已创建绑定体: {binding_id}")
        print(f"  - Protocol ID: {protocol_id}")
        print(f"  - Channel ID: {channel_id}")

        # 将创建的绑定信息 yield 给测试函数
        yield created_binding

    finally:
        # --- 清理绑定 (Teardown) ---
        # 无论测试成功还是失败，finally 块中的代码都会执行
        if created_binding and created_binding.get('result', {}).get('id'):
            binding_id_to_delete = created_binding.get('result', {}).get('id')
            print(f"[Fixture] 根据ID删除绑定体中: {binding_id_to_delete}...")
            try:
                # 先禁用绑定体 之后才能删网关
                print("[Fixture] 正在禁用绑定体")
                disable_resp = binding_client.disable_binding(binding_id_to_delete)
                # 等待一下确保状态更新
                time.sleep(0.5)

                # 再开始删除绑定
                binding_client.delete_binding(binding_id_to_delete)
                print(f"[Fixture] 绑定体 {binding_id_to_delete} 删除成功")
            except Exception as e:
                # 如果删除失败，打印错误但不要让整个测试套件失败
                print(f"[Fixture] 警告：绑定体删除失败 {binding_id_to_delete}. 错误: {e}")

@pytest.fixture
def device_access_chain(api_client, create_product_fixture, temp_binding, product_write_api, product_read_api):
    """
    【核心聚合夹具】完整的设备接入链路（极简版）
    依赖：
    - create_product_fixture: 创建产品
    - temp_binding: 自动创建网关+协议+绑定

    流程：
    1. 创建产品
    2. 创建绑定（网关+协议自动创建）
    3. PATCH产品，关联绑定ID
    4. 创建设备
    """

    chain_data = {}
    create_device = None
    device_id = None
    try:
        # 获取产品和绑定
        product_id = create_product_fixture['id']
        product_name = create_product_fixture['name']
        chain_data['product_id'] = product_id
        print(f"[Step 1/6] 产品就绪：{product_id}")

        # 绑定信息 来自temp_binding
        # temp_binding 已经创建了网关、协议、绑定三层关系
        binding_id = temp_binding['result']['id']
        binding_info = temp_binding['result']

        print(f"[Step 2/6] 绑定就绪：{binding_id}")
        print(f" -网关ID：{binding_info.get('channelId')}")
        print(f"   - 协议ID: {binding_info.get('protocol')}")

        print(f"[Step 3/6] 正在将产品 {product_id} 绑定到接入网关 {binding_id}...")

        # 产品绑定设备接入网关(全字段，不然会返回500，设备产品无法启动)
        bind_payload  = {
            "id": product_id,
            "accessId": binding_info.get('channelId'),
            "accessName": binding_info.get('name'),
            "accessProvider": binding_info.get('provider'),
            "messageProtocol": binding_info.get('protocol'),
            "name": product_name,
            "transportProtocol": "MQTT",
            "protocolName": "topic",
            "metadata": "",
            "configMetadatas": [],
            "features": [ # 必须包含至少一个特性
                {"id": "eventNotInsertable", "name": "物模型事件不可新增", "type": "SimpleFeature", "deprecated": False}
            ]
        }

        # 调用 PATCH 方法
        update_resp = product_write_api.patch_product(bind_payload)

        if update_resp['status'] != 200:
            raise Exception(f"产品绑定接入网关失败：{update_resp}")

        print(f"产品已绑定接入网关")

        # 设置MQTT验证方式
        print(f"[Step 4/6] 设置MQTT验证方式...")

        # 可以硬编码或从配置中读取
        MQTT_SECURE_ID = "1111"
        MQTT_SECURE_KEY = "1111"
        chain_data['mqtt_username'] = MQTT_SECURE_ID
        chain_data['mqtt_password'] = MQTT_SECURE_KEY
        try:
            product_write_api.set_mqtt_auth(
                product_id = product_id,
                secure_id = MQTT_SECURE_ID,
                secure_key = MQTT_SECURE_KEY,
                secure_type = "plaintext"
            )
        except Exception as e:
            print(f"MQTT验证设置失败（可能产品已设置或找不到产品）：{e}")
            # 不阻断流程，继续执行

        print(f"[Step 5/6] 更新产品物模型...")

        # 构建物模型metadata
        metadata = {
            "properties":[
                {
                    "id": "temperature",
                    "name": "温度",
                    "expends":{
                        "source": "device",
                        "type": ["read","write","report"],
                        "groupId": "group_1",
                        "groupName": "分组_1",
                        "storageType": "ignore",
                        "otherEdit": True
                    },
                    "valueType": {"type": "float"}
                },
                {
                    "id": "humidity",
                    "name": "湿度",
                    "expends": {
                        "source": "device",
                        "type": ["read","write","report"],
                        "groupId": "group_1",
                        "groupName": "分组_1"
                    },
                    "valueType": {"type": "float"}
                },
                {
                    "id": "interval",
                    "name": "心跳间隔",
                    "expends": {
                        "source": "device",
                        "type": ["read","write","report"],
                        "groupId": "group_1",
                        "groupName": "分组_1"
                    },
                    "valueType": {"type": "int"}
                }
            ],
            "events": [],
            "actions": []
        }
        try:
            product_write_api.patch_product_metadata(
                product_id = product_id,
                metadata = metadata,
                name = product_name
            )
        except Exception as e:
            print(f"物模型更新异常（可能已设置）：{e}")

        # 启动产品(必须先绑定并设置接入方式)

        product_read_client = ProductReadApi("http://localhost:8848")
        product_read_client = api_client.session
        product_read_client.headers = product_read_client.headers

        product_write_client = ProductWriteApi()
        product_write_client.session = api_client.session
        product_write_client.headers = api_client.headers
        product_write_client.token = api_client.token

        product_write_client.deploy_product(product_id)

        product_detail_after_deploy = product_read_api.get_detail(column = "id", value = product_id)
        print(f"product_detail_after_deploy: {product_detail_after_deploy['result']}")
        product_detail = product_read_api.get_detail(product_id)
        print(f"product_detail:{product_detail}")

        print(f"[Step 6/6] 创建设备...")
        # 创建设备
        device_id = f"dev_full_{int(time.time() * 1000)}"
        create_device = DeviceClient()
        create_device.session = api_client.session
        create_device.headers = api_client.headers
        create_device.token = api_client.token
        create_resp = create_device.create_device(
            device_id = device_id,
            name = device_id,
            product_id = product_id
        )
        device_detail = create_device.get_device_detail(device_id)
        print(f"device_detail = {device_detail}")
        deploy_resp = create_device.deploy_device(device_id)
        if deploy_resp['message'] != 'success':
            raise Exception(f"启用设备失败")
        if create_resp['status'] != 200:
            raise Exception(f"设备创建失败：{create_resp}")
        time.sleep(0.5)
        print("设备启用成功！")
        chain_data['device_id'] = device_id
        print(f"[Step 6/6] 设备创建成功：{device_id}")

        yield chain_data
        device_undeploy_prep = create_device.undeploy_device(device_id)
        if device_undeploy_prep['status'] != 200 and device_undeploy_prep['message'] != 'success':
            raise Exception(f"错误：设备禁用失败：{device_undeploy_prep['status'], device_undeploy_prep['message']}")
        time.sleep(0.8)
        product_undeploy_resp = product_write_api.undeploy_product(product_id)
        if product_undeploy_resp['message'] != 'success' and product_undeploy_resp['status'] != 200:
            raise Exception(f"错误：产品禁用失败：{product_undeploy_resp['status']},{product_undeploy_resp['message']}")
        time.sleep(0.8)
    finally:
        if "device_id" in chain_data:
            try:
                create_device.undeploy_device({})
                time.sleep(0.5)
                create_device.delete_device(chain_data['device_id'])
                print(f"[Cleanup] 设备 {chain_data['device_id']} 已删除")
            except Exception as e:
                print(f"[Cleanup] 警告：设备删除失败：{e}")


@pytest.fixture
def mqtt_device_conn(api_client, device_access_chain, product_read_api):
    """
    MQTT设备连接夹具（增强版）
    """
    # 获取参数
    device_id = device_access_chain['device_id']
    product_id = device_access_chain['product_id']

    # API 获取通信账号密码
    print(f"\n[MQTT Fixture] 准备连接设备: {device_id}")
    print(
        f"[MQTT Fixture] 尝试使用 User: {device_access_chain.get('mqtt_username')}, Pass: {device_access_chain.get('mqtt_password')}")

    mqtt_username = device_access_chain.get('mqtt_username', device_id)  # 有些平台用户名是设备ID
    mqtt_password = device_access_chain.get('mqtt_password', '1111')  # 默认密码

    BROKER = "127.0.0.1"
    PORT = 1885

    client = mqtt.Client(client_id=device_id, clean_session=True)
    client.username_pw_set(username=mqtt_username, password=mqtt_password)

    message_queue = Queue()
    connection_event = threading.Event()
    connection_success = [False]
    time.sleep(2)
    def on_connect(client, userdata, flags, rc):
        print(f"[MQTT] 连接回调触发, rc={rc}")
        if rc == 0:
            print(f"[MQTT] 连接成功！")
            connection_success[0] = True
            connection_event.set()

            # ========== 立即发送一条遥测数据 ==========
            payload = {
                "properties": {
                    "temperature": 36.5,
                    "humidity": 60
                },
                "timestamp": int(time.time() * 1000)
            }

            topic_telemetry = f"/{product_id}/{device_id}/properties/report"
            topic_command = f"/{product_id}/{device_id}/command"

            # 订阅命令主题
            client.subscribe(topic_command)

            # 发布遥测数据
            client.publish(topic_telemetry, json.dumps(payload), qos=1)
            print(f"[MQTT] 已发送初始遥测数据")

            # ========== 启动心跳线程 ==========
            def heartbeat_thread():
                for i in range(2):  # 只发送2次心跳
                    if not client.is_connected():
                        break
                    try:
                        # 更新温度值（模拟变化）
                        payload['properties']['temperature'] = round(36.5 + i * 0.1, 1)
                        payload['timestamp'] = int(time.time() * 1000)

                        # 发布心跳
                        client.publish(topic_telemetry, json.dumps(payload), qos=1)
                        print(f"[MQTT] 心跳 #{i + 1}: temperature={payload['properties']['temperature']}")

                        time.sleep(5)  # 每5秒发送一次
                    except Exception as e:
                        print(f"[MQTT] 心跳线程异常: {e}")
                        break

                print(f"[MQTT] 心跳已发送2次，线程退出")

            # 启动守护线程
            heartbeat = threading.Thread(target=heartbeat_thread, daemon=True)
            heartbeat.start()
            print(f"[MQTT] 心跳线程已启动（将发送2次）")

        elif rc == 4:
            print(f"[MQTT] 认证失败！User='{mqtt_username}'")
            connection_event.set()
        else:
            print(f"[MQTT] 连接失败，rc={rc}")
            connection_event.set()

    client.on_connect = on_connect
    client.on_message = lambda c, u, msg: message_queue.put({
        "topic": msg.topic, "payload": msg.payload.decode("utf-8")
    })

    # 重试机制（解决时序问题）
    print(f"[MQTT] 发起连接...")
    time.sleep(8)
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    time.sleep(2)
    device_client = DeviceClient()
    device_client.session = api_client.session
    device_client.headers = api_client.headers
    device_detail = device_client.get_device_detail(device_id)
    print(f"device_detail: {device_detail['result']['state']}")
    product_detail = product_read_api.get_detail(product_id)
    print(f"product_detail: {product_detail}")
    # 等待连接结果，最多重试 3 次
    for attempt in range(3):
        if connection_event.wait(timeout=5):  # 每次等5秒
            break
        else:
            print(f"[MQTT] 第 {attempt + 1} 次尝试超时，正在重试...")
            # 重新连接尝试
            if not client.is_connected():
                client.reconnect()

    # 最终校验
    if not connection_success[0]:
        # 这里打印详细的调试信息
        print(f"\n[ERROR] MQTT 连接最终失败！")
        print(f"  - Device ID: {device_id}")
        print(f"  - Product ID: {product_id}")
        print(f"  - Broker: {BROKER}:{PORT}")
        print(f"  - Username: {mqtt_username}")
        print(f"  - Password: {mqtt_password}")
        print(f"\n[建议] 请检查：")
        print(f"  1. JetLinks 后台 -> 网关管理 -> MQTT网关 -> 接入配置 -> 认证方式")
        print(f"  2. 是否开启了 'Allow Anonymous'（如果是，请勿设置 username_pw_set）")
        print(f"  3. 设备是否处于 '启用' 状态（API创建后默认为'禁用'？）")

        pytest.fail(f"MQTT 连接失败，rc != 0。最后返回码参考日志。")

    print(f"[MQTT] 设备在线，开始测试...")
    # 返回连接对象和队列
    yield {
        "client": client,
        "queue": message_queue,
        "device_id": device_id,
        "product_id": product_id,
        "topic_telemetry": f"/{product_id}/{device_id}/properties/report",
        "topic_command": f"/{product_id}/{device_id}/command"
    }

    # Teardown
    client.loop_stop()
    client.disconnect()

@pytest.fixture
def alarm_id(api_client):
    """
    Function 级夹具：为每个测试函数创建一个独立的告警，并在测试结束后清理。
    - Setup: 创建一个新告警，并 yield 其 ID。
    - Teardown: 使用 yield 的 ID 禁用并删除该告警。
    """
    alarm_id_to_return = None
    alarm_client = None
    try:
        # 创建告警
        # 使用时间戳确保名称唯一，避免并发冲突
        alarm_client = AlarmClient()
        alarm_client.session = api_client.session
        alarm_client.headers = api_client.headers
        unique_name = f"test_alarm_{int(time.time() * 1000)}"
        create_payload = {

        }
        # 创建 alarm
        resp = alarm_client.create_alarm(
            level = 2,
            target_type = "device",
            name = unique_name,
            description = "这是一个由pytest fixture 自动创建的测试告警"
        )

        # 提取 ID 创建告警会返回ID（后端自动创建）
        alarm_id_to_return = resp.get('result', {}).get('id', None)
        if not alarm_id_to_return:
            pytest.fail(f"创建告警失败：未能获取到ID，响应：{resp}")

        print(f"[Alarm Fixture] 告警创建成功：ID：{alarm_id_to_return}")

        # yield ID 给用例
        yield alarm_id_to_return

    finally:
        # Teardown 无论成功失败都要清理
        if alarm_id_to_return:
            try:
                # 先禁用
                print(f"[Alarm Fixture] 正在禁用告警...")
                alarm_client.disable_alarm(alarm_id_to_return)
                print(f"[Alarm Fixture] 告警已禁用")
            except Exception as e:
                # 即使禁用失败（例如告警已被禁用），也继续尝试删除
                print(f"[Alarm Fixture] 警告：禁用高警出现异常：{e}，将尝试继续删除")

            try:
                # 后删除
                print(f"[Alarm Fixture] 正在删除告警...")
                alarm_client.delete_alarm(alarm_id_to_return)
                print(f"[Alarm Fixture] 告警已删除")
            except Exception as e:
                # 如果删除也失败，在测试报告中标记为警告，但不要让 teardown 失败
                # 因为测试本身可能已经失败了
                pytest.fail(f"清理告警（ID：{alarm_id_to_return}）失败！请手动清理。错误：{e}")
        else:
            print(f"\n[Alarm Fixture] 未创建告警，无需清理。")

@pytest.fixture
def scene_with_device_access(api_client, device_access_chain):
    """
    【场景联动夹具】基于设备接入链路创建场景
    依赖：
    - device_access_chain: 完整的设备接入链路（提供product_id和device_id）

    流程：
    1. 从device_access_chain获取product_id和device_id
    2. 创建并配置场景（使用设备和产品信息）
    3. Teardown: 尝试禁用场景 -> 删除场景

    注意：device_access_chain的清理会独立处理设备和产品的删除
    """

    scene_id = None
    scene_data = {}
    scene_client = None
    try:
        # 从设备接入链路获取必要信息
        product_id = device_access_chain['product_id']
        device_id = device_access_chain['device_id']

        print(f"创建场景联动产品ID：{product_id}，设备ID：{device_id}")

        # 创建SceneClient实例（复用api_client的session）
        scene_client = SceneClient()
        scene_client.session = api_client.session
        scene_client.headers = api_client.headers

        # 创建并配置场景
        # 使用设备ID作为device_name，产品ID作为product_id
        result = scene_client.create_and_configure_scene(
            scene_name = f"高温告警{device_id}",
            device_id = device_id,
            product_id = product_id,
            high_temp_threshold = 60,
            high_temp_interval = 2,
            low_temp_threshold = 50,
            low_temp_interval = 5
        )

        scene_id = result['id']
        scene_data = {
            'id': scene_id,
            'name': result['name'],
            "device_id": device_id,
            "product_id": product_id,
            "status": "started"
        }

        print(f"场景创建成功，ID：{scene_id}")
        print(f"场景已启用，监控设备ID：{device_id}")
        # 默认禁用场景，因此在这里先启用
        scene_client.enable_scene(scene_id)
        yield scene_data

    except Exception as e:
        print(f"创建场景时出现错误！{e}")
        raise

    finally:
        # Teardown 清理场景
        if scene_id:
            try:
                # 先禁用场景
                disable_resp = scene_client.disable_scene(scene_id)
                assert disable_resp['message'] == "success", f"禁用场景失败：{disable_resp['message']}"
                print("场景禁用成功")
                time.sleep(0.5)
            except Exception as e:
                print(f"禁用场景错误，可能已禁用：{e}")

            try:
                # 后删除场景
                delete_resp = scene_client.delete_scene(scene_id)
                assert delete_resp['message'] == 'success', f"删除场景失败：{delete_resp['message']}"
                print("场景删除成功")
            except Exception as e:
                print(f"删除场景错误：{e}")

@pytest.fixture
def mqtt_device_simulator(scene_with_device_access):
    """
    MQTT 设备模拟器（被动模式，完全由平台规则驱动）
    - 初始心跳 5 秒，45°C 开始升温
    - 温度到 60°C 等待 interval=2，进入降温
    - 温度到 50°C 等待 interval=5，进入再升温
    - 温度到 65°C 自动停止
    - 每次上报温度时夹具自行打印，测试侧无需轮询打印
    """

    import socket
    import time

    def wait_for_broker(host, port, timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.create_connection((host, port), timeout=1):
                    return True
            except (ConnectionRefusedError, OSError):
                time.sleep(1)
        raise TimeoutError(f"Broker {host}:{port} 未就绪")

    product_id = scene_with_device_access['product_id']
    device_id = scene_with_device_access['device_id']

    BROKER = "127.0.0.1"
    PORT = 1885
    USERNAME = "1111"
    PASSWORD = "1111"
    CLIENT_ID = device_id

    device_state = {
        "temperature": 45.0,
        "interval": 5.0,
        "direction": "increasing",
        "is_running": True,
        "waiting_for_command": False,
        "expect_interval": None,
        "phase": "initial"
    }

    client = mqtt.Client(client_id=CLIENT_ID)
    client.username_pw_set(USERNAME, PASSWORD)

    thread_control = {
        'client_thread': None,
        'stop_event': threading.Event(),
        'first_report_event': threading.Event(),
    }

    def on_message(client, userdata, msg):
        """处理平台下发的属性修改指令"""
        print(f"\n[下行] Topic: {msg.topic}")
        print(f"[下行] 消息: {msg.payload.decode('utf-8')}")
        try:
            payload_in = json.loads(msg.payload.decode('utf-8'))
            message_id = payload_in.get('messageId')
            properties = payload_in.get('properties', {})
            if not message_id:
                print("[警告] 缺少 messageId")
                return

            reply = {
                "timestamp": int(time.time() * 1000),
                "messageId": message_id,
                "properties": properties,
                "success": True
            }

            if 'interval' in properties:
                new_interval = properties['interval']
                if not (isinstance(new_interval, (int, float)) and new_interval > 0):
                    print(f"[错误] 无效间隔: {new_interval}")
                    reply["success"] = False
                else:
                    print(f"[指令] 间隔修改: {new_interval}s")
                    old_interval = device_state['interval']

                    # 阶段1：初始升温，等待 interval=2
                    if device_state['phase'] == 'initial' and device_state['waiting_for_command']:
                        if new_interval == 2.0:
                            print("[阶段] 收到 2s → 降温阶段")
                            device_state['interval'] = 2.0
                            device_state['direction'] = 'decreasing'
                            device_state['waiting_for_command'] = False
                            device_state['phase'] = 'cooling'
                        else:
                            print(f"[提示] 等待 2，但收到 {new_interval}，仅更新间隔")
                            device_state['interval'] = float(new_interval)

                    # 阶段2：降温，等待 interval=5
                    elif device_state['phase'] == 'cooling' and device_state['waiting_for_command']:
                        if new_interval == 5.0:
                            print("[阶段] 收到 5s → 再升温阶段")
                            device_state['interval'] = 5.0
                            device_state['direction'] = 'increasing'
                            device_state['waiting_for_command'] = False
                            device_state['phase'] = 'reheating'
                        else:
                            print(f"[提示] 等待 5，但收到 {new_interval}，仅更新间隔")
                            device_state['interval'] = float(new_interval)

                    # 阶段3：再升温阶段，忽略非 5 的指令
                    elif device_state['phase'] == 'reheating':
                        if new_interval != 5.0:
                            print(f"[警告] 再升温阶段忽略 interval={new_interval}，保持 5s")
                            reply["success"] = False  # 可选：告知平台拒绝
                        else:
                            print("[提示] 再升温阶段保持 interval=5")
                    # 其他状态：直接应用
                    else:
                        if new_interval != old_interval:
                            device_state['interval'] = float(new_interval)
                            print(f"[间隔] {old_interval}s → {new_interval}s")
                        else:
                            print(f"[间隔] 未变化，仍为 {device_state['interval']}s")

            # 上行回复
            reply_topic = f"/{product_id}/{CLIENT_ID}/properties/write/reply"
            client.publish(reply_topic, json.dumps(reply), qos=1)
            print("[回复] 已发送")

        except Exception as e:
            print(f"[异常] on_message: {e}")

    def on_connect(client, userdata, flags, rc):
        print(f"[连接] 结果码: {rc}")
        if rc == 0:
            print("设备已连接")
            downlink = f"/{product_id}/{CLIENT_ID}/properties/write"
            client.subscribe(downlink, qos=1)
            print(f"已订阅: {downlink}")

            topic = f"/{product_id}/{CLIENT_ID}/properties/report"
            # 首报
            payload = {
                "properties": {"temperature": device_state['temperature'], "humidity": 60},
                "timestamp": int(time.time() * 1000)
            }
            client.publish(topic, json.dumps(payload), qos=1)
            print(f"首报: 温度={device_state['temperature']}°C")

            thread_control['first_report_event'].set()

            def state_machine():
                print("[状态机] 启动")
                while device_state['is_running'] and not thread_control['stop_event'].is_set():
                    if device_state['waiting_for_command']:
                        time.sleep(1)
                        continue

                    # 更新温度
                    if device_state['direction'] == 'increasing':
                        device_state['temperature'] += 1.0
                    else:
                        device_state['temperature'] -= 1.0
                    device_state['temperature'] = round(device_state['temperature'], 1)

                    # 上报
                    report = {
                        "properties": {
                            "temperature": device_state['temperature'],
                            "humidity": 60
                        },
                        "timestamp": int(time.time() * 1000)
                    }
                    try:
                        client.publish(topic, json.dumps(report), qos=1)
                        # 关键改动：每次上报后立即打印温度
                        print(f"[上报] 温度: {device_state['temperature']}°C, "
                              f"方向: {device_state['direction']}, "
                              f"间隔: {device_state['interval']}s, "
                              f"阶段: {device_state['phase']}")
                    except Exception as e:
                        print(f"[上报失败] {e}")

                    # 阶段判定
                    if device_state['phase'] == 'initial' and device_state['temperature'] >= 60.0:
                        print(f"温度达到 {device_state['temperature']}°C，等待平台下发 interval=2")
                        device_state['waiting_for_command'] = True
                        device_state['expect_interval'] = 2
                    elif device_state['phase'] == 'cooling' and device_state['temperature'] <= 50.0:
                        print(f"温度降至 {device_state['temperature']}°C，等待平台下发 interval=5")
                        device_state['waiting_for_command'] = True
                        device_state['expect_interval'] = 5
                    elif device_state['phase'] == 'reheating' and device_state['temperature'] >= 65.0:
                        print(f"温度达到 {device_state['temperature']}°C，模拟结束")
                        client.publish(topic, json.dumps(report), qos=1)
                        thread_control['stop_event'].set()
                        break

                    time.sleep(device_state['interval'])

            thread_control['client_thread'] = threading.Thread(target=state_machine, daemon=True)
            thread_control['client_thread'].start()
        else:
            print(f"连接失败，错误码: {rc}")

    client.on_connect = on_connect
    client.on_message = on_message

    # ---------- 启动（带重试） ----------
    print(f"[启动] 连接 {BROKER}:{PORT}，ClientID={CLIENT_ID}")
    wait_for_broker(BROKER, PORT)
    print("[启动] 等待平台内部服务同步（5秒）...")
    time.sleep(5)

    max_connect_retries = 5
    connection_ok = False
    last_rc = None

    for attempt in range(1, max_connect_retries + 1):
        print(f"[连接] 第 {attempt}/{max_connect_retries} 次尝试...")

        connection_result_event = threading.Event()
        connection_rc = None

        def on_connect_with_result(client, userdata, flags, rc):
            nonlocal connection_rc
            connection_rc = rc
            connection_result_event.set()

        client.on_connect = on_connect_with_result

        try:
            client.connect(BROKER, PORT, 60)
        except Exception as e:
            print(f"[连接] TCP 连接失败: {e}")
            time.sleep(2)
            continue

        client.loop_start()

        # 等待 CONNACK，最多 10 秒
        if not connection_result_event.wait(timeout=10):
            print("[连接] 未收到 CONNACK，重试...")
            client.loop_stop()
            time.sleep(2)
            continue

        last_rc = connection_rc
        if connection_rc == 0:
            connection_ok = True
            print("[连接] MQTT 连接成功 (rc=0)")
            # 连接成功后立刻触发原有 on_connect 逻辑（订阅、首报、状态机）
            # 注意：on_connect 内部会启动 first_report_event，但这里我们还需要确保它被调用一次
            # 因为 on_connect 在 on_connect_with_result 里调用了，所以不需要重复调用
            break
        else:
            print(f"[连接] 连接被拒绝，错误码: {connection_rc}")
            client.loop_stop()
            time.sleep(2)
            continue

    if not connection_ok:
        raise ConnectionError(f"MQTT 连接失败，最后错误码: {last_rc}")

    # 原有 on_connect 已经在 on_connect_with_result 中被调用，这里只需等待首条上报
    if not thread_control['first_report_event'].wait(timeout=15):
        raise TimeoutError("设备已连接但未在 15 秒内完成首条属性上报")

    print("[就绪] MQTT 设备模拟器已就绪")
    yield {
        "client": client,
        "device_state": device_state,
        "product_id": product_id,
        "device_id": device_id,
        "thread_control": thread_control
    }

    # ---------- 清理 ----------
    print("[清理] 停止模拟器")
    thread_control['stop_event'].set()
    if thread_control['client_thread'] and thread_control['client_thread'].is_alive():
        thread_control['client_thread'].join(timeout=5)
    try:
        client.loop_stop()
        client.disconnect()
    except:
        pass
    print("[清理] 完成")

@pytest.fixture
def batch_devices_for_load(api_client, create_product_fixture, temp_binding,
                           product_write_api, product_read_api, request):
    """
    批量创建用于压测的设备，返回设备ID列表，测试结束后自动清理。
    依赖已有的产品、绑定、物模型等基础设施（由其他 fixture 提供），避免重复创建。

    可通过 pytest.mark.parametrize 间接控制数量，或直接修改 DEVICE_COUNT。
    """
    DEVICE_COUNT = getattr(request, 'param', 100)  # 默认100，可通过参数化修改

    product_id = create_product_fixture['id']
    product_name = create_product_fixture['name']
    binding_info = temp_binding['result']
    binding_id = binding_info['id']

    # ---------- 复用 device_access_chain 中的步骤 3~5 ----------
    # 产品绑定接入网关
    bind_payload = {
        "id": product_id,
        "accessId": binding_info.get('channelId'),
        "accessName": binding_info.get('name'),
        "accessProvider": binding_info.get('provider'),
        "messageProtocol": binding_info.get('protocol'),
        "name": product_name,
        "transportProtocol": "MQTT",
        "protocolName": "topic",
        "metadata": "",
        "configMetadatas": [],
        "features": [
            {"id": "eventNotInsertable", "name": "物模型事件不可新增",
             "type": "SimpleFeature", "deprecated": False}
        ]
    }
    product_write_api.patch_product(bind_payload)

    # MQTT 认证
    try:
        product_write_api.set_mqtt_auth(
            product_id=product_id,
            secure_id="1111",
            secure_key="1111",
            secure_type="plaintext"
        )
    except Exception as e:
        print(f"[批量设备] MQTT认证设置失败（可能已存在）: {e}")

    # 物模型
    metadata = {
        "properties": [
            {"id": "temperature", "name": "温度",
             "expends": {"source": "device", "type": ["read","write","report"],
                         "groupId": "group_1", "groupName": "分组_1", "storageType": "ignore"},
             "valueType": {"type": "float"}},
            {"id": "humidity", "name": "湿度",
             "expends": {"source": "device", "type": ["read","write","report"],
                         "groupId": "group_1", "groupName": "分组_1"},
             "valueType": {"type": "float"}},
            {"id": "interval", "name": "心跳间隔",
             "expends": {"source": "device", "type": ["read","write","report"],
                         "groupId": "group_1", "groupName": "分组_1"},
             "valueType": {"type": "int"}}
        ],
        "events": [], "actions": []
    }
    product_write_api.patch_product_metadata(product_id=product_id, metadata=metadata, name=product_name)

    # 部署产品
    product_write_api.deploy_product(product_id)

    # ---------- 批量创建设备 ----------
    device_ids = []
    device_client = DeviceClient()
    device_client.session = api_client.session
    device_client.headers = api_client.headers
    device_client.token = api_client.token

    for i in range(DEVICE_COUNT):
        device_id = f"load_{int(time.time() * 1000)}_{i}"
        try:
            resp = device_client.create_device(device_id=device_id, name=device_id, product_id=product_id)
            if resp.get('status') != 200:
                print(f"创建设备失败 {device_id}: {resp}")
                continue
            deploy_resp = device_client.deploy_device(device_id)
            if deploy_resp.get('message') != 'success':
                print(f"启用设备失败 {device_id}: {deploy_resp}")
                continue
            device_ids.append(device_id)
        except Exception as e:
            print(f"设备 {device_id} 创建异常: {e}")

    print(f"[批量设备] 成功创建 {len(device_ids)} 个设备（目标 {DEVICE_COUNT}）")
    yield device_ids

    # ---------- 清理：仅删除自己创建的所有设备 ----------
    for device_id in device_ids:
        try:
            device_client.undeploy_device(device_id)
            time.sleep(0.3)
            device_client.delete_device(device_id)
        except Exception as e:
            print(f"[批量清理] 设备 {device_id} 清理失败: {e}")