import os
import socket
import time
import uuid

import requests
import json
from typing import Optional, Dict, Any

import requests.exceptions


class APIClient:
    """统一的 API 客户端封装"""

    def __init__(self, base_url = "http://localhost:8848"):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.headers = {
            "Content-Type" : "application/json" # 向服务器声明发送数据的格式
        }

    def login(self, username, password):
        """
        登录接口封装
        :return: access_token
        """
        url = f"{self.base_url}/authorize/login"
        payload = {
            "username": username,
            "password": password,
            "expires": 360000,
            "remember": False
        }

        try:
            resp = self.session.post(url, json=payload)
            resp.raise_for_status()  # 这里会抛出 HTTPError

            data = resp.json()

            # 检查业务状态
            success = data.get('success')
            if success is False:
                message = data.get('message', '登录失败')
                raise Exception(message)

            result = data.get('result', {})
            self.token = result.get('token')

            if not self.token:
                raise Exception(f"登录失败，未返回Token。响应: {resp.text}")

            self.headers["Authorization"] = f"Bearer {self.token}"
            print(f"登录成功， Token已注入Header")
            return self.token

        except requests.exceptions.RequestException as e:
            # 捕获所有 requests 相关的异常（包括 HTTPError）
            error_msg = f"请求失败: {e}"
            # 尝试解析响应体
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_detail = e.response.json().get('message', '')
                    if error_detail:
                        error_msg = error_detail
            except:
                pass
            raise Exception(error_msg)

        except Exception as e:
            # 其他所有异常
            raise Exception(f"登录失败: {e}")

    def request(self, method, endpoint, **kwargs):
        """
        统一请求方法，自动携带 Token
        :param method: GET/POST/PUT/PATCH/DELETE
        :param endpoint: API 路径，如 /device-product/_query
        :param kwargs: json, params, headers 等
        """
        url = f"{self.base_url}{endpoint}"
        final_headers = self.headers.copy() # 创建一个新的字典 方便复用请求头
        if 'headers' in kwargs:
            final_headers.update(kwargs.pop('headers'))

        try:
            resp = self.session.request(method, url, headers = final_headers, **kwargs)
            # 特殊处理：DELETE 请求的 404 不视为错误（资源不存在是正常业务场景）
            if method in ['DELETE', 'PUT'] and resp.status_code == 404:
                return resp.json()
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求失败[{method}{endpoint}:{e}]")

    def get(self, endpoint, **kwargs):
        return self.request("GET", endpoint, **kwargs)

    def post(self, endpoint, **kwargs):
        return self.request("POST", endpoint, **kwargs)

    def put(self, endpoint, **kwargs):
        return self.request("PUT", endpoint, **kwargs)

    def delete(self, endpoint, **kwargs):
        return self.request("DELETE", endpoint, **kwargs)

    def patch(self, endpoint, **kwargs):
        return self.request("PATCH", endpoint, **kwargs)

    # ==================== 产品接口 ====================
    def create_product_function(self, name, classifiedId, classifiedName, deviceType, describe, photoUrl = "/assets/device-product.png", id = None):
        """
        创建产品接口封装
        """
        if id:
            print("检查该ID是否已存在")

            # 调用 base_url/{id}/exists接口看该ID是否存在 若存在则ID重复
            exists_url = f"/device-product/{id}/exists"
            try:
                resp = self.get(endpoint = exists_url)

                if resp.get('result') is True:
                    raise Exception(f"创建失败：产品ID[{id}]已被占用！")
                else:
                    print(f"ID[{id}]可用")
            except Exception as e:
                # 如果 exists 接口本身挂了（比如500），也要让测试停下来
                raise Exception(f"ID校验接口异常：{e}")

        # 通过校验后：
        endpoint = "/device-product"
        payload = {
            "name" : name,
            "classifiedId" : classifiedId,
            "classifiedName" : classifiedName,
            "deviceType" : deviceType,
            "describe" : describe,
            "photoUrl" : photoUrl
        }

        if id:
            payload['id'] = id
        # 打印最终发送的内容
        print(f"发送创建请求：{json.dumps(payload, ensure_ascii = False, indent = 2)}")

        # 发送请求
        try:
            resp  = self.post(endpoint, json = payload)

            # 统一业务断言
            if resp.get('success') is False:
                raise Exception(f"业务报错：{resp.get('message', '未知错误')}")

            result_data = resp.get('result', {})
            if not result_data:
                raise Exception("创建成功但未返回ID")

            print(f"创建成功！产品ID：{result_data.get('id')}")
            return result_data
        except Exception as e:
            print(f"创建失败：{e}")
            raise

    def delete_product(self, product_id):
        """
        删除产品接口封装
        :param product_id: 要删除的产品ID
        """
        endpoint = f"/device-product/{product_id}"

        print(f"正在删除产品，ID：{product_id}")

        try:
            # DELETE 请求 无需json参数
            resp = self.delete(endpoint = endpoint)

            if resp.get('success') is False:
                if "404" in str(resp.get('status')) or "not found" in str(resp.get('message', '')).lower():
                    print(f"产品{product_id}不存在，无需删除")
                    return True
                raise Exception(f"删除失败：{resp.get('message')}")
            print(f"产品{product_id}删除成功")
            return True
        except Exception as e:
            print(f"删除异常：{e}")
            raise

    def get_device_latest_properties(self, device_id):
        """获取设备最新属性（通过 HTTP API）"""
        resp = self.get(f"/api/v1/device/{device_id}/properties/latest")
        assert resp.status_code == 200, f"查询设备属性失败: {resp.text}"
        data = resp.json()
        # 根据实际返回结构解析，常见结构：{"result": {"temperature": 60.5, ...}}
        return data.get('result', data)

