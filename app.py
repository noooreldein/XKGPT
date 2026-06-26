import os, json, secrets, time, re
from flask import Flask, request, jsonify, Response, stream_with_context, render_template_string
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ========== إعدادات ==========
SERVICES = {
    "chat": {
        "wormgpt": {
            "name": "WormGPT",
            "url": "https://wormgpt2-u2rn.vercel.app/chat",
            "method": "GET",
            "params": {"q": "{text}"},
            "response_key": "reply"
        },
        "gpt5nano": {
            "name": "GPT-5 Nano",
            "url": "https://gpt5nano.vercel.app/chat",
            "method": "GET",
            "params": {"text": "{text}"},
            "response_key": "reply"
        },
        "deepseek": {
            "name": "DeepSeek",
            "url": "https://deepseek-nor.vercel.app/deepseek",
            "method": "GET",
            "params": {"text": "{text}", "uid": "{uid}"},
            "response_key": "reply"
        },
        "gemini": {
            "name": "Gemini 2.5 Flash",
            "url": "https://gemini-nor.vercel.app/gemini",
            "method": "GET",
            "params": {"text": "{text}"},
            "response_key": "reply"
        },
        "chatgpt": {
            "name": "ChatGPT الرسمي",
            "url": "http://93.115.101.109:12131/chat",
            "method": "GET",
            "params": {"text": "{text}", "model": "gpt-4o"},
            "response_key": "reply"
        },
        "deeppro": {
            "name": "DeepSeek Pro",
            "url": "https://deepseek-norpro.vercel.app/deeppro",
            "method": "POST",
            "params": {"model": "1", "message": "{text}"},
            "response_key": "response"
        },
        "blackbox": {
            "name": "Blackbox AI",
            "url": "https://black-box-by-nour-w7nv.vercel.app/chat",
            "method": "GET",
            "params": {"q": "{text}"},
            "response_key": "reply"
        },
        "k_gemini": {
            "name": "KILWA Gemini",
            "url": "http://de3.bot-hosting.net:21007/kilwa-chat",
            "method": "GET",
            "params": {"text": "{text}"},
            "response_key": "reply"
        },
        "k_gpt5nano": {
            "name": "KILWA GPT-5 Nano",
            "url": "http://de3.bot-hosting.net:21007/kilwa-chatgpt",
            "method": "GET",
            "params": {"text": "{text}"},
            "response_key": "reply"
        },
        "deepseek_free": {
            "name": "DeepSeek Free",
            "url": "https://deep-seek-inmn.vercel.app/chat",
            "method": "GET",
            "params": {"q": "{text}"},
            "response_key": "reply"
        },
        "multimodel": {
            "name": "Multi-Model (GPT, Grok, Gemini)",
            "url": "https://full-stack-api-seven.vercel.app/v1/chat/completions",
            "method": "POST",
            "params": {"message": "{text}", "model_choice": "1"},
            "response_key": "choices[0].Message.content"
        }
    }
}

OWNER = "@Blak_man_one"
CHANNEL = "https://t.me/R4_QX"
DEVELOPER = "the black man"

# ========== دوال مساعدة ==========
def get_nested_value(data, key_path):
    keys = key_path.replace('[', '.').replace(']', '').split('.')
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        elif isinstance(val, list) and k.isdigit():
            val = val[int(k)]
        else:
            return None
    return val

