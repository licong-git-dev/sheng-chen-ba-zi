function switchTab(tabName) {
    // Deactivate all tabs and buttons
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    // Activate the selected tab and button
    let targetContentId;
    switch(tabName) {
        case 'number': targetContentId = 'number-evaluation'; break;
        case 'fortune': targetContentId = 'fortune-telling'; break;
        case 'name': targetContentId = 'name-analysis'; break;
        case 'lucky': targetContentId = 'lucky-draw'; break;
        case 'ranking': targetContentId = 'ranking-board'; break;
        default: targetContentId = 'number-evaluation';
    }

    document.getElementById(targetContentId).classList.add('active');
    document.querySelector(`.tab-btn[onclick="switchTab('${tabName}')"]`).classList.add('active');

    // Initialize wheel if switching to lucky tab
    if (tabName === 'lucky') {
        setTimeout(initWheel, 100);
    }

    // Load rankings if switching to ranking tab
    if (tabName === 'ranking') {
        loadRankings();
    }
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

// 姓名分析功能
async function analyzeName() {
    const nameInput = document.getElementById('name');
    const name = nameInput.value.trim();
    const nameResultDiv = document.getElementById('name-result');
    const nameTextEl = document.getElementById('name-text');
    const analyzeBtn = document.querySelector('#name-analysis .evaluate-btn');

    if (!name || name.length < 2) {
        nameResultDiv.style.display = 'block';
        nameTextEl.innerHTML = '<span style="color: #e53935;">请输入有效的姓名（至少2个字符）</span>';
        return;
    }

    analyzeBtn.textContent = '解读中...';
    analyzeBtn.disabled = true;
    nameResultDiv.style.display = 'block';
    nameTextEl.innerHTML = '';

    try {
        const response = await fetch('/name_analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name }),
        });

        if (!response.ok) {
            throw new Error('姓名分析服务出错');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const typingSpeed = 25;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            for (const char of chunk) {
                if (char === '\n') {
                    nameTextEl.innerHTML += '<br>';
                } else {
                    nameTextEl.innerHTML += char;
                }
                await sleep(typingSpeed);
            }
        }

    } catch (error) {
        console.error('姓名分析出错:', error);
        nameTextEl.innerHTML = '<span style="color: #e53935;">服务暂时不可用，请稍后再试。</span>';
    } finally {
        analyzeBtn.textContent = '开始解读';
        analyzeBtn.disabled = false;
    }
}

// 幸运转盘功能
let wheelCanvas, wheelCtx;
let isSpinning = false;
const prizes = [
    { name: "超级幸运星", color: "#ff6b6b", probability: 5 },
    { name: "大吉大利", color: "#4ecdc4", probability: 10 },
    { name: "财运亨通", color: "#45b7d1", probability: 15 },
    { name: "事业有成", color: "#96ceb4", probability: 20 },
    { name: "平安喜乐", color: "#feca57", probability: 25 },
    { name: "好运连连", color: "#ff9ff3", probability: 25 }
];

function initWheel() {
    wheelCanvas = document.getElementById('wheelCanvas');
    if (!wheelCanvas) return;

    wheelCtx = wheelCanvas.getContext('2d');
    drawWheel();
}

function drawWheel() {
    if (!wheelCtx) return;

    const centerX = wheelCanvas.width / 2;
    const centerY = wheelCanvas.height / 2;
    const radius = 140;

    let startAngle = 0;

    prizes.forEach((prize, index) => {
        const sliceAngle = (2 * Math.PI * prize.probability) / 100;

        // 绘制扇形
        wheelCtx.beginPath();
        wheelCtx.moveTo(centerX, centerY);
        wheelCtx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
        wheelCtx.closePath();
        wheelCtx.fillStyle = prize.color;
        wheelCtx.fill();
        wheelCtx.strokeStyle = '#fff';
        wheelCtx.lineWidth = 2;
        wheelCtx.stroke();

        // 绘制文字
        wheelCtx.save();
        wheelCtx.translate(centerX, centerY);
        wheelCtx.rotate(startAngle + sliceAngle / 2);
        wheelCtx.textAlign = 'right';
        wheelCtx.fillStyle = '#fff';
        wheelCtx.font = 'bold 14px Arial';
        wheelCtx.shadowColor = 'rgba(0,0,0,0.5)';
        wheelCtx.shadowBlur = 2;
        wheelCtx.fillText(prize.name, radius - 20, 5);
        wheelCtx.restore();

        startAngle += sliceAngle;
    });
}

