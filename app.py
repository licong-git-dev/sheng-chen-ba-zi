import os
from dotenv import load_dotenv
import dashscope
from flask import Flask, request, render_template, Response, stream_with_context, jsonify
from http import HTTPStatus
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io

# 强制加载项目根目录下的 .env 文件，并覆盖任何已存在的同名系统级环境变量
# 这能确保我们使用的是项目指定的API Key，而不是外部的无效Key
load_dotenv(override=True)

app = Flask(__name__)

# --- 安全地从环境变量获取API Key ---
api_key = os.getenv("DASHSCOPE_API_KEY")
print(f"Attempting to use API Key: {api_key[:5]}...{api_key[-4:] if api_key else 'None'}")
if api_key:
    dashscope.api_key = api_key
else:
    print("警告：未找到 DASHSCOPE_API_KEY 环境变量。API调用将会失败。")


@app.route('/')
def index():
    return render_template('index.html')

def generate_stream(prompt):
    """一个通用的流式生成器函数，只返回增量内容。"""
    if not dashscope.api_key:
        yield "错误：服务器未配置API Key。"
        return

    try:
        responses = dashscope.Generation.call(
            model='qwen-plus',
            prompt=prompt,
            stream=True,
            result_format='text'
        )

        previous_content = ""
        for resp in responses:
            if resp.status_code == HTTPStatus.OK:
                full_content = resp.output.text
                # 计算并发送增量内容
                incremental_content = full_content[len(previous_content):]
                yield incremental_content
                previous_content = full_content
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
- **`price` (string)**：必须给出一个 **3000到8000之间** 的趣味评估价格，必须是整数，并以字符串形式表示。**严禁总是给出相同的估值**，价格必须根据号码的吉利和稀有程度有显著的区分度。例如，普通号码估值可以是 `"3888"`，而稀有吉祥号（如888, 666）则应该估值更高，如 `"7888"`。
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
            raw_text = response.output.text
            # 找到第一个 '{' 和最后一个 '}' 来提取纯净的JSON字符串
            start_index = raw_text.find('{')
            end_index = raw_text.rfind('}')
            
            if start_index != -1 and end_index != -1 and start_index < end_index:
                json_str = raw_text[start_index:end_index+1]
                try:
                    # 在返回前，先在后端验证一下它是不是一个合法的JSON
                    json.loads(json_str)
                    return Response(json_str, content_type='application/json')
                except json.JSONDecodeError:
                    return jsonify({'error': 'AI返回了格式错误的JSON，无法解析。'}), 500
            else:
                return jsonify({'error': 'AI响应中不包含有效的JSON内容。'}), 500
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
请根据我的生日 {birthdate}，为我撰写一份约300-400字的"个人天赋与能量蓝图"。
请用温暖、专业、富有启发性的语言，直接开始分析，无需客套。
请深入解读我的核心性格、事业潜能、情感模式，并给出未来一年的幸运建议。
"""
    return Response(stream_with_context(generate_stream(prompt)), content_type='text/plain; charset=utf-8')

@app.route('/name_analysis', methods=['POST'])
def name_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体必须是有效的JSON。'}), 400
        name = data.get('name')
    except Exception as e:
        return jsonify({'error': f'解析JSON请求失败: {str(e)}'}), 400

    if not name:
        return jsonify({'error': 'JSON请求体中必须包含 \'name\' 字段。'}), 400

    prompt = f"""
你是一位传统文化学者，专门研究汉字文化和姓名学。
请对姓名：{name} 进行深度文化解读，注意这是传统文化分析，仅供娱乐参考。

**分析维度**：
1. **字形解读**：分析每个字的字形结构和文化内涵
2. **五行属性**：从传统五行理论角度分析字的属性
3. **音韵美学**：分析名字的音韵搭配和朗读效果
4. **文化寓意**：挖掘名字中蕴含的传统文化意义
5. **现代启示**：结合现代社会给出积极的人格特质分析

