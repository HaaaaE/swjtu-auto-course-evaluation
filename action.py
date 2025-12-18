# --- auto_assess.py ---
import os
# 从配置文件导入账号密码
import config
from assessor import SWJTUAssessor


if __name__ == "__main__":
    print("--- 西南交大教务处自动评教脚本 ---")

    username = os.environ.get('SWJTU_USERNAME')
    password = os.environ.get('SWJTU_PASSWORD')

    if  not username or not password:
        print("请配置 github actions 环境变量 SWJTU_USERNAME 和 SWJTU_PASSWORD")
        raise Exception("未找到环境变量 SWJTU_USERNAME 或 SWJTU_PASSWORD")
        
    if not username or not password:
        print("错误：学号或密码不能为空！")
        raise Exception("学号或密码不能为空！")
    else:
        assessor = SWJTUAssessor(username=username, password=password)
        assessor.run()