async function spinWheel() {
    if (isSpinning) return;

    const numberInput = document.getElementById('luckyNumber');
    const number = numberInput.value.trim();
    const spinBtn = document.getElementById('spinBtn');
    const luckyResultDiv = document.getElementById('lucky-result');

    if (!number || number.length !== 4 || !/^\d+$/.test(number)) {
        alert('请输入有效的4位数字！');
        return;
    }

    isSpinning = true;
    spinBtn.disabled = true;
    spinBtn.textContent = '转动中...';
    luckyResultDiv.style.display = 'none';

    try {
        const response = await fetch('/lucky_draw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ number: number }),
        });

        if (!response.ok) {
            throw new Error('转盘服务出错');
        }

        const result = await response.json();

        // 转盘动画
        wheelCanvas.classList.add('spinning');

        setTimeout(() => {
            wheelCanvas.classList.remove('spinning');
            showPrizeResult(result);
        }, 3000);

    } catch (error) {
        console.error('转盘出错:', error);
        alert('服务暂时不可用，请稍后再试。');
    } finally {
        setTimeout(() => {
            isSpinning = false;
            spinBtn.disabled = false;
            spinBtn.textContent = '开始转动';
        }, 3000);
    }
}

function showPrizeResult(result) {
    const prizeIcon = document.getElementById('prizeIcon');
    const prizeName = document.getElementById('prizeName');
    const prizeMessage = document.getElementById('prizeMessage');
    const luckyResultDiv = document.getElementById('lucky-result');

    // 根据奖项设置图标
    const icons = {
        "超级幸运星": "⭐",
        "大吉大利": "🍀",
        "财运亨通": "💰",
        "事业有成": "🏆",
        "平安喜乐": "😊",
        "好运连连": "🎉"
    };

    prizeIcon.textContent = icons[result.prize] || "🎁";
    prizeName.textContent = result.prize;
    prizeMessage.textContent = result.message;
    luckyResultDiv.style.display = 'block';

    // 添加庆祝效果
    setTimeout(() => {
        createConfetti();
    }, 100);
}

function createConfetti() {
    // 简单的庆祝效果
    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            const confetti = document.createElement('div');
            confetti.innerHTML = ['🎉', '✨', '🎊', '⭐'][Math.floor(Math.random() * 4)];
            confetti.style.position = 'fixed';
            confetti.style.left = Math.random() * window.innerWidth + 'px';
            confetti.style.top = '-20px';
            confetti.style.zIndex = '9999';
            confetti.style.fontSize = '20px';
            confetti.style.pointerEvents = 'none';
            document.body.appendChild(confetti);

            const duration = 3000;
            confetti.animate([
                { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
                { transform: `translateY(${window.innerHeight + 100}px) rotate(720deg)`, opacity: 0 }
            ], {
                duration: duration,
                easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
            });

            setTimeout(() => {
                confetti.remove();
            }, duration);
        }, i * 100);
    }
}

// 数字输入限制
document.getElementById('luckyNumber').addEventListener('input', function(e) {
    this.value = this.value.replace(/\D/g, '').slice(0, 4);
});

// 分享卡片功能
let currentShareImage = null;

async function generateShareCard(type) {
    let content = {};

    // 根据类型收集内容
    if (type === 'number') {
        const number = document.getElementById('number').value;
        const price = document.getElementById('price').textContent.replace('¥ ', '');
        const level = document.getElementById('level').textContent;
        content = { number, price, level };
    } else if (type === 'lucky') {
        const prize = document.getElementById('prizeName').textContent;
        const score = lastLuckyScore || 50; // 保存最后一次的幸运值
        content = { prize, score };
    }

    if (!content.number && !content.prize) {
        alert('请先进行相应的测算！');
        return;
    }

    try {
        const response = await fetch('/generate_share_card', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, content }),
        });

        if (!response.ok) {
            throw new Error('生成分享卡片失败');
        }

        const result = await response.json();
        currentShareImage = result.image;

        // 显示分享卡片
        document.getElementById('shareCardImage').src = result.image;
        document.getElementById('shareModal').style.display = 'flex';

    } catch (error) {
        console.error('生成分享卡片出错:', error);
        alert('生成分享卡片失败，请稍后再试！');
    }
}

function closeShareModal() {
    document.getElementById('shareModal').style.display = 'none';
}

function downloadShareCard() {
    if (!currentShareImage) return;

    const link = document.createElement('a');
    link.href = currentShareImage;
    link.download = `红姐数字能量站-分享卡片-${Date.now()}.png`;
    link.click();
}

