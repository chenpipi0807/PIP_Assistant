import gradio as gr
import requests
import json
import os

# 从相对路径的key.txt文件中读取API密钥
def get_api_key():
    current_dir = os.path.dirname(__file__)  # 获取当前脚本的目录
    key_file_path = os.path.join(current_dir, "key.txt")  # 构造key.txt的路径
    try:
        with open(key_file_path, "r") as file:
            return file.read().strip()  # 读取并返回API密钥
    except FileNotFoundError:
        raise FileNotFoundError(f"API密钥文件未找到，请确保key.txt文件位于 {current_dir} 目录中。")

# 获取API密钥
API_KEY = get_api_key()
API_URL = "https://api.moonshot.cn/v1/chat/completions"

# 八字排盘函数
def bazi_analysis(birth_date, gender, birth_time, birth_place):
    # 构造请求数据
    request_data = {
        "model": "moonshot-v1-8k",
        "messages": [
            {
                "role": "user",
                "content": f"请根据以下信息进行八字排盘：出生日期 {birth_date}，性别 {gender}，出生时辰 {birth_time}，出生地 {birth_place}。"
            }
        ]
    }
    
    # 发送请求
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    response = requests.post(API_URL, headers=headers, data=json.dumps(request_data))
    
    # 解析响应
    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    else:
        return f"Error: Unable to fetch data from Moonshot AI API. Status Code: {response.status_code}"

# 创建Gradio界面
with gr.Blocks() as demo:
    gr.Markdown("# 八字排盘")
    birth_date = gr.Textbox(label="出生日期（格式：YYYY-MM-DD）")
    gender = gr.Radio(["男", "女"], label="性别")
    birth_time = gr.Textbox(label="出生时辰（格式：辰时等）")
    birth_place = gr.Textbox(label="出生地")
    output = gr.Textbox(label="八字分析结果")
    
    # 按钮点击事件
    button = gr.Button("分析八字")
    button.click(fn=bazi_analysis, inputs=[birth_date, gender, birth_time, birth_place], outputs=output)

# 启动应用
demo.launch()