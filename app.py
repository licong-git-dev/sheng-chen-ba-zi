import os
from dotenv import load_dotenv
from flask import Flask, request, render_template, Response, stream_with_context, jsonify
from http import HTTPStatus
import json
import base64
from PIL import Image, ImageDraw, ImageFont
import io
import time
import requests

# Vercel环境适配：优先从环境变量加载配置
# 在无服务器环境中，不依赖.env文件
try:
    load_dotenv(override=True)
except:
    pass  # 在Vercel环境中可能没有.env文件

app = Flask(__name__)

# 检测是否为Vercel环境
VERCEL_ENV = os.getenv('VERCEL_ENV') or os.getenv('VERCEL') or os.getenv('NOW_REGION')
IS_VERCEL = VERCEL_ENV is not None

# AI服务配置
if not IS_VERCEL:
    try:
        import dashscope
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if api_key:
            print(f"API Key loaded successfully: {api_key[:5]}...{api_key[-4:]}")
            dashscope.api_key = api_key
        else:
            print("警告：未找到 DASHSCOPE_API_KEY 环境变量。")
    except ImportError:
        print("警告：dashscope模块未安装，使用备用响应。")
        IS_VERCEL = True
else:
    print("检测到Vercel环境，使用预设响应模式。")


@app.route('/')
def index():
    return render_template('index.html')

def call_ai_with_retry(prompt, stream=False, max_retries=3):
    """带重试机制的AI调用函数，Vercel环境使用预设响应"""
    if IS_VERCEL:
        # Vercel环境使用预设的高质量中文响应
        return get_vercel_preset_response(prompt)
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

        # 统一处理响应文本获取
        if isinstance(response, str):
            # Vercel预设响应，直接是JSON字符串
            raw_text = response
        elif hasattr(response, 'status_code') and response.status_code == HTTPStatus.OK:
            # dashscope API响应
            raw_text = response.output.text
        else:
            # 其他情况
            raw_text = str(response)

        # 处理JSON提取
        start_index = raw_text.find('{')
        end_index = raw_text.rfind('}')

        if start_index != -1 and end_index != -1 and start_index < end_index:
            json_str = raw_text[start_index:end_index+1]
            try:
                # 验证JSON格式
                json.loads(json_str)
                # 保存到缓存
                set_cache_result(cache_key, json_str)
                return Response(json_str, content_type='application/json')
            except json.JSONDecodeError:
                # 如果提取的不是有效JSON，尝试直接使用原始文本
                try:
                    json.loads(raw_text)
                    set_cache_result(cache_key, raw_text)
                    return Response(raw_text, content_type='application/json')
                except:
                    return jsonify({'error': 'AI返回了格式错误的JSON，无法解析。'}), 500
        else:
            # 没有找到JSON结构，尝试直接解析原始文本
            try:
                json.loads(raw_text)
                set_cache_result(cache_key, raw_text)
                return Response(raw_text, content_type='application/json')
            except:
                return jsonify({'error': 'AI响应中不包含有效的JSON内容。'}), 500
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

# Vercel适配：使用内存存储代替文件存储
# 在无服务器环境中无法进行持久化文件写入
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

        # Vercel适配：内存存储，无需文件操作
        return jsonify({'message': '添加成功'})

    except Exception as e:
        return jsonify({'error': f'添加失败: {str(e)}'}), 500

def get_vercel_preset_response(prompt):
    """Vercel环境的预设响应函数"""
    import hashlib
    import random

    # 基于prompt生成稳定的随机种子
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    random.seed(seed)

    # 检测是否为数字评估请求
    if "手机尾号" in prompt or "数字能量" in prompt:
        # 提取数字
        import re
        numbers = re.findall(r'\d{4}', prompt)
        if numbers:
            number = numbers[0]
            return generate_number_analysis(number)

    # 检测是否为生辰分析请求
    if "生辰八字" in prompt or "出生日期" in prompt:
        return generate_fortune_analysis()

    # 检测是否为姓名分析请求
    if "姓名" in prompt:
        return generate_name_analysis()

    # 默认响应
    return "感谢您使用红姐数字能量站！这是基于传统文化的趣味解读，仅供娱乐参考，请以科学理性的态度对待生活。"

