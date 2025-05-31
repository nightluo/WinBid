import os
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import re
import io
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 正式版
# key = "e36d9f43-4442-48d8-b864-18a084a85840"

# 测试版
key = "04c30c93-6d63-4f65-b58b-8ad649dcdb54"

class WeComWebhook:  
    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
    def __init__(self):
        self.webhook_key = key
        if not self.webhook_key:
            logger.error("未检测到环境变量 WECOM_WEBHOOK_KEY")
            raise ValueError("缺失密钥")

    def send_text(self, content: str) -> dict:
        payload = {"msgtype": "text", "text": {"content": content}}
        try:
            response = requests.post(
                self.BASE_URL.format(key=self.webhook_key),
                json=payload,
                timeout=8
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"消息发送失败: {str(e)}")
            return {"errcode": -1, "errmsg": "请求异常"}

def ct_search(keyword, start_time):
    session = requests.Session()
    home_url = "https://caigou.chinatelecom.com.cn"
    try:
        home_response = session.get(home_url)
        home_response.raise_for_status()

    except Exception as e:
            logger.error(f"主页请求失败: {str(e)}")
            return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
    }

    payload_type = ["xi9s", "e2no", "e3erht", "ru7of", "e8vif", "ds3fd2s", "f1f7e", "n0eves", "ow7t", "th4gie", "s1x5e"]
    type_list = ["6", "1", "3", "4", "5", "14", "3", "7", "2", "8", "7"]
    
    api_url = "https://caigou.chinatelecom.com.cn/portal/base/announcementJoin/queryListNew"
    bid_list = []
    for i in range(len(payload_type)):
        type = payload_type[i]
        type_id = type_list[i]
        payload = {
            "title": keyword,
            "pageSize": 10,
            "pageNum": 1,
            "type": type,
            "creatorName": "",
            "provinceCode": ""
        }

        try:
            response = session.post(
                url=api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()              
            data = response.json()
            data_list = data['data']['list']
            for list in data_list:
                format_str = "%Y-%m-%d %H:%M:%S"
                bid_time = datetime.strptime(list['createDate'], format_str)
                if bid_time >= start_time.replace(tzinfo=None):
                    bid = {
                        "标题": list['docTitle'],
                        "类型": list['docType'],
                        "链接":  f"{home_url}/DeclareDetails?id={list['docId']}&type={type_id}&docTypeCode={list['docTypeCode']}"
                    }
                    bid_list.append(bid)
                else:
                    break

        except requests.exceptions.HTTPError as e:
            logger.error(f"API请求失败: 状态码 {response.status_code}, 响应内容: {response.text}")
            return None
    
    return bid_list
    
def tower_search(keyword, start_time):
    session = requests.Session()
    home_url = "http://www.tower.com.cn/#/purAnnouncement?name=more&purchaseNoticeType=2&activeIndex=0"
    try:
        home_response = session.get(home_url)
        home_response.raise_for_status()

    except Exception as e:
            logger.error(f"主页请求失败: {str(e)}")
            return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Content-Type': 'application/json;charset=UTF-8',
    }

    type_list = ["2", "45"]
    docType_list = ["采购公告", "候选人及结果公示"]
    
    api_url = "http://www.tower.com.cn/supportal/v1/obp-notice/query-notice"
    bid_list = []
    for i in range(len(type_list)):
        type_id = type_list[i]
        docType = docType_list[i]
        payload = {
            "noticeTitle": keyword,
            "purchaseNoticeType": type_id,
            "orgName":"",
            "times":"",
            "transformationField":"",
            "conversionMethod":"",
            "current":1,
            "size":20
        }

        try:
            response = session.post(
                url=api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
                
            data = response.json()
            
            data_list = data['data']['records']
            for list in data_list:
                format_str = "%Y-%m-%d %H:%M:%S"
                bid_time = datetime.strptime(list['createTime'], format_str)
                if bid_time >= start_time.replace(tzinfo=None):
                    bid = {
                        "标题": list['noticeTitle'],
                        "类型": docType,
                        "链接":  f"http://www.tower.com.cn/#/noticeDetail?id={list['noticeId']}"
                    }
                    bid_list.append(bid)
                else:
                    break

        except requests.exceptions.HTTPError as e:
            logger.error(f"API请求失败: 状态码 {response.status_code}, 响应内容: {response.text}")
            return None
        
    return bid_list
    

def lambda_handler(event, context):
    """Lambda入口函数"""
    try:
        logger.info("【调试】函数开始执行")
        webhook = WeComWebhook()
        logger.info("【调试】Webhook初始化成功")

        utc_now = datetime.now(timezone.utc)
        beijing_time = utc_now.astimezone(timezone(timedelta(hours=8)))
        # today = beijing_time.date()
        # start_time = datetime.combine(today, time(9, 0)).astimezone(timezone(timedelta(hours=8)))
        # end_time = datetime.combine(today, time(18, 0)).astimezone(timezone(timedelta(hours=8)))
        
        start_time = beijing_time - timedelta(hours=24)

        send_test = webhook.send_text(f"start_time: {start_time}")
        
        keyword_list = ["培训", "竞赛", "赋能", "会务", "交流活动", "辅助服务"]
        for keyword in keyword_list:
            result_1 = ct_search(keyword, start_time)
            result_2 = tower_search(keyword, start_time)
            result = result_1 + result_2

            message = ''
            for msg in result:
                message = message + f"【标题】{msg['标题']}\n【类型】{msg['类型']}\n【链接】{msg['链接']}\n\n"

            if message != '':
                message = message[:-2]
                result = webhook.send_text(message)
                logger.info(f"【调试】发送结果: {json.dumps(result)}")
            else:
                continue
    
    except Exception as e:
        logger.error(f"全局异常: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    
if __name__ == "__main__":
    func = lambda_handler("", "")
