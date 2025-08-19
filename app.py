from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer
import torch
import json
from datetime import datetime

app = Flask(__name__)

# 配置模型和分词器路径
model_path = "d:\\app\\PythonFiles\\douyin_number_evaluation\\Qwen2.5-0.5B-Instruct"

# 确定设备
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 加载分词器和模型，并使用半精度和优化
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16, # 使用半精度
    device_map="auto", # 自动分配到可用设备
    trust_remote_code=True
).to(device).eval() # 切换到评估模式

@app.route('/')
def index():
    return render_template('index.html')

def generate_evaluation_response(phone_number):
    """生成手机号评估响应"""
    prompt = f"""你是一个专业的手机号码评估专家。
请根据以下手机号码，为其生成一个具体的评估价格、等级和建议。

**手机号码：** {phone_number}

请严格以JSON格式返回评估结果，包含以下字段，并且所有字段都必须有实际值，不能是示例或括号说明。确保估算的价格在3000元到10000元之间，不要添加任何额外的解释或说明：
{{
  "price": "一个具体的估算价格 (例如: 8888元)",
  "level": "一个明确的号码等级 (例如: 吉祥)",
  "suggestion": "一段详细具体的运势分析和建议"
}}
"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant that provides analysis in JSON format."},
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    generated_ids = model.generate(
        model_inputs.input_ids,
        max_new_tokens=512
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    response_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    print(f"模型原始返回文本: {response_text}") # 增加日志

    try:
        # 从Markdown代码块中提取JSON字符串
        json_str = response_text.split('```json')[1].split('```')[0].strip()
        response_json = json.loads(json_str)
        return response_json
    except (json.JSONDecodeError, IndexError):
        # 如果解析失败，返回一个错误提示或默认值
        return {"price": "N/A", "level": "N/A", "suggestion": "无法解析模型返回结果，请稍后重试。"}

@app.route('/evaluate', methods=['POST'])
def evaluate_number():
    data = request.get_json()
    if not data or 'number' not in data:
        return jsonify({'error': '请求参数错误，需要提供 number 字段'}), 400

    number = data['number']
    if not isinstance(number, str) or not number.isdigit() or len(number) != 4:
        return jsonify({'error': '号码必须是4位数字字符串'}), 400

    try:
        result = generate_evaluation_response(number)
        print(f"模型原始返回结果: {result}") # 添加日志记录
        return jsonify(result)
    except Exception as e:
        print(f"模型推理或解析出错: {e}")
        return jsonify({'error': '模型处理失败'}), 500

def get_zodiac(year, month, day):
    # 农历新年日期（公历），数据来源：https://www.prokerala.com/general/calendar/chinese-new-year.php
    # 扩展查找表以提高准确性，覆盖更广泛的年份范围
    lunar_new_year = {
        1930: (1, 30), 1931: (2, 17), 1932: (2, 6), 1933: (1, 26), 1934: (2, 14), 1935: (2, 4), 1936: (1, 24), 1937: (2, 11), 1938: (1, 31), 1939: (2, 19),
        1940: (2, 8), 1941: (1, 27), 1942: (2, 15), 1943: (2, 5), 1944: (1, 25), 1945: (2, 13), 1946: (2, 2), 1947: (1, 22), 1948: (2, 10), 1949: (1, 29),
        1950: (2, 17), 1951: (2, 6), 1952: (1, 27), 1953: (2, 14), 1954: (2, 3), 1955: (1, 24), 1956: (2, 12), 1957: (1, 31), 1958: (2, 18), 1959: (2, 8),
        1960: (1, 28), 1961: (2, 15), 1962: (2, 5), 1963: (1, 25), 1964: (2, 13), 1965: (2, 2), 1966: (1, 21), 1967: (2, 9), 1968: (1, 30), 1969: (2, 17),
        1970: (2, 6), 1971: (1, 27), 1972: (2, 15), 1973: (2, 3), 1974: (1, 23), 1975: (2, 11), 1976: (1, 31), 1977: (2, 18), 1978: (2, 7), 1979: (1, 28),
        1980: (2, 16), 1981: (2, 5), 1982: (1, 25), 1983: (2, 13), 1984: (2, 2), 1985: (2, 20), 1986: (2, 9), 1987: (1, 29), 1988: (2, 17), 1989: (2, 6),
        1990: (1, 27), 1991: (2, 15), 1992: (2, 4), 1993: (1, 23), 1994: (2, 10), 1995: (1, 31), 1996: (2, 19), 1997: (2, 7), 1998: (1, 28), 1999: (2, 16),
        2000: (2, 5), 2001: (1, 24), 2002: (2, 12), 2003: (2, 1), 2004: (1, 22), 2005: (2, 9), 2006: (1, 29), 2007: (2, 18), 2008: (2, 7), 2009: (1, 26),
        2010: (2, 14), 2011: (2, 3), 2012: (1, 23), 2013: (2, 10), 2014: (1, 31), 2015: (2, 19), 2016: (2, 8), 2017: (1, 28), 2018: (2, 16), 2019: (2, 5),
        2020: (1, 25), 2021: (2, 12), 2022: (2, 1), 2023: (1, 22), 2024: (2, 10), 2025: (1, 29), 2026: (2, 17), 2027: (2, 6), 2028: (1, 26), 2029: (2, 13),
        2030: (2, 3)
    }
    # 生肖列表，从鼠年开始
    zodiacs = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
    
    # 1900年是鼠年，作为计算基准
    start_year = 1900

    # 判断用户生日是否在当年农历新年之前
    if year in lunar_new_year and (month, day) < lunar_new_year[year]:
        year -= 1
        
    return zodiacs[(year - start_year) % 12]

def get_constellation(month, day):
    dates = (21, 20, 21, 21, 22, 22, 23, 24, 24, 24, 23, 22)
    constellations = ("水瓶座", "双鱼座", "白羊座", "金牛座", "双子座", "巨蟹座", "狮子座", "处女座", "天秤座", "天蝎座", "射手座", "摩羯座")
    if day < dates[month-1]:
        return constellations[month-2]
    else:
        return constellations[month-1]

def generate_fortune_response(birth_date):
    """生成生辰八字算命响应（流式）"""
    # 检查日期格式是否符合要求
    if not birth_date or not isinstance(birth_date, str) or len(birth_date.split('/')) != 3:
        def error_stream():
            yield "输入的日期格式不正确，请使用 YYYY/MM/DD 格式。"
        return error_stream()

    try:
        dt = datetime.strptime(birth_date, "%Y/%m/%d")
        year, month, day = dt.year, dt.month, dt.day
        # 检查日期是否有效
        if not (1900 <= year <= 2030):
            def error_stream():
                yield "请输入1900年到2030年之间的日期。"
            return error_stream()
        zodiac = get_zodiac(year, month, day)
        constellation = get_constellation(month, day)
    except ValueError:
        def error_stream():
            yield "输入的日期无效，请确保日期真实存在。"
        return error_stream()

    prompt = f"""你是一位专业的命理分析师。请严格按照我提供的信息进行分析，不要自行修改或重新计算生肖和星座。