def call_service(service, text, uid=None):
    cfg = SERVICES.get(service["category"], {}).get(service["model"])
    if not cfg:
        return None, "Service not found"
    url = cfg["url"]
    method = cfg["method"]
    params = {}
    for k, v in cfg["params"].items():
        if v == "{text}":
            params[k] = text
        elif v == "{uid}":
            params[k] = uid or "default"
        else:
            params[k] = v

    try:
        if method == "GET":
            resp = requests.get(url, params=params, timeout=30)
        else:
            resp = requests.post(url, data=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if cfg["response_key"]:
            result = get_nested_value(data, cfg["response_key"])
            return result, None
        return data, None
    except Exception as e:
        return None, str(e)

# ========== واجهة المستخدم (شات بسيط مع دعم Markdown) ==========
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Noor AI Chat</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family: system-ui, sans-serif; background: #0c0d14; color: #fff; height:100vh; display:flex; }
    .sidebar { width:260px; background: #1a1b24; padding:20px; display:flex; flex-direction:column; border-left:1px solid #2a2c3a; }
    .sidebar h2 { font-size:20px; color:#c084fc; margin-bottom:20px; }
    .sidebar select { width:100%; padding:10px; border-radius:8px; background:#0f1017; color:#fff; border:1px solid #333; margin-bottom:10px; }
    .main { flex:1; display:flex; flex-direction:column; }
    .chat-area { flex:1; overflow-y:auto; padding:20px; display:flex; flex-direction:column; gap:12px; }
    .message { max-width:80%; padding:12px 16px; border-radius:16px; line-height:1.5; }
    .user { align-self:flex-end; background: #1e3a5f; }
    .bot { align-self:flex-start; background: #1a1b24; border:1px solid #2a2c3a; }
    .typing { display:inline-block; width:8px; height:8px; background:#888; border-radius:50%; margin:0 2px; animation: blink 1.2s infinite; }
    .typing:nth-child(2){ animation-delay:0.2s; } .typing:nth-child(3){ animation-delay:0.4s; }
    @keyframes blink { 0%,60%,100%{opacity:0.3; transform:scale(0.9)} 30%{opacity:1;transform:scale(1.1)} }
    .input-area { padding:16px; border-top:1px solid #2a2c3a; display:flex; gap:10px; background:#111217; }
    .input-area input { flex:1; padding:12px 16px; border-radius:24px; background:#0f0f0f; border:1px solid #333; color:#fff; }
    .input-area button { padding:12px 20px; border-radius:24px; background:#a855f7; border:none; color:#fff; cursor:pointer; }
    @media (max-width:768px) { .sidebar { display:none; } }
    .bot a { color:#a78bfa; text-decoration:underline; }
    .bot strong { color:#e2b6c2; }
    .bot em { color:#b9c3db; }
    .bot pre { background:#0f1017; padding:10px; border-radius:8px; overflow-x:auto; }
    .bot code { font-family:monospace; background:#0f1017; padding:2px 4px; border-radius:4px; }
  </style>
</head>
<body>
  <div class="sidebar">
    <h2>Noor AI Chat</h2>
    <select id="modelSelect"></select>
    <div style="margin-top:auto; font-size:12px; color:#666;">{{ owner }}</div>
  </div>
  <div class="main">
    <div class="chat-area" id="chatArea"></div>
    <div class="input-area">
      <input type="text" id="userInput" placeholder="اكتب رسالتك..." onkeypress="if(event.key==='Enter') sendMessage()">
      <button onclick="sendMessage()">إرسال</button>
    </div>
  </div>

  <script>
    const chatArea = document.getElementById('chatArea');
    const userInput = document.getElementById('userInput');
    const modelSelect = document.getElementById('modelSelect');

    // تحميل النماذج
    fetch('/v1/models')
      .then(r => r.json())
      .then(data => {
        const models = data.models;
        Object.keys(models).forEach(key => {
          if (key.startsWith('chat/')) {
            const option = document.createElement('option');
            option.value = key.replace('chat/', '');
            option.textContent = models[key].name;
            modelSelect.appendChild(option);
          }
        });
      });

    // دالة تحويل Markdown خفيف إلى HTML
    function formatMarkdown(text) {
      if (!text) return '';
      // استبدال الروابط [النص](الرابط)
      let html = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
      // استبدال **نص** بـ <strong>
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      // استبدال *نص* بـ <em> (لكن لا نستبدل داخل الوسوم)
      html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');
      // استبدال \n و \n بـ <br>
      html = html.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
      return html;
    }

    function addMessage(text, role) {
      const div = document.createElement('div');
      div.className = 'message ' + (role === 'user' ? 'user' : 'bot');
      if (role === 'bot') {
        div.innerHTML = formatMarkdown(text);
      } else {
        div.textContent = text;
      }
      chatArea.appendChild(div);
      chatArea.scrollTop = chatArea.scrollHeight;
      return div;
    }

    function showTyping() {
      const div = document.createElement('div');
      div.className = 'message bot';
      div.id = 'typingIndicator';
      div.innerHTML = '<span class="typing"></span><span class="typing"></span><span class="typing"></span>';
      chatArea.appendChild(div);
      chatArea.scrollTop = chatArea.scrollHeight;
    }

    function removeTyping() {
      const el = document.getElementById('typingIndicator');
      if (el) el.remove();
    }

    async function sendMessage() {
      const text = userInput.value.trim();
      if (!text) return;
      addMessage(text, 'user');
      userInput.value = '';
      showTyping();

      const model = modelSelect.value || 'wormgpt';

      try {
        const response = await fetch('/v1/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: model,
            messages: [{ role: 'user', content: text }],
            stream: true
          })
        });

        removeTyping();

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let botDiv = addMessage('', 'bot');
        let fullText = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') break;
              try {
                const json = JSON.parse(data);
                if (json.choices && json.choices[0].delta) {
                  const content = json.choices[0].delta.content || '';
                  fullText += content;
                  botDiv.innerHTML = formatMarkdown(fullText);
                  chatArea.scrollTop = chatArea.scrollHeight;
                }
              } catch(e) {}
            }
          }
        }
      } catch(e) {
        removeTyping();
        addMessage('⚠️ حدث خطأ: ' + e.message, 'bot');
      }
    }
  </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, owner=OWNER)

# ========== API endpoints ==========
@app.route('/v1/models')
def list_models():
    all_models = {}
    for category, models in SERVICES.items():
        for key, cfg in models.items():
            all_models[f"{category}/{key}"] = {
                "name": cfg["name"],
                "category": category,
                "method": cfg["method"],
                "url": cfg["url"]
            }
    return jsonify({"models": all_models})

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    model = data.get('model', 'wormgpt')
    messages = data.get('messages', [])
    stream = data.get('stream', False)

    # استخراج آخر رسالة user
    text = ''
    for msg in reversed(messages):
        if msg.get('role') == 'user':
            text = msg.get('content', '')
            break
    if not text:
        return jsonify({"error": "No user message found"}), 400

    result, error = call_service({"category": "chat", "model": model}, text)
    if error:
        return jsonify({"error": error}), 500

    if not stream:
        return jsonify({
            "id": "chatcmpl-" + secrets.token_hex(12),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": result},
                "finish_reason": "stop"
            }],
            "owner": OWNER,
            "channel": CHANNEL,
            "developer": DEVELOPER
        })
    else:
        def generate():
            words = re.split(r'(\s+)', result)
            for word in words:
                chunk = {
                    "id": "chatcmpl-" + secrets.token_hex(12),
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {"content": word}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
                time.sleep(0.02)
            yield "data: [DONE]\n\n"
        return Response(stream_with_context(generate()), mimetype='text/event-stream')

# ========== تشغيل ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
