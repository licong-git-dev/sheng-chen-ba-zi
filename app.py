import os
from dotenv import load_dotenv
import dashscope
from flask import Flask, request, render_template, Response, stream_with_context, jsonify
from http import HTTPStatus
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import time
import requests

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

def call_ai_with_retry(prompt, stream=False, max_retries=3):
    """带重试机制的AI调用函数"""
    for attempt in range(max_retries):
        try:
            if stream:
                return dashscope.Generation.call(
                    model='qwen-plus',
                    prompt=prompt,
                    stream=True,
                    result_format='text',
                    parameters={
                        'temperature': 0.8,
                        'top_k': 50,
                        'top_p': 0.9,
                        'max_tokens': 1500,
                        'repetition_penalty': 1.1,
                        'seed': None,
                        'incremental_output': True
                    }
                )
            else:
                return dashscope.Generation.call(
                    model='qwen-plus',
                    prompt=prompt,
                    result_format='text',
                    parameters={
                        'temperature': 0.7,
                        'top_k': 50,
                        'top_p': 0.9,
                        'max_tokens': 2000,
                        'repetition_penalty': 1.1,
                        'seed': None,
                        'incremental_output': False
                    }
                )
        except Exception as e:
            print(f"AI调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise e

def generate_stream(prompt):
    """一个通用的流式生成器函数，只返回增量内容。"""
    if not dashscope.api_key:
        yield "错误：服务器未配置API Key。"
        return

    try:
        responses = call_ai_with_retry(prompt, stream=True)

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
作为专业的数字文化研究专家和趣味评估师，请分析手机尾号：{number}

**角色设定**：你是红姐数字能量站的首席分析师，擅长用现代语言解读传统数字文化，语言风格要生动有趣、通俗易懂。

**分析框架**（请严格按此顺序分析）：
1. **谐音寓意**：分析数字的中文谐音含义，要有创意且积极正面
2. **数字能量**：从传统数字学角度解读其能量属性
3. **市场价值**：基于稀有度和吉祥程度评估市场价值
4. **运势影响**：说明对主人可能带来的积极影响

**重要约束条件**：
- 必须输出标准JSON格式
- price字段：根据号码特殊性给出3000-8000的价格（整数字符串）
- level字段：选择适合的等级（普通级/优质级/稀有级/典藏级/传说级）
- suggestion字段：200-300字的专业建议，要有具体的文化内涵解释

**特别要求**：
- 绝对不要输出相同的价格，必须根据号码特征有差异化定价
- 语言要符合中文表达习惯，避免翻译腔
- 内容要富有文化底蕴但通俗易懂
- 只返回JSON，不要任何额外文字

请开始分析尾号：{number}
"""
    # 检查缓存
    cache_key = get_cache_key("evaluate", number)
    cached_result = get_cached_result(cache_key)
    if cached_result:
        return Response(cached_result, content_type='application/json')

    try:
        response = call_ai_with_retry(prompt, stream=False)
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
                    # 保存到缓存
                    set_cache_result(cache_key, json_str)
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
**角色**：你是红姐数字能量站的命理文化专家，专门从传统文化角度解读生辰信息。

**任务**：根据生日 {birthdate} 进行传统文化分析

**分析要求**：
1. **性格特质**：从出生月份、季节等角度分析性格倾向
2. **天赋优势**：分析可能具备的天然优势和潜能
3. **情感特征**：解读在人际关系中的表现特点
4. **事业方向**：建议适合的发展领域和方式
5. **开运建议**：给出未来一年的吉祥提醒

**输出规范**：
- 语言要温暖亲切，如红姐亲自解读
- 内容要具体实用，不空泛
- 长度控制在350-450字
- 要体现中华传统文化底蕴
- 语气积极正面，给人希望和动力

**重要声明**：请在开头说明这是"传统文化娱乐解读，仅供参考"

现在开始为生日{birthdate}的朋友进行解读：
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
**角色**：你是红姐数字能量站的汉字文化专家，专注传统姓名文化解读。

**任务**：为姓名"{name}"进行传统文化解析

**解读框架**：
1. **字音解析**：分析姓名的音韵特点和谐音寓意
2. **字形文化**：解读汉字结构蕴含的文化内涵
3. **五行能量**：从传统五行角度分析姓名能量
4. **性格映射**：推测可能的性格特质和天赋
5. **人生暗示**：分析姓名对人生路径的积极指引

**表达风格**：
- 用红姐温暖亲切的语调
- 语言要生动有趣，避免学术化
- 多用"可能"、"倾向于"等谦逊表述
- 内容积极正面，给人启发
- 长度控制在420-520字

**合规要求**：
- 开头必须声明"这是传统文化娱乐解读，仅供参考"
- 强调姓名只是文化符号，人生靠自己努力
- 避免任何绝对化的预测表述

现在开始为"{name}"进行姓名文化解读：
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
        # 优化：使用更小的图像尺寸提高性能
        width, height = 400, 600

        # 创建分享卡片图像（优化版本）
        image = Image.new('RGB', (width, height), '#6a11cb')
        draw = ImageDraw.Draw(image)

        # 简化渐变背景绘制（减少循环次数）
        gradient_steps = 50  # 减少渐变步数提高性能
        step_height = height // gradient_steps

        for i in range(gradient_steps):
            y = i * step_height
            ratio = i / gradient_steps
            r = int(106 * (1 - ratio) + 37 * ratio)
            g = int(17 * (1 - ratio) + 117 * ratio)
            b = int(203 * (1 - ratio) + 252 * ratio)
            color = (r, g, b)
            draw.rectangle([(0, y), (width, y + step_height)], fill=color)

        # 优化字体加载（使用默认字体提高性能）
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
        draw.text(((width - footer_width) // 2, height - 80), footer_text, fill='white', font=content_font)

        # 优化图片压缩输出
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85, optimize=True)  # 使用JPEG格式和85%质量
        img_base64 = base64.b64encode(buffered.getvalue()).decode()

        return jsonify({
            'image': f'data:image/jpeg;base64,{img_base64}',
            'message': '分享卡片生成成功！'
        })

    except Exception as e:
        return jsonify({'error': f'生成分享卡片失败: {str(e)}'}), 500

# 排行榜数据持久化存储
import os
import json

RANKINGS_FILE = 'rankings.json'

# 默认排行榜数据
default_rankings = {
    'top_numbers': [
        {'number': '8888', 'price': '7888', 'level': '传说级', 'timestamp': '2024-01-01'},
        {'number': '6666', 'price': '6666', 'level': '稀有级', 'timestamp': '2024-01-01'},
        {'number': '1314', 'price': '5200', 'level': '典藏级', 'timestamp': '2024-01-01'},
        {'number': '0520', 'price': '4888', 'level': '经典级', 'timestamp': '2024-01-01'},
        {'number': '9999', 'price': '7999', 'level': '传说级', 'timestamp': '2024-01-01'},
    ],
    'recent_evaluations': []
}

def load_rankings():
    """从文件加载排行榜数据"""
    try:
        if os.path.exists(RANKINGS_FILE):
            with open(RANKINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return default_rankings.copy()
    except Exception as e:
        print(f"加载排行榜数据失败: {e}")
        return default_rankings.copy()

def save_rankings(rankings):
    """保存排行榜数据到文件"""
    try:
        with open(RANKINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(rankings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存排行榜数据失败: {e}")

# 加载初始数据
rankings = load_rankings()

# 简单的内存缓存
cache = {}
CACHE_DURATION = 300  # 5分钟缓存

def get_cache_key(prefix, data):
    """生成缓存键"""
    return f"{prefix}:{hash(str(data))}"

def get_cached_result(cache_key):
    """获取缓存结果"""
    if cache_key in cache:
        result, timestamp = cache[cache_key]
        if time.time() - timestamp < CACHE_DURATION:
            return result
        else:
            del cache[cache_key]
    return None

def set_cache_result(cache_key, result):
    """设置缓存结果"""
    cache[cache_key] = (result, time.time())

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

        # 保存数据到文件
        save_rankings(rankings)
        return jsonify({'message': '添加成功'})

    except Exception as e:
        return jsonify({'error': f'添加失败: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)