**输出要求**：
- 语言温和、积极、富有文化底蕴
- 长度约400-500字
- 强调这是传统文化解读，仅供娱乐参考
- 避免绝对化表述，多用"可能"、"倾向于"等词汇
"""
    return Response(stream_with_context(generate_stream(prompt)), content_type='text/plain; charset=utf-8')

@app.route('/lucky_draw', methods=['POST'])
def lucky_draw():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体必须是有效的JSON。'}), 400
        number = data.get('number')
    except Exception as e:
        return jsonify({'error': f'解析JSON请求失败: {str(e)}'}), 400

    if not number:
        return jsonify({'error': 'JSON请求体中必须包含 \'number\' 字段。'}), 400

    # 基于号码计算"幸运值"（纯娱乐）
    import hashlib
    hash_value = int(hashlib.md5(number.encode()).hexdigest()[:8], 16)
    luck_score = (hash_value % 100) + 1

    prizes = [
        {"name": "超级幸运星", "probability": 5, "color": "#ff6b6b"},
        {"name": "大吉大利", "probability": 10, "color": "#4ecdc4"},
        {"name": "财运亨通", "probability": 15, "color": "#45b7d1"},
        {"name": "事业有成", "probability": 20, "color": "#96ceb4"},
        {"name": "平安喜乐", "probability": 25, "color": "#feca57"},
        {"name": "好运连连", "probability": 25, "color": "#ff9ff3"}
    ]

    # 根据luck_score确定奖项
    cumulative = 0
    selected_prize = prizes[-1]  # 默认最后一个
    for prize in prizes:
        cumulative += prize["probability"]
        if luck_score <= cumulative:
            selected_prize = prize
            break

    return jsonify({
        "prize": selected_prize["name"],
        "color": selected_prize["color"],
        "score": luck_score,
        "message": f"恭喜！根据您的号码{number}，获得了【{selected_prize['name']}】！这是传统文化的趣味解读，愿好运伴随您！"
    })

@app.route('/generate_share_card', methods=['POST'])
def generate_share_card():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体必须是有效的JSON。'}), 400

        card_type = data.get('type', 'number')  # number, fortune, name, lucky
        content = data.get('content', {})
    except Exception as e:
        return jsonify({'error': f'解析JSON请求失败: {str(e)}'}), 400

    try:
        # 创建分享卡片图像
        width, height = 600, 800

        # 创建渐变背景
        image = Image.new('RGB', (width, height), '#6a11cb')
        draw = ImageDraw.Draw(image)

        # 绘制渐变背景
        for y in range(height):
            ratio = y / height
            r = int(106 * (1 - ratio) + 37 * ratio)
            g = int(17 * (1 - ratio) + 117 * ratio)
            b = int(203 * (1 - ratio) + 252 * ratio)
            color = (r, g, b)
            draw.line([(0, y), (width, y)], fill=color)

        # 尝试使用系统字体，如果不可用则使用默认字体
        try:
            title_font = ImageFont.truetype("arial.ttf", 36)
            subtitle_font = ImageFont.truetype("arial.ttf", 24)
            content_font = ImageFont.truetype("arial.ttf", 18)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            content_font = ImageFont.load_default()

        # 绘制标题
        title = "红姐数字能量站"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 50), title, fill='white', font=title_font)

        # 根据类型绘制不同内容
        if card_type == 'number':
            # 手机号码估值卡片
            number = content.get('number', '****')
            price = content.get('price', '未知')
            level = content.get('level', '普通级')

            # 绘制号码
            number_text = f"手机尾号: {number}"
            number_bbox = draw.textbbox((0, 0), number_text, font=subtitle_font)
            number_width = number_bbox[2] - number_bbox[0]
            draw.text(((width - number_width) // 2, 150), number_text, fill='white', font=subtitle_font)

            # 绘制价格
            price_text = f"估值: ¥{price}"
            price_bbox = draw.textbbox((0, 0), price_text, font=title_font)
            price_width = price_bbox[2] - price_bbox[0]
            draw.text(((width - price_width) // 2, 250), price_text, fill='#ffd700', font=title_font)

            # 绘制等级
            level_text = f"等级: {level}"
            level_bbox = draw.textbbox((0, 0), level_text, font=subtitle_font)
            level_width = level_bbox[2] - level_bbox[0]
            draw.text(((width - level_width) // 2, 350), level_text, fill='white', font=subtitle_font)

        elif card_type == 'lucky':
            # 幸运转盘卡片
            prize = content.get('prize', '好运连连')
            score = content.get('score', 50)

            # 绘制奖项
            prize_text = f"🎉 {prize} 🎉"
            prize_bbox = draw.textbbox((0, 0), prize_text, font=title_font)
            prize_width = prize_bbox[2] - prize_bbox[0]
            draw.text(((width - prize_width) // 2, 200), prize_text, fill='#ffd700', font=title_font)

            # 绘制分数
            score_text = f"幸运值: {score}"
            score_bbox = draw.textbbox((0, 0), score_text, font=subtitle_font)
            score_width = score_bbox[2] - score_bbox[0]
            draw.text(((width - score_width) // 2, 300), score_text, fill='white', font=subtitle_font)

        # 绘制底部文字
        footer_text = "仅供传统文化娱乐参考"
        footer_bbox = draw.textbbox((0, 0), footer_text, font=content_font)
        footer_width = footer_bbox[2] - footer_bbox[0]
        draw.text(((width - footer_width) // 2, height - 80), footer_text, fill='rgba(255,255,255,0.7)', font=content_font)

        # 将图像转换为base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        return jsonify({
            'image': f'data:image/png;base64,{img_base64}',
            'message': '分享卡片生成成功！'
        })

    except Exception as e:
        return jsonify({'error': f'生成分享卡片失败: {str(e)}'}), 500

# 简单的内存排行榜（实际项目中应使用数据库）
rankings = {
    'top_numbers': [
        {'number': '8888', 'price': '7888', 'level': '传说级', 'timestamp': '2024-01-01'},
        {'number': '6666', 'price': '6666', 'level': '稀有级', 'timestamp': '2024-01-01'},
        {'number': '1314', 'price': '5200', 'level': '典藏级', 'timestamp': '2024-01-01'},
        {'number': '0520', 'price': '4888', 'level': '经典级', 'timestamp': '2024-01-01'},
        {'number': '9999', 'price': '7999', 'level': '传说级', 'timestamp': '2024-01-01'},
    ],
    'recent_evaluations': []
}

@app.route('/rankings', methods=['GET'])
def get_rankings():
    """获取排行榜数据"""
    return jsonify({
        'top_numbers': rankings['top_numbers'][:10],  # 前10名
        'recent_evaluations': rankings['recent_evaluations'][-20:]  # 最近20次
    })

@app.route('/add_to_ranking', methods=['POST'])
def add_to_ranking():
    """添加评估结果到排行榜"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体必须是有效的JSON。'}), 400

        number = data.get('number')
        price = data.get('price', '0')
        level = data.get('level', '普通级')

        if not number:
            return jsonify({'error': '缺少必要参数'}), 400

        import datetime
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        # 添加到最近评估
        rankings['recent_evaluations'].append({
            'number': number,
            'price': price,
            'level': level,
            'timestamp': timestamp
        })

        # 保持最近评估列表不超过50条
        if len(rankings['recent_evaluations']) > 50:
            rankings['recent_evaluations'] = rankings['recent_evaluations'][-50:]

        # 如果价格足够高，添加到榜单
        price_num = int(price.replace(',', ''))
        if price_num > 4000:  # 只有高于4000的才进入榜单
            # 检查是否已存在
            existing = next((item for item in rankings['top_numbers'] if item['number'] == number), None)
            if not existing:
                rankings['top_numbers'].append({
                    'number': number,
                    'price': price,
                    'level': level,
                    'timestamp': timestamp
                })
                # 按价格排序，保持前20名
                rankings['top_numbers'].sort(key=lambda x: int(x['price'].replace(',', '')), reverse=True)
                rankings['top_numbers'] = rankings['top_numbers'][:20]

        return jsonify({'message': '添加成功'})

    except Exception as e:
        return jsonify({'error': f'添加失败: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)