import requests
from bs4 import BeautifulSoup
import time
import random
from utils.ocr import classify

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

    def _get_captcha_and_login(self, max_attempts=5):
        """自动识别验证码并登录，最多尝试 max_attempts 次"""
        for attempt in range(1, max_attempts + 1):
            print(f"\n--- 第 {attempt}/{max_attempts} 次尝试登录 ---")
            
            try:
                # 获取验证码
                print("正在获取验证码...")
                captcha_params = {'test': int(time.time() * 1000)}
                response = self.session.get(CAPTCHA_URL, params=captcha_params)
                response.raise_for_status()
                captcha_bytes = response.content
                
                # 使用 OCR 自动识别
                print("正在使用 OCR 自动识别验证码...")
                captcha_code = classify(captcha_bytes)
                print(f"OCR 识别结果: {captcha_code}")
                
            except Exception as e:
                print(f"获取或识别验证码失败: {e}")
                if attempt < max_attempts:
                    print(f"等待 1 秒后重试...")
                    time.sleep(1)
                    continue
                else:
                    raise Exception(f"获取或识别验证码失败，已重试 {max_attempts} 次: {e}")
            
            # 尝试登录
            print("正在提交登录...")
            login_payload = { 
                'username': self.username, 
                'password': self.password, 
                'ranstring': captcha_code, 
                'url': '', 
                'returnType': '', 
                'returnUrl': '', 
                'area': '' 
            }
            login_headers = self.session.headers.copy()
            login_headers['Referer'] = LOGIN_PAGE_URL
            
            try:
                response = self.session.post(LOGIN_API_URL, data=login_payload, headers=login_headers)
                response.raise_for_status()
                login_result = response.json()
                
                if login_result.get('loginStatus') == '1':
                    print(f"✅ 登录成功！{login_result.get('loginMsg')}")
                    return True
                else:
                    error_msg = login_result.get('loginMsg', '服务器未返回明确错误信息')
                    print(f"❌ 登录失败: {error_msg}")
                    
                    # 检查是否为密码错误，如果是则不需要重试验证码
                    if '密码' in error_msg:
                        raise Exception(f"登录失败: {error_msg}")
                    
                    if attempt < max_attempts:
                        print(f"等待 1 秒后重试...")
                        time.sleep(1)
                    
            except Exception as e:
                print(f"登录请求异常: {e}")
                if attempt < max_attempts:
                    print(f"等待 1 秒后重试...")
                    time.sleep(1)
                else:
                    raise Exception(f"登录失败，已重试 {max_attempts} 次: {e}")
        
        raise Exception(f"已达到最大尝试次数 ({max_attempts})，登录失败。")

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
            raise Exception(f"访问加载页面失败: {e}")

    def get_unevaluated_courses(self):
        print("\n正在获取待评价课程列表...")
        try:
            headers = self.session.headers.copy()
            headers['Referer'] = LOADING_URL
            response = self.session.get(ASSESS_LIST_URL, headers=headers)
            response.raise_for_status()
            if "非常抱歉，您还未登陆" in response.text:
                 raise Exception("获取课程列表失败，服务器仍然认为我们未登录。")
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            for a_tag in soup.find_all('a', string='填写问卷'):
                relative_path = a_tag['href'].replace('..', '')
                full_link = f"{BASE_URL}{relative_path}"
                links.append(full_link)
            print(f"成功找到 {len(links)} 门待评价课程。")
            return links
        except Exception as e:
            raise Exception(f"获取课程列表失败: {e}")

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
            
            if "操作成功" not in submit_response.text:
                raise Exception("提交失败，服务器返回信息未知。")
            
            print(" -> ✅ 提交成功！")
            return True
        except Exception as e:
            raise Exception(f"评价过程中发生错误: {e}")

    def run(self):
        """执行主流程"""
        self._get_captcha_and_login()
        self._perform_loading_action()

        courses = self.get_unevaluated_courses()
        if not courses:
            print("没有需要评价的课程")
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