class ProductReadApi(APIClient):
    """
    产品模块 API 封装（继承自 APIClient）
    专注于 Read (查询) 相关接口
    """

    def __init__(self, base_url = "http://localhost:8848", username = None, password = None):
        super().__init__(base_url)
        # 如果传入了账号密码，初始化时自动登录
        if username and password:
            self.login(username, password)

    # 搜索接口
    def search(self, page_index = 0, page_size = 12, terms = None, sorts = None):
        """
        封装产品搜索接口
        :param page_index: 页码
        :param page_size: 每页数量
        :param terms: 搜索条件列表 (List[Dict])，例如:
                        [{"column": "name", "termType": "like", "value": "%test%", "type": "or"}]
        :param sorts: 排序规则列表 (List[Dict])，例如:
                        [{"name": "createTime", "order": "desc"}]
        :return: API 响应 JSON
        """
        endpoint = "/device-product/_query"
        payload = {
            "pageIndex": page_index,
            "pageSize": page_size,
            "terms": terms if terms else [],
            "sorts": sorts if sorts else []
        }
        return self.post(endpoint, json = payload)

    # 产品详情接口
    def get_detail(self, column = "id", value = None):
        """
        根据 ID 获取产品详情
        :param value：具体查询的值
        :param column: 查询方式
        :return: API 响应 JSON
        """
        endpoint = f"/device-product/_query"
        payload = {
            "pageSize": 1,
            "terms": [{"column": column, "value": value}]
        }
        return self.post(endpoint, json = payload)

    # 无过滤列表接口（复用搜索）
    def list_all(self, page_index = 0, page_size = 12, sorts = None):
        """
        获取无过滤条件的产品列表（默认列表）
        :param sorts: 排序规则
        :param page_index: 页码
        :param page_size: 每页数量
        :return: API 响应 JSON
        """
        return self.search(page_index = page_index, page_size = page_size, sorts = sorts)

    # 字典数据接口（下拉选项）
    def get_dict(self):
        """
        获取字典数据（如网关类型、设备类型）
        :param dict_type: 字典类型字符串，如 "gatewayType", "deviceType"
        :return: API 响应 JSON
        """
        endpoint = f"/gateway/device/providers"
        return self.get(endpoint = endpoint)

class ProductWriteApi(APIClient):
    """产品写操作封装"""

    def _assert_success(self, resp, action_name):
        """
        统一校验业务状态码
        :param resp: API返回的JSON
        :param action_name: 操作名称（用于报错信息）
        :raises Exception: 当业务状态不为200或success=false时抛出异常
        """
        if resp is None:
            raise Exception(f"[{action_name}]响应为空，可能网络断开")

        # 校验HTTP状态码
        status_code = resp.get('status')
        if status_code != 200:
            raise Exception(f"[{action_name}]HTTP状态码异常：{status_code} 响应：{resp}")

        # 校验业务 message 字段
        message = resp.get('message')
        if message != 'success':
            raise Exception(f"[{action_name}] 业务逻辑失败：{message}")

        # 校验result是否存在（针对有返回体的接口）
        # 删除接口可能没有result，根据实际情况调整
        if 'result' not in resp and action_name not in ['删除产品']:
            pass

        return resp

    def delete_my_product(self, product_id):
        """删除产品"""
        endpoint = f"/device-product/{product_id}"

        try:
            resp = self.delete(endpoint)
            print(f"resp:{resp}")
            if resp.get('status') == 404:
                print(f"产品{product_id}不存在，无需删除")
                return resp

            if resp['message'] != 'success':
                raise Exception(f"业务报错：{resp['message']}")

            print(f"删除成功：{product_id}")
            return resp

        except Exception as e:
            print(f"删除失败：{e}")
            raise

    def update_product(self, product_id, updata_data):
        """
        编辑/修改产品信息
        :param product_id: 产品ID
        :param update_data: 要修改的字段字典
        :return: API 响应 JSON
        """
        endpoint = f"/device-product/{product_id}"

        # 确保 update_data 包含id字段（接口要求）
        if "id" not in updata_data:
            updata_data["id"] = product_id

        try:
            resp = self.put(endpoint, json = updata_data)

            # 检查业务状态
            if resp.get('success') is False:
                raise Exception(f"业务报错：{resp.get('message', '未知错误')}")

            # 检查 HTTP 状态码
            if resp.get('status') not in [200, 201]:
                raise Exception(f"HTTP状态码异常：{resp.get('status')}")

            print(f"修改成功：产品{product_id}")
            return resp

        except Exception as e:
            print(f"修改失败:{e}")
            raise

    def patch_product(self, payload):
        """
        PATCH: 部分更新产品
        适用于：绑定网关、修改单个字段、增量更新等场景
        """
        endpoint = f"/device-product"

        try:
            resp = self.patch(endpoint, json = payload)

            # 检查业务状态
            if resp['message'] != 'success':
                raise Exception(f"业务报错：{resp['message']}")

            # 检查HTTP状态码
            if resp['status'] not in [200, 201]:
                raise Exception(f"HTTP状态码异常：{resp['status']}")

            print(f"PATCH成功：产品{payload['id']}")
            return resp

        except Exception as e:
            print(f"PATCH失败：{e}")
            raise

    def check_product_exist_by_query(self, product_id):
        """
        通过 _query 接口检查产品是否存在
        :param product_id: 产品ID
        :return: True/False
        """
        endpoint = f"/device-product/{product_id}"
        payload = {
            "pageSize": 1,
            "terms": [{"column": "id", "value": product_id}]
        }

        try:
            resp = self.post(endpoint, json = payload)

            if resp.get('message') is not 'success':
                raise Exception(f"业务报错：{resp}")

            # total == 1为存在 为0 不存在
            return resp['result']['total'] == 1

        except Exception as e:
            print(f"检查存在失败：{e}")
            raise

    def set_mqtt_auth(self, product_id, secure_id, secure_key, secure_type = "plaintext"):
        """
        【新增】设置产品MQTT验证方式
        PUT /device-product/{product_id}
        """
        endpoint = f"/device-product/{product_id}"

        payload = {
            "id": product_id,
            "configuration":{
                "secureType": secure_type,
                "secureId": secure_id,
                "secureKey": secure_key
            },
            "storePolicy": "timescaledb-column"
        }

        try:
            resp = self.put(endpoint, json = payload)

            if resp.get('status') != 200:
                raise Exception(f"设置MQTT验证方式失败：{resp.get('message')}")

            print(f"产品{product_id}MQTT验证方式已设置")
            return resp

        except Exception as e:
            print(f"设置MQTT验证失败：{e}")
            raise

    def deploy_product(self, product_id):
        """启用/部署设备 (POST)"""
        resp = self.post(f"/device-product/{product_id}/deploy", json = {})
        return self._assert_success(resp, "启动产品")

    def undeploy_product(self, product_id):
        """禁用设备 (POST)"""
        resp = self.post(f"/device-product/{product_id}/undeploy", json = {})
        return self._assert_success(resp, "禁用产品")

    def patch_product_metadata(self, product_id, metadata, **kwargs):
        """
        专门用于更新产品物模型（metadata）的PATCH方法

        :param product_id: 产品ID
        :param metadata: 物模型metadata字符串或字典
        :param kwargs: 其他需要更新的产品字段（可选）
                    例如: name, classifiedId, deviceType 等
        :return: API 响应 JSON

        使用示例:
            metadata = {
                "properties": [{
                    {
                        "id": "temperature",
                        "name": "温度",
                        "expands": {
                            "source": "device",
                            "type": ["read","write","report"],
                            "groupId": "group_1",
                            "groupName": "分组_1",
                            "storageType": "ignore",
                            "otherEdit": True
                        },
                        "valueType": {"type": "float"}
                    }
                ]
            }
            product_write_api.patch_product_metadata(
                product_id="prod_003",
                metadata=metadata,
                name="新产品名称"  # 可选：同时更新其他字段
            )
        """
        endpoint = f"/device-product"

        # payload，至少包含id和metadata
        payload = {
            "id": product_id,
            "metadata": metadata if isinstance(metadata, str) else json.dumps(metadata, ensure_ascii = False)
        }

        if kwargs:
            payload.update(kwargs)

        try:
            resp = self.patch(endpoint, json = payload)

            # 统一校验
            self._assert_success(resp, "更新产品物模型")

            # 额外检查result字段
            if 'result' in resp:
                result = resp['result']
                print(f"更新统计：add = {result.get('added', 0)}，update = {result.get('updated', 0)}, total = {result.get('total', 0)}")

            print(f"产品{product_id}物模型更新成功")
            return resp

        except Exception as e:
            print(f"物模型更新失败：{e}")
            raise

