import pytest
from test_jetlinks.common.api_client import ProductWriteApi, DeviceClient
import time

from test_jetlinks.conftest import product_read_api


def test_prod(api_client, product_write_api):
    product_id = f"test_prod_{int(time.time() * 1000)}"
    product_resp = product_write_api.create_product_function(
        name = product_id,
        id  = product_id,
        classifiedId = "-222-",
        classifiedName = "智能电力",
        deviceType = "device",
        describe = "11111"
    )
    device_client = DeviceClient()
    device_client.session = api_client.session
    device_client.headers = api_client.headers
    device_deploy_resp = device_client.deploy_device("111")


    # ... [前面的代码保持不变] ...

    # 绑定产品后，更新物模型
    print(f"[Step 4/6] 更新产品物模型...")

    # 构造物模型metadata（示例）
    metadata = {
        "properties": [
            {
                "id": "temperature",
                "name": "温度",
                "expands": {
                    "source": "device",
                    "type": ["report"],
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
                "expands": {
                    "source": "device",
                    "type": ["report"],
                    "groupId": "group_1",
                    "groupName": "分组_1"
                },
                "valueType": {"type": "float"}
            }
        ],
        "events": [],
        "actions": []
    }
    try:
        product_write_api.patch_product_metadata(
            product_id=product_id,
            metadata=metadata,
            name = product_id  # 可选：同时更新名称
        )

    except Exception as e:
        print(f"物模型更新异常（可能已设置）: {e}")

