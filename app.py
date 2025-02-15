from flask import Flask, render_template, request, jsonify, send_from_directory, Response, redirect, url_for
import logging
import traceback
import json
import os
from werkzeug.utils import secure_filename
import httpx
from functools import wraps
from typing import Generator, List, Dict, Any, Optional
from dataclasses import dataclass
import time
import PyPDF2
from docx import Document
import uuid
import datetime
import socket
import psutil
from dotenv import load_dotenv
import openai

# 加载环境变量
load_dotenv()

# 配置类
class Config:
    UPLOAD_FOLDER = 'uploads'
    ARK_API_KEY = os.getenv("ARK_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
    ENDPOINT_ID = "你的飞舟id"

# 初始化应用
app = Flask(__name__)
app.config.from_object(Config)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 配置静态文件路由
app.static_folder = 'static'
app.static_url_path = '/static'

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 错误处理装饰器
def handle_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            error_msg = f"Error in {f.__name__}: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return jsonify({"error": error_msg}), 500
    return wrapper

# 请求速率限制装饰器
def rate_limit(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # 简单的速率限制实现
        time.sleep(0.1)  # 每个请求至少间隔 0.1 秒
        return f(*args, **kwargs)
    return wrapper

# 支持的文件类型
ALLOWED_CODE_EXTENSIONS = {
    'py', 'js', 'html', 'css', 'json', 'xml', 'yaml', 'yml', 
    'md', 'txt', 'ini', 'conf', 'sh', 'bat', 'ps1'
}
ALLOWED_DOC_EXTENSIONS = {'doc', 'docx', 'pdf', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'rtf'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename, file_type='code'):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if file_type == 'code':
        return ext in ALLOWED_CODE_EXTENSIONS
    elif file_type == 'doc':
        return ext in ALLOWED_DOC_EXTENSIONS
    elif file_type == 'image':
        return ext in ALLOWED_IMAGE_EXTENSIONS
    return False

# 工具函数
def create_chat_completion(messages: List[Dict[str, str]], stream: bool = False) -> Any:
    """创建对话"""
    client = openai.OpenAI(
        api_key=Config.ARK_API_KEY,
        base_url=Config.OPENAI_BASE_URL,
        http_client=httpx.Client(
            timeout=1800,  # 30分钟超时
            follow_redirects=True
        )
    )
    
    try:
        response = client.chat.completions.create(
            model=Config.ENDPOINT_ID,
            messages=messages,
            stream=stream,
            temperature=0.7,
            max_tokens=2000
        )
        return response
    except Exception as e:
        logging.error(f"OpenAI API 调用失败: {str(e)}")
        raise

def process_file_content(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def process_with_ai(prompt: str) -> str:
    """使用AI处理文本内容"""
    try:
        response = create_chat_completion([
            {"role": "user", "content": prompt}
        ], stream=False)
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"AI处理失败: {str(e)}")
        return f"处理失败: {str(e)}"

# 存储对话历史的数据结构
conversations = {}

def get_conversations():
    """获取所有会话"""
    return list(conversations.values())

def create_conversation():
    """创建新会话"""
    conversation_id = str(uuid.uuid4())
    conversations[conversation_id] = {
        'id': conversation_id,
        'messages': [],
        'created_at': datetime.datetime.now().isoformat(),
        'updated_at': datetime.datetime.now().isoformat()
    }
    return conversations[conversation_id]

def get_conversation(conversation_id):
    """获取指定会话"""
    return conversations.get(conversation_id)

def add_message(conversation_id: str, role: str, content: str, reasoning: str = None):
    """添加消息到会话"""
    if conversation_id not in conversations:
        return False
    
    message = {
        "role": role,
        "content": content
    }
    if reasoning:
        message["reasoning_content"] = reasoning
    
    conversations[conversation_id]['messages'].append(message)
    conversations[conversation_id]['updated_at'] = datetime.datetime.now().isoformat()
    return True

def delete_conversation(conversation_id):
    """删除会话"""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return True
    return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
@handle_errors
def ask():
    """处理用户问题"""
    data = request.json
    conversation_id = data.get('conversation_id')
    message = data.get('message', '').strip()
    search_enabled = data.get('search_enabled', False)

    if not message:
        return jsonify({'error': '消息不能为空'}), 400

    # 获取或创建会话
    conversation = get_conversation(conversation_id)
    if not conversation:
        conversation = create_conversation()
        conversation_id = conversation['id']

    # 添加用户消息到会话历史
    add_message(conversation_id, "user", message)

    # 准备消息列表
    messages = [
        {"role": "system", "content": "你是一个多功能助手，可以回答问题，解释概念，提供建议，翻译文本等。"},
    ]
    messages.extend(conversation['messages'])

    # 生成响应
    def generate():
        content_buffer = ""
        current_sentence = ""
        reasoning_buffer = ""
        
        try:
            response = create_chat_completion(messages, stream=True)
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta:
                    delta = chunk.choices[0].delta
                    
                    # 检查是否有思维链内容
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        reasoning_buffer += delta.reasoning_content
                        # 直接发送当前完整的思维链内容
                        yield f'data: {{"type": "reasoning", "content": {json.dumps(reasoning_buffer)}}}\n\n'
                    
                    # 处理主要内容
                    if delta.content:
                        content_chunk = delta.content
                        current_sentence += content_chunk
                        content_buffer += content_chunk
                        
                        # 当遇到句子结束符时，发送完整的句子
                        if any(current_sentence.endswith(end) for end in ['.', '!', '?', '\n']):
                            yield f'data: {{"type": "content", "content": {json.dumps(content_buffer)}}}\n\n'
                            current_sentence = ""

            # 发送剩余的内容
            if current_sentence:
                yield f'data: {{"type": "content", "content": {json.dumps(content_buffer)}}}\n\n'

            # 添加助手回复到会话历史
            add_message(conversation_id, "assistant", content_buffer, reasoning_buffer)
            
            # 发送结束信号
            yield 'data: {"type": "done"}\n\n'
            
        except Exception as e:
            logging.error(f"处理消息时出错: {str(e)}")
            logging.error(traceback.format_exc())
            error_message = {"type": "error", "content": str(e)}
            yield f'data: {json.dumps(error_message)}\n\n'

    return Response(generate(), mimetype='text/event-stream')

@app.route('/conversations', methods=['GET'])
def list_conversations():
    """获取所有会话列表"""
    return jsonify(get_conversations())

@app.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation_route(conversation_id):
    """获取指定会话"""
    conversation = get_conversation(conversation_id)
    if not conversation:
        return jsonify({"error": "会话不存在"}), 404
    return jsonify(conversation)

@app.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation_route(conversation_id):
    """删除会话"""
    if delete_conversation(conversation_id):
        return '', 204
    return jsonify({"error": "会话不存在"}), 404

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件被上传'})
    
    file = request.files['file']
    file_type = request.form.get('type', '')
    user_message = request.form.get('message', '').strip()
    
    if file.filename == '':
        return jsonify({'error': '没有选择文件'})
    
    try:
        # 获取文件内容
        content = ''
        if file_type == 'code' or file_type == 'document':
            if file.filename.endswith('.pdf'):
                # 处理PDF文件
                pdf_reader = PyPDF2.PdfReader(file)
                content = '\n'.join([page.extract_text() for page in pdf_reader.pages])
            elif file.filename.endswith(('.doc', '.docx')):
                # 处理Word文件
                doc = Document(file)
                content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            else:
                # 处理文本文件
                content = file.read().decode('utf-8')
        elif file_type == 'image':
            # 处理图片文件
            content = '图片已上传成功，正在分析...'
        
        # 构建提示词
        prompt = f"""分析以下{file_type}文件，文件名为{file.filename}。
{f'问题：{user_message}' if user_message else '请分析文件内容并给出建议。'}

文件内容：
```{'python' if file.filename.endswith('.py') else 'plaintext'}
{content}
```

请按以下格式回复：
1. 先用[思考过程]...[/思考过程]标记你的分析过程
2. 如果需要展示代码，使用 ```语言名 代码 ``` 格式
3. 保持专业、简洁和友好的语气"""
        
        # 调用AI处理文件内容
        response = create_chat_completion([
            {"role": "system", "content": "你是一个专业的代码分析助手，擅长分析各种文件并给出建议。"},
            {"role": "user", "content": prompt}
        ], stream=False)
        
        return jsonify({
            'success': True,
            'content': response.choices[0].message.content
        })
        
    except Exception as e:
        logger.error(f"处理文件时出错: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'error': f'处理文件时出错: {str(e)}'
        })

@app.route('/search', methods=['POST'])
@handle_errors
def search():
    """搜索功能"""
    query = request.json.get('query', '')
    if not query:
        return jsonify({'error': '搜索查询不能为空'}), 400

    response = create_chat_completion([
        {"role": "system", "content": """你是一个专业的搜索助手。在回答问题时：
1. 先用[思考过程]...[/思考过程]标记你的分析和搜索过程
2. 如果需要展示代码，使用 ```语言名 代码 ``` 格式
3. 保持专业、简洁和友好的语气"""},
        {"role": "user", "content": f"请搜索并回答以下问题：{query}"}
    ], stream=False)
    
    return jsonify({
        'content': response.choices[0].message.content,
        'reasoning': response.choices[0].message.get('reasoning_content')
    })

@app.route('/static/image/<path:filename>')
def serve_image(filename):
    app.logger.info(f'Requesting image: {filename}')
    try:
        response = send_from_directory('static/image', filename)
        app.logger.info(f'Successfully served image: {filename}')
        return response
    except Exception as e:
        app.logger.error(f'Error serving image {filename}: {str(e)}')
        return f'Error loading image: {str(e)}', 500

if __name__ == '__main__':
    import atexit
    import signal
    import sys
    
    def check_port(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return True
        except socket.error:
            return False

    def kill_process_on_port(port):
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections(kind='tcp'):
                    if conn.laddr.port == port:
                        print(f"Terminating process {proc.pid} using port {port}")
                        proc.terminate()
                        proc.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue

    def cleanup():
        print("正在关闭服务器...")
        # 确保端口 5000 被释放
        kill_process_on_port(5000)
        sys.exit(0)

    # 注册清理函数
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTERM, lambda s, f: cleanup())

    # 在启动前检查并清理端口
    if not check_port(5000):
        print("端口 5000 已被占用，正在尝试释放...")
        kill_process_on_port(5000)
        time.sleep(1)  # 等待端口完全释放

    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