def generate_number_analysis(number):
    """生成数字能量分析"""
    analysis_templates = {
        "1314": {
            "homophonic_meaning": "'1314'谐音'一生一世'，堪称爱情的数字诗篇。在中文语境中，它象征着永恒的陪伴与不渝的承诺，常用于表白、婚恋场景，是情感长跑中的甜蜜密码。这个组合把浪漫刻进了数字基因，堪称移动的情书。",
            "numerical_energy": "从数字能量学看，'1'代表开创与独立，如同晨曦初露，充满向上的生命力；'3'象征活力与表达，如春风拂面；'4'在此非指'死'，而是'稳'的化身，代表踏实与持久。三者共振，形成'进取—绽放—坚守'的能量闭环，寓意事业有成、感情稳定。",
            "market_value": "由于其深入人心的情感寓意，1314在婚庆、情侣号、纪念日礼品市场备受欢迎。虽非极端稀有，但文化认同度极高，属于高流通性的吉祥号码，具备持续增值潜力。",
            "fortune_impact": "持有此号者易吸引稳定关系与长久合作，尤其利于从事情感咨询、婚庆服务、文化创意等行业。在人际交往中自带亲和力光环，有助于建立信任与深度连接，是情感与事业双线发展的隐形助力。"
        },
        "8888": {
            "homophonic_meaning": "'8888'四连发，谐音'发发发发'，是财富与成功的终极象征。在传统文化中，'8'形似无穷符号，寓意财源滚滚、生生不息。四个'8'的组合如同四方来财，预示着全方位的兴旺发达。",
            "numerical_energy": "从数字能量学角度，'8'代表物质成就与权威地位，具有强烈的聚财磁场。四个'8'连续出现，形成超强的财富振频，有助于提升个人的商业敏感度和投资直觉，是天然的财富吸引器。",
            "market_value": "8888作为顶级吉祥号码，在商界和收藏界享有极高声誉。无论是手机号、车牌还是门牌号，都是身份与财力的象征，具有极强的保值增值能力。",
            "fortune_impact": "持有者往往在商业领域表现出色，容易获得贵人相助和投资机会。这个号码特别适合企业家、金融从业者和销售人员，能够增强个人的商业魅力和谈判能力。"
        }
    }

    # 获取特定数字的分析，如果没有则生成通用分析
    if number in analysis_templates:
        return json.dumps(analysis_templates[number], ensure_ascii=False)
    else:
        # 生成通用分析
        import random
        random.seed(int(number))

        meanings = [
            "寓意吉祥如意，代表着美好的愿望和期待",
            "象征着稳步前进，预示着事业的稳定发展",
            "体现了和谐平衡，有助于人际关系的改善",
            "代表着创新突破，预示着新的机遇和发展"
        ]

        energies = [
            "从数字能量学看，这个组合具有正向的磁场效应",
            "数字排列体现了阴阳平衡的和谐状态",
            "蕴含着稳定而持续的能量波动",
            "展现了积极向上的生命力量"
        ]

        return json.dumps({
            "homophonic_meaning": f"'{number}'{random.choice(meanings)}，在传统文化中被视为吉祥的象征。",
            "numerical_energy": random.choice(energies) + "，有助于提升个人的正能量磁场。",
            "market_value": "这个数字组合在传统文化中具有一定的收藏价值，体现了对美好生活的向往。",
            "fortune_impact": "持有者可能在相关领域获得更多的关注和机会，有助于个人发展和人际交往。"
        }, ensure_ascii=False)

def generate_fortune_analysis():
    """生成生辰八字分析"""
    return "根据传统文化的解读角度，您的生辰蕴含着独特的人生密码。从五行角度来看，您的命格中蕴含着平衡与和谐的特质，预示着稳定的人生发展。不过，这些都是传统文化的趣味解读，现代生活还是要靠自己的努力和奋斗！"

def generate_name_analysis():
    """生成姓名分析"""
    return "从姓名文化学的角度来看，您的姓名字形优美，读音和谐，蕴含着深厚的文化底蕴。在传统文化中，这样的名字往往预示着文雅的气质和良好的人缘。当然，这只是传统文化的解读方式，真正的人生成就还是要靠个人的努力和品德！"

# Vercel部署适配
# 确保app实例可以被Vercel访问
application = app

if __name__ == '__main__':
    app.run(debug=True)