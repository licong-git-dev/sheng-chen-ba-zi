import os
import dashscope
from flask import Flask, request, render_template, Response, stream_with_context
from http import HTTPStatus

app = Flask(__name__)

# --- 安全地从环境变量获取API Key ---
# 在Vercel部署时，我们会把API Key设置为环境变量，这样更安全
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY", "sk-5a09c47c15614ebd95b6e7bff8ae6979")

@app.route('/')
def index():
    return render_template('index.html')

def generate_stream(prompt):
    """一个通用的流式生成器函数"""
    try:
        responses = dashscope.Generation.call(
            model='qwen-turbo', # 使用速度最快的qwen-turbo模型
            prompt=prompt,
            stream=True, # 开启流式输出
            result_format='text' # 设置结果格式为纯文本
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

@app.route('/evaluate_number', methods=['POST'])
def evaluate_number():
    phone_number = request.form.get('phone_number')
    if not phone_number:
        return Response("请输入手机号码", status=400)

    prompt = f"""
你是一位精通东西方数字神秘学、命理学和中华传统文化的趣味解读大师。
请你从多个角度，用风趣幽默、积极向上的风格，为我分析一下手机号码：{phone_number}。

请围绕以下几点展开，但不要局限于此：
1.  **数字谐音**：比如8代表发，4代表“四季发财”等，尽量从好的寓意解读。
2.  **易经卦象**（如果能结合的话）：简单提一下这个号码可能关联的卦象和它积极的寓意。
3.  **能量磁场**：结合数字能量学的概念，比如天医、延年、生气等，说说这个号码的正向能量。
4.  **整体评价**：给出一个综合性的、令人愉快的总结。

**要求**：
- 全程使用简体中文。
- 风格要像一个网络上的趣味测试，轻松、好玩，多用积极正面的词语。
- 内容要原创，每次生成都要不一样。
- 总字数在200-300字之间。
- 直接开始分析，不要说“好的”、“当然”等多余的话。
"""
    return Response(stream_with_context(generate_stream(prompt)), content_type='text/plain')

@app.route('/fortune_telling', methods=['POST'])
def fortune_telling():
    birth_date = request.form.get('birth_date')
    if not birth_date:
        return Response("请输入出生日期", status=400)

    prompt = f"""
你是一位现代的、积极心理学导向的命理解读师，同时也是一个温暖、善于鼓励的人生导师。
请根据我提供的公历生日：{birth_date}，为我生成一份专属的“人生能量”解读报告。

请围绕以下几个方面，用现代、科学、易于理解的语言进行分析：
1.  **核心性格特质**：根据星座、生命数字等（你可以虚构一个听起来科学的体系），分析这个人与生俱来的性格优点和潜力。
2.  **事业能量导向**：分析此人适合在哪些领域发光发热，更容易获得成就感和满足感。
3.  **人际关系能量**：分析此人在与人交往中的特点和优势。
4.  **人生幸运提示**：提供一些积极的、可操作的心理学建议，作为Ta的“幸运锦囊”，帮助Ta更好地发挥天赋，吸引好运。

**要求**：
- 全程使用简体中文。
- 风格要非常积极、温暖、治愈，多用鼓励性和启发性的语言，像一个专业的心理咨询师在做积极引导。
- 避免使用任何宿命论、迷信、负面的词汇（如“劫难”、“克夫”等），将一切都解释为“挑战”与“成长的机会”。
- 内容要原创，每次生成都要不一样。
- 总字数在300-400字之间。
- 直接开始解读，不要有任何多余的开场白。
"""
    return Response(stream_with_context(generate_stream(prompt)), content_type='text/plain')

if __name__ == '__main__':
    # 注意：在Vercel上部署时，它会使用自己的方式来运行app，不会执行下面的代码
    app.run(debug=True)