**用户信息**
- **生肖**: {zodiac}
- **星座**: {constellation}

**任务要求**
1.  **性格分析**: 结合生肖“{zodiac}”和星座“{constellation}”的特点，提供一份详细的性格分析报告。
2.  **五行与运势**: 分析其五行属性，并总结其在事业、财运、健康和感情方面的运势。
3.  **开运建议**: 提供具体、可行的开运建议。

请以清晰的Markdown格式返回报告，确保内容专业、严谨。
"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]
    text = tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    def generate():
        with torch.no_grad():
            # 使用线程来运行模型生成，以避免阻塞请求
            from threading import Thread
            generation_kwargs = dict(
                **model_inputs,
                streamer=streamer,
                max_new_tokens=1024
            )
            thread = Thread(target=model.generate, kwargs=generation_kwargs)
            thread.start()

            # 从streamer中yield生成的文本
            # 这是一个简化的示例，实际应用中可能需要更复杂的队列机制
            # 这里我们直接从streamer的打印输出中获取文本，这并不理想但能工作
            # 一个更好的方法是自定义streamer以将文本放入队列
            # 但为了简单起见，我们暂时这样处理
            # 注意：TextStreamer默认将文本打印到stdout，我们需要一种方式来捕获它
            # 这里我们用一个更简单的流式方法

    # 为了实现真正的流式输出，我们需要修改generate函数
    # 下面是一个更合适的流式实现
    
    generation_kwargs = dict(
        **model_inputs,
        streamer=streamer,
        max_new_tokens=1024
    )

    # 在一个单独的线程中运行生成器，这样它就不会阻塞Flask的响应
    from threading import Thread
    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()

    # 这个函数将从streamer中yield token
    # 注意：这是一个简化的实现。在生产环境中，您可能需要一个队列来在线程之间安全地传递数据。
    def streamer_queue():
        # TextStreamer直接打印到控制台，所以我们不能直接从中yield。
        # 我们需要一个自定义的streamer来将token放入队列。
        from queue import Queue
        
        q = Queue()

        class QueueStreamer(TextStreamer):
            def __init__(self, tokenizer, queue, skip_prompt=True, **decode_kwargs):
                super().__init__(tokenizer, skip_prompt, **decode_kwargs)
                self.queue = queue

            def on_finalized_text(self, text: str, stream_end: bool = False):
                self.queue.put(text)
                if stream_end:
                    self.queue.put(None) # 发送信号表示结束

        # 在新线程中运行生成
        def run_generation():
            streamer = QueueStreamer(tokenizer, q, skip_prompt=True, skip_special_tokens=True)
            with torch.no_grad():
                model.generate(**model_inputs, streamer=streamer, max_new_tokens=1024)

        thread = Thread(target=run_generation)
        thread.start()

        # 从队列中yield token
        while True:
            token = q.get()
            if token is None:
                break
            yield token

    return streamer_queue()

@app.route('/fortune', methods=['POST'])
def get_fortune():
    data = request.get_json()
    if not data or 'birthdate' not in data:
        return jsonify({'error': '请求参数错误，需要提供 birthdate 字段'}), 400

    birthdate = data['birthdate']

    try:
        # 使用 stream_with_context 和 Response 来实现流式输出
        return Response(stream_with_context(generate_fortune_response(birthdate)), mimetype='text/event-stream')
    except Exception as e:
        print(f"模型推理或解析出错: {e}")
        return jsonify({'error': '模型处理失败'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)