async function copyShareCard() {
    if (!currentShareImage) return;

    try {
        // 将base64转换为Blob
        const response = await fetch(currentShareImage);
        const blob = await response.blob();

        await navigator.clipboard.write([
            new ClipboardItem({ 'image/png': blob })
        ]);

        alert('图片已复制到剪贴板！');
    } catch (error) {
        console.error('复制失败:', error);
        alert('复制失败，请尝试直接保存图片');
    }
}

// 保存幸运值供分享使用
let lastLuckyScore = 50;

// 修改showPrizeResult函数以保存幸运值
const originalShowPrizeResult = showPrizeResult;
function showPrizeResult(result) {
    lastLuckyScore = result.score;
    originalShowPrizeResult(result);
}

// 点击模态框外部关闭
document.addEventListener('click', function(event) {
    const modal = document.getElementById('shareModal');
    if (event.target === modal) {
        closeShareModal();
    }
});

// 音效管理
const SoundManager = {
    sounds: {},
    enabled: true,

    // 使用Web Audio API生成音效
    generateTone(frequency, duration, type = 'sine') {
        if (!this.enabled) return;

        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
        oscillator.type = type;

        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + duration);
    },

    // 播放按钮点击音效
    playClick() {
        this.generateTone(800, 0.1);
    },

    // 播放成功音效
    playSuccess() {
        this.generateTone(523.25, 0.2); // C5
        setTimeout(() => this.generateTone(659.25, 0.2), 100); // E5
        setTimeout(() => this.generateTone(783.99, 0.3), 200); // G5
    },

    // 播放转盘音效
    playSpin() {
        for (let i = 0; i < 20; i++) {
            setTimeout(() => {
                this.generateTone(200 + i * 50, 0.05);
            }, i * 150);
        }
    },

    // 播放打字音效
    playType() {
        this.generateTone(1000, 0.03);
    },

    toggle() {
        this.enabled = !this.enabled;
        return this.enabled;
    }
};

// 添加音效控制按钮
function addSoundToggle() {
    const container = document.querySelector('.container');
    const soundToggle = document.createElement('button');
    soundToggle.className = 'sound-toggle';
    soundToggle.innerHTML = '🔊';
    soundToggle.title = '音效开关';
    soundToggle.onclick = () => {
        const enabled = SoundManager.toggle();
        soundToggle.innerHTML = enabled ? '🔊' : '🔇';
        SoundManager.playClick();
    };
    container.appendChild(soundToggle);
}

// 为按钮添加音效
function addButtonSounds() {
    document.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!btn.classList.contains('sound-toggle')) {
                SoundManager.playClick();
            }
        });
    });
}

// 增强的动画效果
function addEnhancedAnimations() {
    // 为结果容器添加展开动画
    const style = document.createElement('style');
    style.textContent = `
        .result.show {
            animation: slideInUp 0.6s ease-out;
        }

        @keyframes slideInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .loading-dots::after {
            content: '';
            animation: dots 1.5s infinite;
        }

        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }

        .shake {
            animation: shake 0.5s ease-in-out;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            75% { transform: translateX(5px); }
        }

        .pulse {
            animation: pulse 0.6s ease-in-out;
        }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }

        .float {
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .glow {
            animation: glow 2s ease-in-out infinite alternate;
        }

        @keyframes glow {
            from { box-shadow: 0 0 5px currentColor; }
            to { box-shadow: 0 0 20px currentColor, 0 0 30px currentColor; }
        }
    `;
    document.head.appendChild(style);

    // 为标题添加浮动效果
    const title = document.querySelector('.title');
    if (title) title.classList.add('float');
}

// 修改现有函数添加音效支持
const originalEvaluateNumber = evaluateNumber;
async function evaluateNumber() {
    const result = document.getElementById('result');
    const btn = document.querySelector('#number-evaluation .evaluate-btn');

    // 添加加载动画
    btn.classList.add('loading-dots');

    await originalEvaluateNumber();

    // 移除加载动画，添加展开动画
    btn.classList.remove('loading-dots');
    if (result.style.display !== 'none') {
        result.classList.add('show');
        SoundManager.playSuccess();
    }
}

const originalSpinWheel = spinWheel;
async function spinWheel() {
    SoundManager.playSpin();
    await originalSpinWheel();
}

const originalAnalyzeName = analyzeName;
async function analyzeName() {
    const result = document.getElementById('name-result');
    await originalAnalyzeName();
    if (result.style.display !== 'none') {
        result.classList.add('show');
        SoundManager.playSuccess();
    }
}

