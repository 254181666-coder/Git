"""
业务系统OpenAPI客户端
处理签名认证、请求发送
"""
import hashlib
import hmac
import time
import random
import string
from typing import Optional, Dict, Any, List
import requests

from config import BUSINESS_API

def generate_sign(params: Dict[str, Any], secret: str) -> str:
    """
    生成签名
    规则：对参数按键名升序排序，格式 key=value 拼接，再加上 &secret=xxx，然后md5加密
    """
    # 按键名升序排序
    sorted_keys = sorted(params.keys())
    
    # 拼接字符串
    sign_str = ""
    for key in sorted_keys:
        if sign_str:
            sign_str += "&"
        sign_str += f"{key}={params[key]}"
    
    # 添加secret
    sign_str += f"&secret={secret}"
    
    # md5加密
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest()

def generate_nonce(length: int = 16) -> str:
    """生成随机nonce字符串"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


class BusinessAPIClient:
    def __init__(self):
        self.base_url = BUSINESS_API["base_url"]
        self.appid = BUSINESS_API["appid"]
        self.secret = BUSINESS_API["secret"]
        self.access_token = BUSINESS_API.get("access_token", "")
    
    def add_auth_params(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """添加认证参数和签名"""
        if params is None:
            params = {}
        
        # 添加基本参数
        params["appid"] = self.appid
        params["timestamp"] = int(time.time())
        params["nonce"] = generate_nonce()
        
        # 生成签名
        params["sign"] = generate_sign(params, self.secret)
        
        return params
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    def request(self, method: str, endpoint: str, 
                params: Optional[Dict[str, Any]] = None, 
                json_body: Optional[Dict[str, Any]] = None,
                retry: int = 3) -> Optional[Dict[str, Any]]:
        """
        发送请求
        method: GET/POST
        endpoint: 接口路径，如 /open/shop/list
        params: URL查询参数（会添加认证信息）
        json_body: JSON请求体
        retry: 重试次数
        """
        # 添加认证参数
        query_params = self.add_auth_params(params)
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retry):
            try:
                resp = requests.request(
                    method, url, 
                    params=query_params,
                    json=json_body,
                    headers=self.get_headers(),
                    timeout=30
                )
                resp.raise_for_status()
                result = resp.json()
                
                if result.get("code") == 200 and result.get("sub_code") == 0:
                    return result
                else:
                    print(f"API请求失败: {result}")
                    if attempt < retry - 1:
                        time.sleep(1)
                    continue
                    
            except Exception as e:
                print(f"API请求异常: {e}")
                if attempt < retry - 1:
                    time.sleep(1)
                continue
        
        return None
    
    # ============== 已明确接口 ==============
    
    def get_shop_list(self, shop_id: int = 0) -> Optional[List[Dict[str, Any]]]:
        """
        获取门店列表
        GET /open/shop/list
        """
        result = self.request("POST", "/open/shop/list", json_body={"shop_id": shop_id})
        if result and "data" in result and "res" in result["data"]:
            return result["data"]["res"]
        return None
    
    def get_user_list(self) -> Optional[List[Dict[str, Any]]:
        """
        获取员工列表
        POST /open/system/user/list
        """
        result = self.request("POST", "/open/system/user/list", json_body={})
        if result and "data" in result:
            return result["data"]
        return None
    
    def get_province_list(self) -> Optional[List[Dict[str, Any]]:
        """获取省份列表"""
        result = self.request("POST", "/open/common/area/get_province", json_body={})
        if result and "data" in result and "res" in result["data"]:
            return result["data"]["res"]
        return None
    
    def get_city_list(self, province_code: int) -> Optional[List[Dict[str, Any]]:
        """获取城市列表"""
        result = self.request("POST", "/open/common/area/get_city", json_body={"code": province_code})
        if result and "data" in result and "res" in result["data"]:
            return result["data"]["res"]
        return None
    
    def get_district_list(self, city_code: int) -> Optional[List[Dict[str, Any]]:
        """获取区域列表"""
        result = self.request("POST", "/open/common/area/get_district", json_body={"code": city_code})
        if result and "data" in result and "res" in result["data"]:
            return result["data"]["res"]
        return None
    
    def debug_sign(self, nonce: str = "1", timestamp: str = "1", appid: str = "wsk") -> Optional[Dict[str, Any]]:
        """调试签名接口"""
        params = {
            "nonce": nonce,
            "timestamp": timestamp,
            "appid": appid,
        }
        result = self.request("GET", "/open/common/sign/gen", params=params)
        return result
    
    def get_orders_by_date(self, start_date: str, end_date: str, page: int = 1, page_size: int = 100) -> Optional[List[Dict[str, Any]]:
        """
        按日期范围获取订单列表
        """
        result = self.request("POST", "/open/order/list", json_body={
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "page_size": page_size
        })
        if result and "data" in result and "orders" in result["data"]:
            return result["data"]["orders"]
        return None
    
    def get_member_recharge_by_date(self, start_date: str, end_date: str, page: int = 1, page_size: int = 100) -> Optional[List[Dict[str, Any]]:
        """
        按日期范围获取储值订单列表
        """
        result = self.request("POST", "/open/member/recharge/list", json_body={
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "page_size": page_size
        })
        if result and "data" in result and "list" in result["data"]:
            return result["data"]["list"]
        return None
    
    def get_member_balance_changes(self, start_date: str, end_date: str, page: int = 1, page_size: int = 100) -> Optional[List[Dict[str, Any]]:
        """
        按日期范围获取会员余额变动记录
        """
        result = self.request("POST", "/open/member/balance/list", json_body={
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "page_size": page_size
        })
        if result and "data" in result and "list" in result["data"]:
            return result["data"]["list"]
        return None