# 网关接口封装
class NetworkConfigApi(APIClient):
    """
    网络配置/网关接口封装
    专注于 /network/config 路径
    继承自 APIClient，自动拥有登录和请求能力
    """

    def __init__(self, base_url: str = "http://localhost:8848"):
        """
        初始化网关API
        :param base_url: API基础地址
        """
        super().__init__(base_url)

    def _assert_response_success(self, response: Dict[str, any], endpoint: str, method: str):
        """
        私有辅助方法，用于断言API响应是否成功
        :raises Exception: 如果响应状态或业务逻辑指示失败
        """
        status = response.get('status')
        success = response.get('success')
        message = response.get('message')

        if status is None:
            raise Exception(f"响应中缺少 'status' 字段：{response}")

        # 检查 HTTP 状态码 (JetLinks 成功通常返回 200)
        if not (200 <= status < 300):
            raise Exception(f"API请求失败[{method} {endpoint}] - HTTP状态码：{status}，消息：{message}")

        # 对于 DELETE 操作，成功时可能没有 'result' 字段
        if 'result' not in response and method == 'DELETE':
            pass # 可接受
        elif 'result' not in response and method in ['DELETE', 'POST', 'PUT', 'PATCH']:
            # 对于GET和需要返回数据的POST，缺少result是异常
            if method == 'GET':
                raise Exception(f"API缺少 'result' 字段：{response}")

    def create_mqtt_gateway(self, name, port = 1885, host = "0.0.0.0", public_port = 1885, public_host = "127.0.0.1"):
        """
        创建 MQTT Server 类型的网关配置
        :param name: 网关名称 (唯一标识)
        :param port: 服务端口
        :param host: 绑定主机
        :param public_port: 公网映射端口 (用于设备连接)
        :param public_host: 公网IP/域名
        :return: API 响应 JSON
        """
        endpoint = "/network/config"

        # 构造配置体
        payload = {
            "name": name,
            "type": "MQTT_SERVER", # 固定类型
            "shareCluster": True, # 通常集群环境下需要
            "description": f"Auto-created MQTT Gateway for {name}",
            "configuration":{
                "secure": False, # TSL/SSL
                "maxMessageSize": 8192,
                "publicPort": public_port,
                "publicHost": public_host,
                "port": port,
                "host": host
            }
        }

        print(f"[GatewayAPI] 正在创建网关：{name}")
        print(f"[GatewayAPI] payload:{json.dumps(payload, indent = 2, ensure_ascii = False)}")

        try:
            resp = self.post(endpoint, json = payload)

            # 业务校验
            if resp.get('success') is False:
                # 如果是名称重复等业务错误
                raise Exception(f"业务报错：{resp.get('message', '未知错误')}")

            # HTTP校验码
            if resp.get('status') not in [200, 201]:
                raise Exception(f"HTTP状态码异常：{resp.get('status')}")

            result = resp.get('result', {})
            if not result or not result.get('id'):
                raise Exception("创建成功但未返回网关ID")

            gateway_id = result.get('id')
            print(f"[GatewayAPI] 网关创建成功！ID: {gateway_id}")
            return resp

        except requests.exceptions.RequestException as e:
            raise Exception(f"API请求失败：[POST {endpoint}]: {e}")
        except Exception as e:
            raise Exception(f"网关创建失败：{e}")

    def shutdown_gateway(self, gateway_id: str):
        """
        禁用/关闭指定的网关
        对应接口: POST /network/config/{gateway_id}/_shutdown
        :param gateway_id: 要禁用的网关ID
        :return: 如果禁用成功则返回 True
        :raises Exception: 当API调用或业务逻辑失败时
        """
        endpoint = f"/network/config/{gateway_id}/_shutdown"
        print(f"正在禁用网关ID：{gateway_id}")

        # 该接口payload为空字典（无需传参，ID删除）
        payload = {}

        try:
            resp = self.post(endpoint, json = payload)
            self._assert_response_success(resp, endpoint, "POST")

            # 验证响应
            if resp.get('message') != 'success':
                print(f"禁用网关返回非 'success' 消息：{resp.get('message')}")
            else:
                print(f"网关{gateway_id} 成功发送禁用指令")
                return resp

        except Exception as e:
            print(f"禁用网关{gateway_id}失败：{e}")
            raise

    def delete_gateway(self, gateway_id: str) -> bool:
        """
        删除网关配置
        对应接口: DELETE /network/config/{id}
        :return: 如果删除成功或资源已不存在（幂等），则返回 True
        """
        endpoint = f"/network/config/{gateway_id}"
        print(f"正在删除网关：{gateway_id}")

        try:
            resp = self.delete(endpoint)

            # 统一的响应校验会处理HTTP状态码和业务success标志
            # 对于删除，如果资源不存在，基类 request 方法已处理404并返回一个模拟响应
            # 我们需要检查这个模拟响应或正常响应
            status = resp.get('status')
            success = resp.get('success')

            if 200 <= status < 300:
                print(f"网关：{gateway_id}删除成功")
                return True
            elif status == 404:
                print(f"尝试删除的网关{gateway_id}不存在（已清理）")
                return True # 视作被其他操作删除
            else:
                # 其他情况，如 500 服务器错误，或 200 但 success=false
                raise Exception(f"删除网关失败 - 状态：{status}，成功：{success}, 消息：{resp.get('message')}")

        except Exception as e:
            print(f"删除网关{gateway_id}时发生异常：{e}")
            raise

    def get_gateway_detail(self, gateway_id: str) -> Dict[str, Any]:
        """获取网关详情"""
        endpoint = f"/network/config/{gateway_id}"
        print(f"正在获取网关ID:{gateway_id}的详情")
        try:
            resp = self.get(endpoint)
            self._assert_response_success(resp, endpoint = endpoint, method = "GET")
            print(f"成功获取网关{gateway_id}详情")
            return resp
        except Exception as e:
            print(f"获取网关{gateway_id}详情失败：{e}")
            raise