// 为打字效果添加音效
function addTypingSound() {
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' || mutation.type === 'characterData') {
                // 随机播放打字音效（降低频率避免太吵）
                if (Math.random() < 0.1) {
                    SoundManager.playType();
                }
            }
        });
    });

    // 观察结果文本的变化
    const fortuneText = document.getElementById('fortune-text');
    const nameText = document.getElementById('name-text');

    if (fortuneText) observer.observe(fortuneText, { childList: true, subtree: true, characterData: true });
    if (nameText) observer.observe(nameText, { childList: true, subtree: true, characterData: true });
}

// Initialize first tab
document.addEventListener('DOMContentLoaded', () => {
    const initialTab = 'number';
    switchTab(initialTab);

    // 初始化音效和动画
    addSoundToggle();
    addButtonSounds();
    addEnhancedAnimations();
    addTypingSound();

    // 添加页面加载动画
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease-in-out';
        document.body.style.opacity = '1';
    }, 100);
});

// 排行榜功能
let rankingsData = { top_numbers: [], recent_evaluations: [] };

function switchRankingTab(tabName) {
    // 切换排行榜标签
    document.querySelectorAll('.ranking-tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.ranking-content').forEach(c => c.classList.remove('active'));

    if (tabName === 'top') {
        document.querySelector(`.ranking-tab-btn[onclick="switchRankingTab('top')"]`).classList.add('active');
        document.getElementById('top-ranking').classList.add('active');
        renderTopRanking();
    } else {
        document.querySelector(`.ranking-tab-btn[onclick="switchRankingTab('recent')"]`).classList.add('active');
        document.getElementById('recent-ranking').classList.add('active');
        renderRecentRanking();
    }
}

async function loadRankings() {
    try {
        const response = await fetch('/rankings');
        if (response.ok) {
            rankingsData = await response.json();
            renderTopRanking();
        }
    } catch (error) {
        console.error('加载排行榜失败:', error);
    }
}

function renderTopRanking() {
    const container = document.getElementById('topRankingList');
    const topNumbers = rankingsData.top_numbers;

    if (!topNumbers || topNumbers.length === 0) {
        container.innerHTML = '<div class="no-data">暂无排行数据</div>';
        return;
    }

    const html = topNumbers.map((item, index) => {
        const rank = index + 1;
        let rankClass;
        if (rank === 1) rankClass = 'top1';
        else if (rank === 2) rankClass = 'top2';
        else if (rank === 3) rankClass = 'top3';
        else rankClass = 'other';

        const medal = rank <= 3 ? ['🥇', '🥈', '🥉'][rank - 1] : '';

        return `
            <div class="ranking-item">
                <div class="ranking-position">
                    <div class="rank-number ${rankClass}">${rank}</div>
                    <span style="font-size: 18px;">${medal}</span>
                </div>
                <div class="ranking-info">
                    <div class="ranking-number">****${item.number}</div>
                    <div class="ranking-details">
                        <span class="ranking-price">¥${item.price}</span>
                        <span class="ranking-level">${item.level}</span>
                        <span class="ranking-time">${item.timestamp}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = html;
}

function renderRecentRanking() {
    const container = document.getElementById('recentRankingList');
    const recentEvaluations = rankingsData.recent_evaluations;

    if (!recentEvaluations || recentEvaluations.length === 0) {
        container.innerHTML = '<div class="no-data">暂无最近评估</div>';
        return;
    }

    const html = recentEvaluations.reverse().map((item, index) => `
        <div class="ranking-item">
            <div class="ranking-position">
                <div class="rank-number other">${index + 1}</div>
                <span>🔮</span>
            </div>
            <div class="ranking-info">
                <div class="ranking-number">****${item.number}</div>
                <div class="ranking-details">
                    <span class="ranking-price">¥${item.price}</span>
                    <span class="ranking-level">${item.level}</span>
                    <span class="ranking-time">${item.timestamp}</span>
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

// 修改评估函数以添加到排行榜
async function addToRanking(number, price, level) {
    try {
        await fetch('/add_to_ranking', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ number, price, level }),
        });
    } catch (error) {
        console.error('添加到排行榜失败:', error);
    }
}

// 修改 evaluateNumber 函数
const originalEvaluateNumberWithRanking = evaluateNumber;
async function evaluateNumber() {
    await originalEvaluateNumberWithRanking();

    // 如果评估成功，添加到排行榜
    const resultDiv = document.getElementById('result');
    if (resultDiv.style.display !== 'none') {
        const number = document.getElementById('number').value;
        const price = document.getElementById('price').textContent.replace('¥ ', '');
        const level = document.getElementById('level').textContent;

        await addToRanking(number, price, level);
    }
};