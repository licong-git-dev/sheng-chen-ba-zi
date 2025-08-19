import os
from dotenv import load_dotenv
import dashscope
from flask import Flask, request, render_template, Response, stream_with_context, jsonify
from http import HTTPStatus
import json

# 在程序启动时加载 .env 文件中的环境变量
load_dotenv()

app = Flask(__name__)

# --- 安全地从环境变量获取API Key ---
api_key = os.getenv("DASHSCOPE_API_KEY")
if api_key:
    dashscope.api_key = api_key
else:
    print("警告：未找到 DASHSCOPE_API_KEY 环境变量。API调用将会失败。")


@app.route('/')
def index():
    return render_template('index.html')

def generate_stream(prompt):
    """一个通用的流式生成器函数"""
    if not dashscope.api_key:
        yield "错误：服务器未配置API Key。"
        return

    try:
        responses = dashscope.Generation.call(
            model='qwen-plus', # <--- 模型升级
            prompt=prompt,
            stream=True,
            result_format='text'
        )

        for resp in responses:
            if resp.status_code == HTTPStatus.OK:
                yield resp.output.text
            else:
                error_message = f"请求错误：code: {resp.code}, message: {resp.message}"
                print(error_message)
                yield error_message
                break
    except Exception as e:
        error_message = f"调用API时发生异常: {str(e)}"
        print(error_message)
        yield error_message

@app.route('/evaluate', methods=['POST'])
def evaluate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体必须是有效的JSON。'}), 400
        number = data.get('number')
    except Exception as e:
        return jsonify({'error': f'解析JSON请求失败: {str(e)}'}), 400

    if not number:
        return jsonify({'error': 'JSON请求体中必须包含 \'number\' 字段。'}), 400

    prompt = f"""
你是一位资深的数字能量解读专家和市场评估师，对中华文化中的数字谐音、易经卦象和现代商业价值有深入研究。
请为我分析手机号码尾号：{number}，并给出一个符合市场预期的趣味估值。

**分析维度**：
1.  **文化寓意**：深度解读数字的谐音和象征意义（例如，1314不仅是一生一世，也象征“一生一发”）。要求解读积极、新颖、令人信服。
2.  **易经智慧**：简要提及该数字组合可能关联的积极卦象及其现代启示（例如，乾卦的自强不息）。
3.  **能量磁场**：结合数字能量学，分析其包含的正向能量（如天医、延年、生气等），并说明其对个人运势的积极影响。
4.  **市场稀有度**：基于数字组合的稀有性和受欢迎程度，给出一个综合评价。

**输出要求**：
- **以JSON格式返回**，必须包含 `price`, `level`, `suggestion` 三个字段。
- **`price` (string)**：给出一个 **3000到8000之间** 的趣味评估价格，必须是整数，并以字符串形式表示。例如 `"4888"` 或 `"6666"`。
- **`level` (string)**：根据综合评估，给出号码等级（例如：稀有级、传说级、典藏级）。
- **`suggestion` (string)**：生成一段200-300字的综合建议，语言要专业、风趣、积极向上，总结该号码的价值和带来的好运。
- **严格遵守**：直接返回纯JSON对象，不包含任何额外说明或Markdown标记。
"""
    try:
        response = dashscope.Generation.call(
            model='qwen-plus', # <--- 模型升级
            prompt=prompt,
            result_format='text'
        )
        if response.status_code == HTTPStatus.OK:
            return Response(response.output.text, content_type='application/json')
        else:
            error_msg = f"API Error: Code: {response.code}, Message: {response.message}"
            return jsonify({'error': error_msg}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/fortune', methods=['POST'])
def fortune():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体必须是有效的JSON。'}), 400
        birthdate = data.get('birthdate')
    except Exception as e:
        return jsonify({'error': f'解析JSON请求失败: {str(e)}'}), 400

    if not birthdate:
        return jsonify({'error': 'JSON请求体中必须包含 \'birthdate\' 字段。'}), 400

    prompt = f"""
你是一位资深的人生导师，能融合现代心理学与东方智慧。
请根据我的生日 {birthdate}，为我撰写一份约300-400字的“个人天赋与能量蓝图”。
请用温暖、专业、富有启发性的语言，直接开始分析，无需客套。
请深入解读我的核心性格、事业潜能、情感模式，并给出未来一年的幸运建议。
"""
    return Response(stream_with_context(generate_stream(prompt)), content_type='text/plain; charset=utf-8')

if __name__ == '__main__':
    app.run(debug=True)