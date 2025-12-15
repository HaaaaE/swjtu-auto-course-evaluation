# --- auto_assess.py ---
import requests
from bs4 import BeautifulSoup
import time
import getpass
from PIL import Image
import io
import random

# 从配置文件导入账号密码
import config


# 相关的URL
BASE_URL = "https://jwc.swjtu.edu.cn"
LOGIN_PAGE_URL = f"{BASE_URL}/service/login.html"
LOGIN_API_URL = f"{BASE_URL}/vatuu/UserLoginAction"
CAPTCHA_URL = f"{BASE_URL}/vatuu/GetRandomNumberToJPEG"
LOADING_URL = f"{BASE_URL}/vatuu/UserLoadingAction" 
ASSESS_LIST_URL = f"{BASE_URL}/vatuu/AssessAction?setAction=list"
SUBMIT_URL = f"{BASE_URL}/vatuu/AssessAction"

# 模拟浏览器的请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Origin': BASE_URL,
}

class SWJTUAssessor:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get_captcha_and_login(self):
        print("正在获取验证碼...")
        try:
            captcha_params = {'test': int(time.time() * 1000)}
            response = self.session.get(CAPTCHA_URL, params=captcha_params)
            response.raise_for_status()
            image = Image.open(io.BytesIO(response.content))
            image.show()
            captcha_code = input("请在新打开的窗口中查看验证码，并在此输入：")
        except Exception as e:
            print(f"获取验证码失败: {e}")
            return False

        print("正在尝试登录API...")
        login_payload = { 'username': self.username, 'password': self.password, 'ranstring': captcha_code, 'url': '', 'returnType': '', 'returnUrl': '', 'area': '' }
        login_headers = self.session.headers.copy()
        login_headers['Referer'] = LOGIN_PAGE_URL
        try:
            response = self.session.post(LOGIN_API_URL, data=login_payload, headers=login_headers)
            response.raise_for_status()
            login_result = response.json()
            if login_result.get('loginStatus') == '1':
                print(f"API验证成功！{login_result.get('loginMsg')}")
                return True
            else:
                print(f"登录失败: {login_result.get('loginMsg', '服务器未返回明确错误信息')}")
                return False
        except Exception as e:
            print(f"登录请求异常: {e}")
            return False

    def _perform_loading_action(self):
        print("正在访问加载页面以建立完整会话...")
        try:
            headers = self.session.headers.copy()
            headers['Referer'] = LOGIN_PAGE_URL
            response = self.session.get(LOADING_URL, headers=headers)
            response.raise_for_status()
            print("会话建立步骤完成。")
            return True
        except Exception as e:
            print(f"访问加载页面失败: {e}")
            return False

    def get_unevaluated_courses(self):
        print("\n正在获取待评价课程列表...")
        try:
            headers = self.session.headers.copy()
            headers['Referer'] = LOADING_URL
            response = self.session.get(ASSESS_LIST_URL, headers=headers)
            response.raise_for_status()
            if "非常抱歉，您还未登陆" in response.text:
                 print("错误：获取课程列表失败，服务器仍然认为我们未登录。")
                 return []
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            for a_tag in soup.find_all('a', string='填写问卷'):
                relative_path = a_tag['href'].replace('..', '')
                full_link = f"{BASE_URL}{relative_path}"
                links.append(full_link)
            print(f"成功找到 {len(links)} 门待评价课程。")
            return links
        except Exception as e:
            print(f"获取课程列表失败: {e}")
            return []

    def _parse_and_build_payload(self, questionnaire_html):
        soup = BeautifulSoup(questionnaire_html, 'html.parser')
        title = soup.find('div', class_='post-title')
        if title: print(f" -> 问卷标题: {title.text.strip()}\n" + "-" * 40)
        payload = {'setAction': 'answerStudent', 'templateFlag': '0', 'keyword': 'null', 't': str(time.time())}
        hidden_inputs = soup.find_all('input', type='hidden')
        for ipt in hidden_inputs:
            if ipt.get('name') and ipt.get('value') is not None: payload[ipt['name']] = ipt['value']
        problem_ids, answers, scores, percents = [], [], [], []
        all_problems = soup.find_all('div', class_='post-problem')
        for i, problem_div in enumerate(all_problems, 1):
            problem_id_input = problem_div.find('input', {'name': 'problem_id'})
            if not problem_id_input: continue
            question_text = ''.join(problem_div.find_all(string=True, recursive=False)).strip()
            print(f"   [问题 {i}] {question_text}")
            problem_ids.append(problem_id_input['value'])
            percents.append(problem_id_input['perc'])
            answer_div = problem_div.find('div', class_='answerDiv')
            if not answer_div: answer_div = problem_div.find_next_sibling('div', class_='answerDiv')
            if not answer_div:
                print(f"   [警告] 找不到问题 {i} 的答案区域，跳过此题。")
                continue
            if answer_div.find('textarea'):
                answer_text = "老师讲得很好，没有意见。"
                answers.append(answer_text)
                scores.append("")
                print(f"   [答案 {i}] (主观题): {answer_text}\n")
            else:
                first_option = answer_div.find('input', type='radio')
                if first_option:
                    answers.append(first_option['value'])
                    scores.append(first_option['score'])
                    label = first_option.find_next_sibling('label')
                    answer_label = label.text.strip() if label else "未知选项"
                    print(f"   [答案 {i}] (选择题): {answer_label}\n")
        print("-" * 40)
        payload['id'] = '_' + '_'.join(problem_ids)
        payload['answer'] = '_' + '_'.join(answers)
        payload['scores'] = '_' + '_'.join(scores)
        payload['percents'] = '_' + '_'.join(percents)
        return payload

    def evaluate_course(self, course_url, current_num, total_num):
        """对单个课程进行评价，并加入防刷延时和进度显示"""
        try:
            print(f" -> 正在进入问卷页面...")
            response = self.session.get(course_url)
            response.raise_for_status()
            print(f" -> 正在解析问卷并构建答案...")
            payload = self._parse_and_build_payload(response.text)
            
            delay_time = random.randint(65, 75)
            print(f" -> 教务处强制要求等待至少一分钟，本脚本在(65，75)随机。本次将等待 {delay_time} 秒后提交...")
            
            for i in range(delay_time):
                # 倒计时显示中加入了进度
                remaining = delay_time - i - 1
                progress = f"[{current_num}/{total_num}]"
                print(f"\r -> 倒计时: {remaining}秒 {progress} ", end="", flush=True)
                time.sleep(1)
            print(f"\r -> 倒计时结束，准备提交。 [{current_num}/{total_num}]")
            
            print(f" -> 正在提交评价...")
            submit_response = self.session.post(SUBMIT_URL, data=payload, headers={'Referer': course_url})
            submit_response.raise_for_status()
            
            if "操作成功" in submit_response.text:
                print(" -> ✅ 提交成功！")
                return True
            else:
                print(" -> ❌ 提交失败，服务器返回信息未知。")
                return False
        except Exception as e:
            print(f" -> ❌ 评价过程中发生错误: {e}")
            return False

    def run(self):
        """执行主流程"""
        if not self._get_captcha_and_login():
            return
        if not self._perform_loading_action():
            return

        courses = self.get_unevaluated_courses()
        if not courses:
            print("\n没有需要评价的课程，程序结束。")
            return
        
        print("\n--- 开始自动评教 ---")
        total_courses = len(courses)
        for i, course_link in enumerate(courses, 1):
            print(f"\n[{i}/{total_courses}] 正在处理课程: {course_link}")
            # 将进度传递给 evaluate_course 函数
            self.evaluate_course(course_link, current_num=i, total_num=total_courses)
            
            if i < total_courses:
                print("...暂停3秒，防止请求过快...")
                time.sleep(3)
        print("\n--- 所有课程评价完成！ ---")


if __name__ == "__main__":
    print("--- 西南交大教务处自动评教脚本 ---")

    # 从 config.py 读取配置，如果密码为空则提示输入
    username = config.USERNAME
    password = config.PASSWORD

    if not password:
        print("提示：未在 config.py 中检测到密码，将提示手动输入。")
        password = getpass.getpass(f"请输入学号 '{username}' 的密码: ")

    if not username or not password:
        print("错误：学号或密码不能为空！")
    else:
        assessor = SWJTUAssessor(username=username, password=password)
        assessor.run()