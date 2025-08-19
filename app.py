from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import time
import json
from datetime import datetime

app = Flask(__name__)

# --- 模型已被移除 ---
# 由于 Vercel 无法托管大型 AI 模型，我们将使用固定的占位符数据来模拟模型响应
# 这样可以让网站前端成功部署并运行起来

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/evaluate', methods=['POST'])
def evaluate_number():
    """手机号评估的占位符版本"""
    data = request.get_json()
    if not data or 'number' not in data:
        return jsonify({'error': '请求参数错误，需要提供 number 字段'}), 400

    number = data['number']
    if not isinstance(number, str) or not number.isdigit() or len(number) != 4:
        return jsonify({'error': '号码必须是4位数字字符串'}), 400

    # 返回一个固定的、模拟的JSON响应
    placeholder_result = {
      "price": "8888元",
      "level": "吉祥",
      "suggestion": f"这是一个为手机尾号 {number} 生成的模拟分析。由于AI模型无法在此平台运行，我们返回一个固定的示例结果。真正的运势分析需要将模型部署在专门的服务器上才能实现。"
    }
    print(f"返回占位符结果: {placeholder_result}")
    return jsonify(placeholder_result)

@app.route('/fortune', methods=['POST'])
def get_fortune():
    """生辰八字算命的占位符版本（流式）"""
    data = request.get_json()
    if not data or 'birthdate' not in data:
        return jsonify({'error': '请求参数错误，需要提供 birthdate 字段'}), 400

    birthdate = data['birthdate']

    def generate_fake_stream():
        """一个模拟的流式响应生成器"""
        try:
            # 验证日期格式
            datetime.strptime(birthdate, "%Y/%m/%d")
            
            yield "data: 正在为您生成分析报告...\n\n"
            time.sleep(0.5)
            yield f"data: **用户信息**\n- **生日**: {birthdate}\n\n"
            time.sleep(0.5)
            yield "data: **性格分析**\n这是一个模拟的性格分析。由于无法在此平台加载AI模型，我们返回固定的示例内容。\n\n"
            time.sleep(0.5)
            yield "data: **运势总结**\n这是一个模拟的运势总结。您未来的事业、财运、健康和感情都需要您继续努力！\n\n"
            time.sleep(0.5)
            yield "data: **开运建议**\n保持积极心态，多喝水，常运动！"
        except ValueError:
            yield "data: 日期格式不正确或日期无效，请使用 YYYY/MM/DD 格式并确保日期真实存在。"

    # 使用 Response 对象来创建流式响应
    return Response(stream_with_context(generate_fake_stream()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)