# 协议接口封装
class ProtocolClient(APIClient):
    """
    继承自 APIClient，专门封装协议管理相关的 API
    """

    def __init__(self, base_url = "http://localhost:8848"):
        super().__init__(base_url)
        self.protocol_base = "/protocol"
        self.file_upload_url = f"/file/upload"

    def upload_jar(self, file_path):
        """
        上传协议 Jar 包（复用父类 post 方法，但需特殊处理 multipart/form-data）
        :param file_path: Jar 包的本地路径
        :return: 上传结果中的 file ID (fileId)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Jar 文件不存在：{file_path}")

        file_name = os.path.basename(file_path)

        # 构建 multipart/form-data 结构
        # requests 库检测到 files 参数时，会自动设置 Content-Type 为 multipart/form-data
        files = {
            'file': (file_name, open(file_path, 'rb'), 'application/java-archive')
        }

        try:
            # 传入 headers={} 清空父类默认的 "Content-Type: application/json"
            # 因为文件上传需要让 requests 自动生成 boundary 和 Content-Type
            resp = self.session.post(
                self.base_url +self.file_upload_url,
                files=files,
                headers={'Authorization': self.headers.get('Authorization', '')}
            )

            # 手动处理响应
            resp.raise_for_status()
            resp_json = resp.json()

            if resp_json['message'] != 'success':
                raise Exception(f"上传失败：{resp_json['message']}")

            result = resp_json.get('result', {})
            file_id = result.get('id', "")
            access_url = result.get('accessUrl') # 获取完整的访问 URL

            if not file_id:
                raise Exception(f"创建成功但未返回fileId")

            print(f"协议Jar包上传成功，fileId：{file_id}")
            return {
                'file_id': file_id,
                'access_url': access_url,
                'access_key': result.get('others', {}).get('accessKey')
            }

        except Exception as e:
            # 父类已经捕获了网络异常，这里主要捕获业务异常
            raise Exception(f"上传协议Jar包失败：{e}")
        finally:
            if 'file' in files:
                try:
                    files['file'][1].close()
                except:
                    pass

    def create_protocol(self, name, jar_file_id, jar_access_key=None, jar_access_url=None):
        """
        创建协议（复用父类 post 方法）
        """
        # 构造 Jar 包的访问 URL
        # 优先使用完整的 access_url
        if jar_access_url:
            location = jar_access_url
        else:
            # 否则构造基础 URL
            location = f"http://localhost:8848/file/{jar_file_id}"
            if jar_access_key:
                location += f"?access_keys={jar_access_key}"

        payload = {
            "name": name,
            "type": "jar",
            "configuration":{
                "location": location
            },
            "description": f"自动化测试的协议 - {name}"
        }

        resp = self.post(self.protocol_base, json = payload)
        if resp['message'] != 'success':
            raise Exception(f"创建协议失败：{resp.get('message')}")

        result = resp.get('result', {})
        protocol_id = result.get('id')
        state = result.get('state')

        print(f"协议'{name}' 协议创建成功，ID：{protocol_id}，State：{state}")
        return protocol_id

    def get_protocol_detail(self, page_index = 0, page_size = 12):
        """
        查询协议列表（完全复用父类 post 方法）
        """
        payload = {
            "pageIndex": page_index,
            "pageSize": page_size,
            "sorts": [{"name": "createTime", "order": "desc"}],
            "terms": []
        }

        resp = self.post(f"{self.protocol_base}/_query", json = payload)
        if resp['message'] != 'success':
            raise Exception(f"查询协议列表失败：{resp.get('message')}")
        return resp.get('result', {})

    def get_protocol_by_id(self, protocol_id):
        """
        根据 ID 查询单个协议详情
        """
        resp = self.get(f"{self.protocol_base}/{protocol_id}")
        if not resp.get('success'):
            raise Exception(f"查询协议详情失败：{resp.get('message')}")
        return resp.get('result', {})

    def delete_protocol(self, protocol_id):
        """
        删除协议方法
        """
        resp = self.delete(f"{self.protocol_base}/{protocol_id}")
        if resp.get('success'):
            print(f"协议 ID{protocol_id} 删除成功")
        else:
            print(f"已发送删除请求，但返回错误信息：{resp.get('message')}")
        return resp

    # ================= 辅助工具方法（非 API 请求） =================

    def wait_for_port(self, port, host = '127.0.0.1', timeout = 10):
        """
        等待端口监听（替代 netstat/nc）
        socket.socket()：Python标准库socket模块提供的核心函数，用于创建新的套接字对象，是网络编程的基础组件。
        参数1：socket.AF_INET
            地址族标识：指定使用IPv4协议进行网络通信
            功能说明：处理基于IPv4地址的网络连接，支持192.168.x.x等经典IP格式
            替代选项：AF_INET6用于IPv6，AF_UNIX用于本地进程间通信
        参数2：socket.SOCK_STREAM
            套接字类型：表示创建面向连接的流式套接字
            核心特性：
            提供可靠的、有序的字节流传输服务
            基于TCP协议实现，确保数据完整性
            支持错误校验与流量控制机制
            替代选项：SOCK_DGRAM用于UDP无连接通信，SOCK_RAW用于原始IP数据包
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1) # 设置 socket 的单次连接超时时间为 1 秒，防止因网络问题导致长时间阻塞
                    s.connect((host, port)) # 尝试连接到目标主机的指定端口
                    print(f"端口{port}已部署")
                    return True
            except (socket.timeout, ConnectionRefusedError):
                time.sleep(0.5)

        raise TimeoutError(f"端口{port}在{timeout}秒内未就绪")

    def send_mqtt_connect(self, host = '127.0.0.1', port = 1883, client_id = "test_001"):
        """
        发送一个原始的 MQTT Connect 报文
        返回：True=连接成功且收到响应, False=失败
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                s.connect((host, port))

                # 构造 MQTT Connect 固定报头
                # 固定头: 0x10 (Connect), 剩余长度, 协议名, 版本, 标志, Keepalive
                # 这里用一个最简的合法报文
                connect_packet = b'\x10\x0C\x00\x04MQTT\x04\x02\x00\x3C\x00\x00'
                s.send(connect_packet)

                # 等待响应 (ConnAck)
                resp = s.recv(1024)

                # MQTT ConnAck 固定头应该是 0x20
                if resp and resp[0] == 0x20:
                    print(f"收到MQTT ConnAck响应：{resp.hex()}")
                    return True
                else:
                    print(f"收到非预期响应：{resp.hex()}")
                    return False

        except socket.timeout:
            print("发送后超时，未收到响应")
            return False
        except Exception as e:
            print(f"Socket 异常：{e}")
            return False

# 网关绑定协议接口封装
class GatewayDeviceBindingClient(APIClient):
    """
    专门用于封装网关协议绑定相关的 API 操作。
    继承自 APIClient
    """

    def create_binding(self, name, protocol_id, channel_id, transport, description, provider = "mqtt-server-gateway") -> Dict:
        """
        创建网关协议绑定
        :param name: 绑定名称
        :param protocol_id: 协议ID
        :param channel_id: 通道/网关ID
        :param provider: 提供者，默认为 "mqtt-server-gateway"
        :param transport: 传输方式，默认为 "MQTT"
        :param description: 描述
        :return: 创建成功后返回的完整绑定信息
        """
        endpoint = '/gateway/device'
        payload = {
            "name": name,
            "description": description,
            "protocol": protocol_id,
            "channel": "network",
            "channelId": channel_id,
            "provider": provider,
            "transport": transport
        }
        print(f"正在创建网关协议绑定：{name}.....")
        resp = self.post(endpoint, json = payload)
        print("创建成功")
        return resp

    def list_bindings(self, page_index = 0, page_size = 12):
        """
        查询网关协议绑定列表
        :param page_index: 页码，从0开始
        :param page_size: 每页数量
        :return: 绑定列表
        """
        endpoint = '/gateway/device/detail/_query'
        payload = {
            "pageIndex": page_index,
            "pageSize": page_size,
            "sorts": [{"name": "createTime", "order": "desc"}],
            "terms": []
        }
        resp = self.post(endpoint, json = payload)
        return resp

    def disable_binding(self, binding_id):
        """
        禁用一个网关协议绑定
        :param binding_id: 要禁用的绑定的ID
        :return: 操作结果
        """
        endpoint = f'/gateway/device/{binding_id}/_shutdown'
        print(f"正在禁用绑定ID：{binding_id}")
        resp = self.post(endpoint, json = {})
        print("禁用成功！")
        return resp

    def delete_binding(self, binding_id):
        """
        删除一个网关协议绑定
        :param binding_id: 要删除的绑定的ID
        :return: 操作结果
        """
        endpoint = f'/gateway/device/{binding_id}'
        print(f"正在删除绑定 ID：{binding_id}...")
        resp = self.delete(endpoint)
        print("删除成功！")
        return resp

    def get_binding_details(self, binding_id):
        """
        获取单个绑定的详细信息 (通过查询列表并筛选实现，或假设存在详情接口)
        注意：您提供的API中没有直接的GET /gateway/device/{id}接口
        但DELETE接口的返回值包含了完整信息 这里通过查询列表来模拟
        """
        bindings = self.list_bindings()
        for binding in bindings['result']['data']:
            if binding.get('id') == binding_id:
                return binding
        return None
    
class DeviceClient(APIClient):

    # 工具方法：内部使用，用于校验业务状态
    def _assert_success(self, resp, action_name):
        """
        统一校验业务状态码
        :param resp: API返回的JSON
        :param action_name: 操作名称（用于报错信息）
        :raises Exception: 当业务状态不为200或success=false时抛出异常
        """
        if resp is None:
            raise Exception(f"[{action_name}]响应为空，可能网络断开")

        # 校验HTTP状态码
        status_code = resp.get('status')
        if status_code != 200:
            raise Exception(f"[{action_name}]HTTP状态码异常：{status_code} 响应：{resp}")

        # 校验业务 message 字段
        message = resp.get('message')
        if message != 'success':
            raise Exception(f"[{action_name}] 业务逻辑失败：{message}")

        # 校验result是否存在（针对有返回体的接口）
        # 删除接口可能没有result，根据实际情况调整
        if 'result' not in resp and action_name not in ['删除设备']:
            pass

        return resp

    # --- 业务接口：调用 _assert_success 验证异常---

    def create_device(self, device_id, name, product_id):
        """创建设备 (PATCH)"""
        url = f"/device-instance"
        payload = {
            "id": device_id,
            "name": name,
            "productId": product_id,
            "photoUrl": "/assets/device-product.png"
        }
        resp = self.patch(url, json = payload)
        # 使用_assert_success验证
        return self._assert_success(resp, "创建设备")

    def delete_device(self, device_id):
        """删除设备 (DELETE)"""
        resp = self.delete(f"/device-instance/{device_id}")
        return self._assert_success(resp, "删除设备")

    def deploy_device(self, device_id):
        """启用/部署设备 (POST)"""
        resp = self.post(f"/device-instance/{device_id}/deploy", json = {})
        return self._assert_success(resp, "启动设备")

    def undeploy_device(self, device_id):
        """禁用设备 (POST)"""
        resp = self.post(f"/device-instance/{device_id}/undeploy", json = {})
        return self._assert_success(resp, "禁用设备")

    def list_devices(self, page_index = 0, page_size = 12):
        """查询设备列表 (POST)"""
        url = "/device-instance/_query"
        payload = {
            "pageIndex": page_index,
            "pageSize": page_size,
            "sorts": [{"name": "createTime", "order": "desc"}],
            "terms": []
        }
        resp = self.post(url, json = payload)
        return self._assert_success(resp, "查询设备列表")

    def get_device_detail(self, device_id):
        """查询设备详情 (POST)"""
        url = f"/device-instance/{device_id}/detail"
        resp = self.get(url)
        return self._assert_success(resp, "查询设备详情")

    def get_device_info(self, device_id, page_index = 1, page_size = 12, max_retries = 3):
        """
        查询设备操作日志（原始接口）
        :param device_id: 设备ID
        :param page_index: 页码
        :param page_size: 每页条数
        :param max_retries: 最大重试次数（防止刚上报还没写入DB）
        :return: 解析后的JSON响应体
        """
        url = f"/device-instance/{device_id}/logs"

        payload = {
            "pageIndex": page_index,
            "pageSize": page_size,
            "sorts": [{"name": "timestamp", "order": "desc"}],
            "terms":[]
        }

        resp = None
        # 有时候刚发完数据，DB还没刷出来，可以加个重试机制
        for i in range(max_retries):
            resp = self.post(url, json = payload)
            self._assert_success(resp, f"查询设备日志（尝试{i + 1}/ {max_retries}次）")

            result = resp.get('result', {})
            data_list = result.get('data', [])

            # 如果找到了数据，直接返回，如果没找到，等一下再试
            if len(data_list) > 0:
                return resp

            if i < max_retries - 1:
                time.sleep(1)

        # 重试完还是没有，返回空结果或者抛异常
        return resp

    def get_latest_telemetry_log(self, device_id):
        """
        获取最新一条遥测日志（自动跳过 ONLINE/OFFLINE 等系统消息）
        """
        # 获取日志列表
        response = self.get_device_info(device_id, page_size=10)  # 获取多条，方便查找

        # 提取 data 列表
        if not response or 'result' not in response:
            return None

        log_list = response['result'].get('data', [])

        if not log_list:
            return None

        print(f"[Device Log] 总共 {len(log_list)} 条日志")

        # 从最新的开始遍历，跳过系统消息
        for log in reversed(log_list):
            # log 应该是字典
            if not isinstance(log, dict):
                print(f"[Device Log] 跳过非字典项: {type(log)}")
                continue

            content = log.get('content', '{}')

            try:
                parsed_content = json.loads(content)
                message_type = parsed_content.get('messageType')

                # 跳过系统消息，只返回业务数据
                if message_type in ['ONLINE', 'OFFLINE', 'HEARTBEAT']:
                    print(f"[Device Log] 跳过系统消息: {message_type}")
                    continue

                # 返回第一条非系统消息
                if message_type in ['REPORT_PROPERTY', 'REPORT_EVENT']:
                    properties = parsed_content.get('properties', {})
                    print(f"[Device Log] 找到遥测数据: {message_type}")
                    print(f"[Device Log] Properties 内容: {json.dumps(properties, indent=2, ensure_ascii=False)}")
                    return parsed_content

            except json.JSONDecodeError as e:
                print(f"[Device Log] JSON解析失败: {e}")
                continue

        return None

    def assert_log_contains_telemetry(self, device_id, expected_temp):
        """
        断言：设备日志中包含指定的遥测数据
        这是一个"断言级"的封装，把校验逻辑也包进来
         """
        parsed_content = self.get_latest_telemetry_log(device_id)

        assert parsed_content is not None
        assert parsed_content.get('messageType') == 'REPORT_PROPERTY', f"消息类型错误：{parsed_content['messageType']}"

        properties = parsed_content.get('properties', {})
        actual_temp = properties.get('temperature')

        assert actual_temp is not None, "properties中没有temperature"
        assert actual_temp == expected_temp, f"温度不匹配：期望{expected_temp}，实际：{actual_temp}"

        return parsed_content

class AlarmClient(APIClient):
    """
    告警配置相关的 API 客户端，继承自 APIClient。
    使用 _assert_success 统一校验业务响应。
    """

    # 工具方法：内部使用，用于校验业务状态
    def _assert_success(self, resp, action_name):
        """
        统一校验业务状态码 (仿照 DeviceClient)
        :param resp: API返回的JSON (dict)
        :param action_name: 操作名称（用于报错信息）
        :raises Exception: 当业务状态不为200或message不为'success'时抛出异常
        :return: 校验通过后返回原始响应
        """
        if resp is None:
            raise Exception(f"[告警{action_name}操作]响应为空，可能网络断开或服务器无响应")

        # 校验业务 status 字段
        status_code = resp.get('status')
        if status_code != 200:
            raise Exception(f"[告警 {action_name}操作]业务状态码异常：{status_code}，响应体：{resp}")

        # 校验业务 message 字段
        message = resp.get('message')
        if message != 'success':
            raise Exception(f"[告警 {action_name}操作]业务逻辑失败：{message}，响应体：{resp}")

        # 某些操作（如删除）可能没有 result 字段，这是正常的
        # 如果需要确保 result 存在，可以取消下面的注释
        # if 'result' not in resp:
        #     raise Exception(f"[{action_name}] 响应中缺少 'result' 字段, 响应体: {resp}")

        print(f"告警 {action_name} 业务校验通过")
        return resp

    def create_alarm(self, level, target_type, name, description):
        """
        新建告警接口
        :return: 创建成功后返回的完整告警配置信息 (dict)
        """
        endpoint = "/alarm/config"
        payload = {
            "level": level,
            "targetType": target_type,
            "name": name,
            "description": description
        }
        print(f"正在创建告警：{name}...")
        resp = self.post(endpoint, json = payload)
        # 使用 _assert_success 统一校验
        return self._assert_success(resp, "创建告警")

    def disable_alarm(self, alarm_id):
        """
        禁用告警接口
        :return: 禁用操作后的服务器响应 (dict)
        """
        endpoint = f"/alarm/config/{alarm_id}/_disable"
        print(f"正在禁用告警（ID：{alarm_id}）...")
        # 禁用操作使用 POST 方法，payload 为空字典
        resp = self.post(endpoint, json = {})
        # 使用 _assert_success 统一校验
        return self._assert_success(resp, "禁用告警")

    def delete_alarm(self, alarm_id):
        """
        删除告警接口
        :return: 删除操作后的服务器响应 (dict)
        """
        endpoint = f"/alarm/config/{alarm_id}"
        print(f"正在删除告警（ID:{alarm_id}）")
        # 删除操作使用 DELETE 方法
        resp = self.delete(endpoint)
        # 使用 _assert_success 统一校验
        return self._assert_success(resp, "删除告警")

    def get_alarm_detail(self, alarm_id):
        """
        查看告警详情接口
        :return: 告警ID对应的告警详情 (dict)
        """
        endpoint = f"/alarm/config/{alarm_id}"
        print(f"正在查询告警（ID：{alarm_id}）")
        resp = self.get(endpoint)
        # 使用 _assert_success 统一校验
        return self._assert_success(resp, action_name = "查看告警详情")

    def update_alarm(self, alarm_id, name = None, description = None, state = None, level = None, target_type = None):
        """
        修改告警配置（PATCH）
        :param alarm_id: 告警ID
        :param name: 新的告警名称（可选）
        :param level: 新的告警级别（可选）
        :param description: 新的描述（可选）
        :param state: 新的状态（可选，如 {"text": "禁用", "value": "disabled"}）
        :return: 修改后的响应
        """
        endpoint = "/alarm/config"

        # 构建payload，只包含需要的字段
        payload = {"id": alarm_id}
        if name is not None:
            payload['name'] = name
        if level is not None:
            payload['level'] = level
        if description is not None:
            payload['description'] = description
        if state is not None:
            payload['state'] = state
        if target_type is not None:
            payload['targetType'] = target_type

        resp = self.patch(endpoint, json = payload)
        return self._assert_success(resp, "修改告警")


class SceneClient(APIClient):
    """
    场景联动相关的 API 客户端，继承自 APIClient。
    封装了创建、更新、启用、禁用和删除场景的接口。
    使用 _assert_success 统一校验业务响应。
    """

    # 工具方法：内部使用，用于校验业务状态
    def _assert_success(self, resp, action_name):
        """
        统一校验业务状态码 (仿照 DeviceClient)
        :param resp: API返回的JSON (dict)
        :param action_name: 操作名称（用于报错信息）
        :raises Exception: 当业务状态不为200或message不为'success'时抛出异常
        :return: 校验通过后返回原始响应
        """
        if resp is None:
            raise Exception(f"[场景联动 {action_name} 操作]响应为空，可能网络断开或服务器无响应")

        # 校验 status 字段
        status_code = resp.get('status')
        if status_code != 200:
            raise Exception(f"[场景联动 {action_name} 操作]业务状态码异常：{status_code}，响应体：{resp}")

        message = resp.get('message')
        if message != 'success':
            raise Exception(f"[场景联动 {action_name} 操作]业务逻辑失败：{message}，响应体：{resp}")

        print(f"[场景联动 {action_name}]业务校验通过")
        return resp

    def create_scene(self, name, trigger_type = "device"):
        """
        创建场景联动（第一步：创建基础框架）
        :param name: 场景名称，例如 "高温告警"
        :param trigger_type: 触发器类型，默认为 "device" (设备触发)
        :return: 创建成功后返回的完整场景信息 (dict)，包含场景ID
        """
        endpoint = "/scene"
        payload = {
            "name": name,
            "trigger":{
                "type": trigger_type
            }
        }
        print(f"正在创建场景：{name}...")
        resp = self.post(endpoint, json = payload)
        return self._assert_success(resp, "创建场景")

    def update_scene_details(self,scene_id, details_payload):
        """
        补充/更新场景联动的规则细节（第二步：配置具体逻辑）
        :param scene_id: 场景ID，从 create_scene 的返回中获取
        :param details_payload: 包含 trigger, branches 等详细规则的完整payload
        :return: 更新操作后的服务器响应 (dict)
        """
        endpoint = f"/scene/{scene_id}"
        print(f"正在更新场景（ID：{scene_id}）的详细内容...")
        payload_with_id = details_payload.copy()
        payload_with_id['id'] = scene_id

        resp = self.put(endpoint, json = payload_with_id)
        return self._assert_success(resp, "更新场景细节")

    def enable_scene(self, scene_id):
        """
        启用一个场景联动
        :param scene_id: 要启用的场景ID
        :return: 启用操作后的服务器响应 (dict)
        """
        endpoint = f"/scene/{scene_id}/_enable"
        print(f"正在启用场景（ID：{scene_id}）...")
        resp = self.put(endpoint, json = {})
        return self._assert_success(resp, "启用场景")

    def disable_scene(self, scene_id):
        """
        禁用一个场景联动
        :param scene_id: 要禁用的场景ID
        :return: 禁用操作后的服务器响应 (dict)
        """
        endpoint = f"/scene/{scene_id}/_disable"
        print(f"正在禁用场景（ID：{scene_id}）...")
        resp = self.put(endpoint, json = {})
        return self._assert_success(resp, "禁用场景")

    def delete_scene(self, scene_id):
        """
        删除一个场景联动
        :param scene_id: 要删除的场景ID
        :return: 删除操作后的服务器响应 (dict)
        """
        endpoint = f"/scene/{scene_id}/"
        print(f"正在删除场景（ID：{scene_id}）...")
        resp = self.delete(endpoint)
        return self._assert_success(resp, "删除场景")

    def create_and_configure_scene(
            self,
            scene_name,
            device_id,
            product_id,
            high_temp_threshold = 60,
            low_temp_threshold = 60,
            high_temp_interval = 2,
            low_temp_interval = 5
    ):
        """
        创建并配置一个完整的场景联动（包含高低温告警逻辑）

        :param scene_name: 场景名称
        :param device_id: 设备ID
        :param product_id: 产品ID
        :param high_temp_threshold: 高温阈值，默认60
        :param low_temp_threshold: 低温阈值，默认50
        :param high_temp_interval: 高温下的属性值，默认2
        :param low_temp_interval: 低温下的属性值，默认5
        :return: 最终创建并启用的场景信息
        """
        create_resp = self.create_scene(name = scene_name)
        scene_id = create_resp.get('result').get('id')
        print(f"场景基础框架创建成功，ID：{scene_id}")

        # 构建完整的详细配置payload
        # 使用传入的参数动态构建，不再硬编码
        details_payload = {
            "id": scene_id,
            "name": create_resp['result']['name'],
            "triggerType": "device",
            "trigger":{
                "type": "device",
                "device":{
                    "source": "fixed",
                    "selector": "fixed",
                    "selectorValues": [{"value": device_id, "name": device_id}],
                    "productId": product_id,
                    "operation": {"operator": "reportProperty"}
                },
                "typeName": "设备触发"
            },
            "parallel": False,
            "branches": [
                {
                    "when": [{
                        "type": "and",
                        "termType": "eq",
                        "options": [],
                        "terms": [{
                            "column": "properties.temperature.current",
                            "type": "and",
                            "termType": "gte",
                            "value": {"source": "manual", "value": high_temp_threshold},
                            "options": [],
                            "terms": [],
                            "key": str(uuid.uuid4())
                        }],
                        "key": str(uuid.uuid4())
                    }],
                    "shakeLimit": {
                        "enabled": False,
                        "time": 1,
                        "threshold": 1,
                        "continuous": False,
                        "alarmFirst": True,
                        "outputFirst": False,
                        "rolling": False
                    },
                    "then": [{
                        "parallel": False,
                        "actions": [{
                            "executor": "device",
                            "device": {
                                "source": "fixed",
                                "upperKey": "",
                                "selector": "fixed",
                                "selectorValues": [{"value": device_id, "name": device_id}],
                                "productId": product_id,
                                "message": {
                                    "messageType": "WRITE_PROPERTY",
                                    "properties": {"interval": {"value": high_temp_interval, "source": "fixed"}},
                                    "inputs": []
                                }
                            },
                            "options": {
                                "selector": "fixed",
                                "triggerName": device_id,
                                "productName": product_id,
                                "name": [device_id],
                                "propertiesName": "interval",
                                "propertiesValue": high_temp_interval,
                                "otherColumns": [],
                                "columnMap": {},
                                "type": "设置",
                                "columns": []
                            },
                            "actionId": 33356854,
                            "key": str(uuid.uuid4())
                        }],
                        "key": str(uuid.uuid4())
                    }],
                    "executeAnyway": True,
                    "branchId": 87662432,
                    "branchName": "高温条件",
                    "key": str(uuid.uuid4()),
                    "branches_index": 0
                },
                {
                    "when": [{
                        "type": "and",
                        "terms": [{
                            "column": "properties.temperature.current",
                            "type": "and",
                            "termType": "lte",
                            "value": {"source": "manual", "value": low_temp_threshold},
                            "key": str(uuid.uuid4())
                        }],
                        "key": str(uuid.uuid4())
                    }],
                    "key": 52566155,
                    "shakeLimit": {
                        "enabled": False,
                        "time": 1,
                        "threshold": 1,
                        "alarmFirst": True
                    },
                    "then": [{
                        "parallel": False,
                        "key": str(uuid.uuid4()),
                        "actions": [{
                            "executor": "device",
                            "key": str(uuid.uuid4()),
                            "actionId": 61029110,
                            "device": {
                                "selector": "fixed",
                                "source": "fixed",
                                "selectorValues": [{"value": device_id, "name": device_id}],
                                "productId": product_id,
                                "upperKey": "",
                                "message": {
                                    "messageType": "WRITE_PROPERTY",
                                    "properties": {"interval": {"value": low_temp_interval, "source": "fixed"}},
                                    "inputs": []
                                }
                            },
                            "options": {
                                "selector": "fixed",
                                "triggerName": device_id,
                                "productName": product_id,
                                "name": [device_id],
                                "propertiesName": "interval",
                                "propertiesValue": low_temp_interval,
                                "otherColumns": [],
                                "columnMap": {},
                                "type": "设置",
                                "columns": []
                            },
                            "actionId": 33356854,
                            "key": str(uuid.uuid4())
                        }],
                        "key": str(uuid.uuid4())
                    }],
                    "branchId": 52566155,
                    "branchName": "低温条件",
                    "branches_index": 1
                }
            ],
            "creatorId": "21232f297a57a5a743894a0e4a801fc3",
            "createTime": 1777280522187,
            "modifierId": "21232f297a57a5a743894a0e4a801fc3",
            "modifyTime": 1777281391410,
            "startTime": 1777281391410,
            "state": {"text": "正常", "value": "started"},
            "options": {
                "trigger": {
                    "name": device_id,
                    "extraName": "",
                    "onlyName": False,
                    "type": "属性上报",
                    "typeIcon": "icon-file-upload-outline",
                    "productName": "",
                    "selectorIcon": "icon-shebei1",
                    "action": ""
                },
                "when": [
                    {
                        "terms": [[["温度/当前值", "大于等于", {"0": high_temp_threshold}, "and"]]],
                        "branchName": "条件",
                        "key": 87662432,
                        "executeAnyway": True,
                        "groupIndex": 1
                    },
                    {
                        "terms": [{
                            "termType": "并且",
                            "terms": [[["温度/当前值", "小于等于", {"0": low_temp_threshold}, "and"]]]
                        }],
                        "key": 52566155
                    }
                ]
            },
            "features": ["none"]
        }

        # 更新场景详情
        self.update_scene_details(scene_id = scene_id, details_payload = details_payload)
        print("场景详细规则已配置")

        # 启用场景
        self.enable_scene(scene_id)
        print("场景已启用")

        print(f"===场景已创建 配置 启用 成功！===")
        print(f"场景ID：{scene_id}")
        print(f"监控设备：{device_id}")
        print(f"高温阈值：{high_temp_threshold}，心跳间隔：{high_temp_interval}")
        print(f"低温阈值：{low_temp_threshold}，心跳间隔：{low_temp_interval}")

        return {
            "id": scene_id,
            "name": scene_name,
            "device_id": device_id,
            "product_id": product_id,
            "status": "started"
        }

    def get_scene_detail(self, scene_id):
        endpoint = f"/scene/{scene_id}"
        print(f"正在查看场景详情：{scene_id}...")
        resp = self.get(endpoint)
        return self._assert_success(resp, "查看场景详情")