function switchTab(tabName) {
    // Deactivate all tabs and buttons
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    // Activate the selected tab and button
    const targetContentId = tabName === 'number' ? 'number-evaluation' : 'fortune-telling';
    document.getElementById(targetContentId).classList.add('active');
    document.querySelector(`.tab-btn[onclick="switchTab('${tabName}')"]`).classList.add('active');
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function evaluateNumber() {
    const numberInput = document.getElementById('number');
    const number = numberInput.value;
    const resultDiv = document.getElementById('result');
    const priceEl = document.getElementById('price');
    const levelEl = document.getElementById('level');
    const suggestionEl = document.getElementById('suggestion');
    const evaluateBtn = document.querySelector('#number-evaluation .evaluate-btn');

    // Clear previous results and errors
    suggestionEl.style.color = '';
    priceEl.textContent = '-';
    levelEl.textContent = '-';
    suggestionEl.textContent = '-';

    if (!number || number.length !== 4 || !/^\d+$/.test(number)) {
        resultDiv.style.display = 'block';
        suggestionEl.textContent = '请输入有效的4位数字手机尾号。';
        suggestionEl.style.color = '#e53935'; // A shade of red
        return;
    }

    evaluateBtn.textContent = '评估中...';
    evaluateBtn.disabled = true;
    resultDiv.style.display = 'none';

    try {
        const response = await fetch('/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ number: number }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '评估失败');
        }

        const result = await response.json();

        priceEl.textContent = `¥ ${result.price}`;
        levelEl.textContent = result.level;
        suggestionEl.textContent = result.suggestion;
        resultDiv.style.display = 'block';

    } catch (error) {
        console.error('评估出错:', error);
        resultDiv.style.display = 'block';
        suggestionEl.textContent = '评估服务暂时不可用，请稍后再试。';
        suggestionEl.style.color = '#e53935';
    } finally {
        evaluateBtn.textContent = '立即评估';
        evaluateBtn.disabled = false;
    }
}

document.getElementById('number').addEventListener('input', function(e) {
    this.value = this.value.replace(/\D/g, '').slice(0, 4);
});

async function getFortune() {
    const birthdateInput = document.getElementById('birthdate');
    const birthdate = birthdateInput.value;
    const fortuneResultDiv = document.getElementById('fortune-result');
    const fortuneTextEl = document.getElementById('fortune-text');
    const fortuneBtn = document.querySelector('#fortune-telling .evaluate-btn');

    if (!birthdate) {
        fortuneResultDiv.style.display = 'block';
        fortuneTextEl.innerHTML = '<span style="color: #e53935;">请先选择您的出生年月日。</span>';
        return;
    }

    fortuneBtn.textContent = '算命中...';
    fortuneBtn.disabled = true;
    fortuneResultDiv.style.display = 'block';
    fortuneTextEl.innerHTML = ''; // Clear previous results

    try {
        const response = await fetch('/fortune', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ birthdate: birthdate }),
        });

        if (!response.ok) {
            throw new Error('算命服务出错');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const typingSpeed = 20; // Adjusted speed for better readability

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            for (const char of chunk) {
                if (char === '\n') {
                    fortuneTextEl.innerHTML += '<br>';
                } else {
                    fortuneTextEl.innerHTML += char;
                }
                await sleep(typingSpeed);
            }
        }

    } catch (error) {
        console.error('算命出错:', error);
        fortuneTextEl.innerHTML = '<span style="color: #e53935;">服务暂时迷失在星辰中，请稍后再试。</span>';
    } finally {
        fortuneBtn.textContent = '开始算命';
        fortuneBtn.disabled = false;
    }
}

// Initialize first tab
document.addEventListener('DOMContentLoaded', () => {
    const initialTab = 'number';
    document.getElementById(initialTab === 'number' ? 'number-evaluation' : 'fortune-telling').classList.add('active');
    document.querySelector(`.tab-btn[onclick="switchTab('${initialTab}')"]`).classList.add('active');
});
