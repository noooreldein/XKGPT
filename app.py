import os, json, secrets, time, re, traceback
from flask import Flask, request, jsonify, Response, stream_with_context, render_template_string
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ========== تهيئة الأمان ==========
@app.after_request
def add_security_headers(response):
    response.headers['X-Powered-By'] = 'KX Team'
    response.headers['X-Developer'] = 'KX Team'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# ========== إعدادات الخدمات ==========
SERVICES = {
    "chat": {
        "wormgpt": {
            "name": "WormGPT",
            "url": "https://wormgpt2-u2rn.vercel.app/chat",
            "method": "GET",
            "params": {"q": "{text}"},
            "headers": {},
            "response_key": "reply"
        },
        "gpt5nano": {
            "name": "GPT-5 Nano",
            "url": "https://gpt5nano.vercel.app/chat",
            "method": "GET",
            "params": {"text": "{text}"},
            "headers": {},
            "response_key": "reply"
        },
        "deepseek": {
            "name": "DeepSeek",
            "url": "https://deepseek-nor.vercel.app/deepseek",
            "method": "GET",
            "params": {"text": "{text}", "uid": "{uid}"},
            "headers": {},
            "response_key": "reply"
        },
        "gemini": {
            "name": "Gemini 2.5 Flash",
            "url": "https://gemini-nor.vercel.app/gemini",
            "method": "GET",
            "params": {"text": "{text}"},
            "headers": {},
            "response_key": "reply"
        },
        "chatgpt": {
            "name": "ChatGPT GPT-4o",
            "url": "http://93.115.101.109:12131/chat",
            "method": "GET",
            "params": {"text": "{text}", "model": "gpt-4o"},
            "headers": {},
            "response_key": "reply"
        },
        "deeppro": {
            "name": "DeepSeek Pro",
            "url": "https://deepseek-norpro.vercel.app/deeppro",
            "method": "POST",
            "params": {"model": "1", "message": "{text}"},
            "headers": {},
            "response_key": "response"
        },
        "blackbox": {
            "name": "Blackbox AI",
            "url": "https://black-box-by-nour-w7nv.vercel.app/chat",
            "method": "GET",
            "params": {"q": "{text}"},
            "headers": {},
            "response_key": "reply"
        },
        "k_gemini": {
            "name": "KILWA Gemini",
            "url": "http://de3.bot-hosting.net:21007/kilwa-chat",
            "method": "GET",
            "params": {"text": "{text}"},
            "headers": {},
            "response_key": "reply"
        },
        "k_gpt5nano": {
            "name": "KILWA GPT-5 Nano",
            "url": "http://de3.bot-hosting.net:21007/kilwa-chatgpt",
            "method": "GET",
            "params": {"text": "{text}"},
            "headers": {},
            "response_key": "reply"
        },
        "deepseek_free": {
            "name": "DeepSeek Free",
            "url": "https://deep-seek-inmn.vercel.app/chat",
            "method": "GET",
            "params": {"q": "{text}"},
            "headers": {},
            "response_key": "reply"
        },
        "multimodel": {
            "name": "Multi-Model (GPT, Grok, Gemini)",
            "url": "https://full-stack-api-seven.vercel.app/v1/chat/completions",
            "method": "POST",
            "params": {"message": "{text}", "model_choice": "1"},
            "headers": {},
            "response_key": "choices[0].Message.content"
        }
    },
    "image": {
        "stable_diffusion": {
            "name": "Stable Diffusion XL",
            "url": "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0",
            "method": "POST",
            "params": {"inputs": "{text}"},
            "headers": {"Authorization": "Bearer hf_dummy_key_placeholder"},
            "response_key": None,
            "response_type": "binary"
        },
        "flux_schnell": {
            "name": "Flux Schnell",
            "url": "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
            "method": "POST",
            "params": {"inputs": "{text}"},
            "headers": {"Authorization": "Bearer hf_dummy_key_placeholder"},
            "response_key": None,
            "response_type": "binary"
        },
        "sd_turbo": {
            "name": "SD Turbo",
            "url": "https://api-inference.huggingface.co/models/stabilityai/sd-turbo",
            "method": "POST",
            "params": {"inputs": "{text}"},
            "headers": {"Authorization": "Bearer hf_dummy_key_placeholder"},
            "response_key": None,
            "response_type": "binary"
        }
    }
}

OWNER = "KX Team"
CHANNEL = "https://t.me/KX_Team"
DEVELOPER = "KX Team"
POWERED_BY = "KX"
PLATFORM_NAME = "KX AI Platform"
LOGO_URL = "https://files.catbox.moe/qvd2o2.png"

# ========== دوال مساعدة ==========
def get_nested_value(data, key_path):
    """استخراج قيمة متداخلة من JSON باستخدام مسار المفتاح."""
    if key_path is None:
        return data
    keys = key_path.replace('[', '.').replace(']', '').split('.')
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        elif isinstance(val, list) and k.isdigit():
            idx = int(k)
            if idx < len(val):
                val = val[idx]
            else:
                return None
        else:
            return None
    return val

def call_service(service_category, model_key, text, uid=None):
    """استدعاء أي خدمة API خارجية وإرجاع النتيجة أو الخطأ."""
    cfg = SERVICES.get(service_category, {}).get(model_key)
    if not cfg:
        return None, "Service not found"

    url = cfg["url"]
    method = cfg["method"]
    params = {}
    for k, v in cfg.get("params", {}).items():
        if v == "{text}":
            params[k] = text
        elif v == "{uid}":
            params[k] = uid or "default"
        else:
            params[k] = v

    headers = cfg.get("headers", {})
    timeout = 45

    try:
        if method == "GET":
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        else:
            resp = requests.post(url, data=params, headers=headers, timeout=timeout)
        resp.raise_for_status()

        response_type = cfg.get("response_type", "json")
        if response_type == "binary":
            return resp.content, None

        data = resp.json()
        if cfg.get("response_key"):
            result = get_nested_value(data, cfg["response_key"])
            return result, None
        return data, None
    except requests.exceptions.Timeout:
        return None, "Request timed out"
    except requests.exceptions.ConnectionError:
        return None, "Connection error"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP error: {e.response.status_code}"
    except Exception as e:
        return None, str(e)

# ========== قالب HTML الكامل ==========
HTML_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ platform_name }}</title>
  <style>
    :root {
      --bg-primary: #0b0c10;
      --bg-secondary: #15161e;
      --bg-tertiary: #1c1e28;
      --bg-card: rgba(28, 30, 40, 0.8);
      --bg-glass: rgba(20, 22, 30, 0.7);
      --border-color: #2a2d3a;
      --border-glass: rgba(255, 255, 255, 0.06);
      --text-primary: #e8eaed;
      --text-secondary: #9aa0a6;
      --text-muted: #6b7280;
      --accent: #a78bfa;
      --accent-hover: #c4b5fd;
      --accent-glow: rgba(167, 139, 250, 0.3);
      --user-bg: #1a3a5c;
      --user-bg-hover: #1e4268;
      --bot-bg: #1c1e28;
      --bot-border: #2a2d3a;
      --danger: #ef4444;
      --success: #10b981;
      --warning: #f59e0b;
      --scrollbar-thumb: #3a3d4a;
      --scrollbar-track: transparent;
      --radius-sm: 8px;
      --radius-md: 14px;
      --radius-lg: 20px;
      --radius-xl: 24px;
      --shadow-sm: 0 2px 8px rgba(0,0,0,0.3);
      --shadow-md: 0 4px 20px rgba(0,0,0,0.4);
      --shadow-glow: 0 0 20px var(--accent-glow);
      --transition: 0.2s ease;
    }

    * { margin: 0; padding: 0; box-sizing: border-box; }
    html { font-size: 16px; }
    body {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      height: 100vh;
      display: flex;
      overflow: hidden;
    }

    /* ===== Scrollbar ===== */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--scrollbar-track); }
    ::-webkit-scrollbar-thumb { background: var(--scrollbar-thumb); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #4a4d5a; }

    /* ===== Sidebar ===== */
    .sidebar {
      width: 280px;
      min-width: 280px;
      background: var(--bg-secondary);
      display: flex;
      flex-direction: column;
      border-left: 1px solid var(--border-color);
      transition: transform var(--transition), opacity var(--transition);
      z-index: 100;
      position: relative;
    }
    .sidebar-header {
      padding: 20px;
      text-align: center;
      border-bottom: 1px solid var(--border-color);
    }
    .sidebar-header img {
      width: 120px;
      height: auto;
      margin-bottom: 8px;
    }
    .sidebar-header h3 {
      font-size: 16px;
      color: var(--accent);
      font-weight: 600;
    }
    .sidebar-content {
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .sidebar-btn {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 16px;
      background: transparent;
      border: 1px solid var(--border-color);
      color: var(--text-primary);
      border-radius: var(--radius-md);
      cursor: pointer;
      font-size: 14px;
      transition: all var(--transition);
      width: 100%;
      text-align: right;
      font-family: inherit;
    }
    .sidebar-btn:hover {
      background: var(--bg-tertiary);
      border-color: var(--accent);
      color: var(--accent-hover);
      box-shadow: var(--shadow-glow);
    }
    .sidebar-btn svg { width: 18px; height: 18px; flex-shrink: 0; }
    .sidebar-section {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid var(--border-color);
    }
    .sidebar-section-title {
      font-size: 11px;
      text-transform: uppercase;
      color: var(--text-muted);
      padding: 8px 12px;
      letter-spacing: 1px;
      font-weight: 600;
    }
    .model-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-secondary);
      border-radius: var(--radius-sm);
      cursor: pointer;
      font-size: 13px;
      transition: all var(--transition);
      width: 100%;
      text-align: right;
      font-family: inherit;
    }
    .model-btn:hover {
      background: var(--bg-tertiary);
      color: var(--text-primary);
    }
    .model-btn.active {
      background: rgba(167, 139, 250, 0.15);
      border-color: var(--accent);
      color: var(--accent);
      font-weight: 500;
    }
    .model-btn .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent);
      flex-shrink: 0;
    }
    .sidebar-footer {
      padding: 12px 20px;
      border-top: 1px solid var(--border-color);
      font-size: 11px;
      color: var(--text-muted);
      text-align: center;
    }

    /* ===== Main ===== */
    .main {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    /* ===== Header ===== */
    .header {
      padding: 14px 24px;
      background: var(--bg-glass);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid var(--border-glass);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      z-index: 50;
    }
    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .menu-toggle {
      display: none;
      background: none;
      border: none;
      color: var(--text-primary);
      cursor: pointer;
      padding: 8px;
      border-radius: 8px;
    }
    .menu-toggle:hover { background: var(--bg-tertiary); }
    .header-title {
      font-size: 15px;
      font-weight: 500;
      color: var(--text-primary);
    }
    .header-title span { color: var(--accent); }
    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .header-badge {
      font-size: 11px;
      padding: 5px 12px;
      border-radius: 20px;
      background: rgba(167, 139, 250, 0.15);
      color: var(--accent-hover);
      border: 1px solid rgba(167, 139, 250, 0.3);
    }

    /* ===== Tab Bar ===== */
    .tab-bar {
      display: flex;
      gap: 4px;
      padding: 12px 24px;
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
    }
    .tab-btn {
      padding: 10px 22px;
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-secondary);
      border-radius: var(--radius-lg);
      cursor: pointer;
      font-size: 14px;
      transition: all var(--transition);
      font-family: inherit;
      font-weight: 500;
    }
    .tab-btn:hover {
      color: var(--text-primary);
      background: var(--bg-tertiary);
    }
    .tab-btn.active {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
      box-shadow: var(--shadow-glow);
    }

    /* ===== Chat Area ===== */
    .chat-area {
      flex: 1;
      overflow-y: auto;
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .welcome-screen {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      gap: 16px;
      padding: 40px;
    }
    .welcome-screen img {
      width: 100px;
      height: auto;
      opacity: 0.8;
    }
    .welcome-screen h1 {
      font-size: 28px;
      color: var(--text-primary);
    }
    .welcome-screen h1 span {
      background: linear-gradient(135deg, var(--accent), #7c3aed);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .welcome-screen p {
      color: var(--text-secondary);
      font-size: 15px;
      max-width: 500px;
    }

    /* ===== Messages ===== */
    .message {
      max-width: 85%;
      padding: 14px 20px;
      border-radius: var(--radius-lg);
      line-height: 1.7;
      animation: fadeIn 0.3s ease;
      position: relative;
      word-wrap: break-word;
      overflow-wrap: break-word;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .message.user {
      align-self: flex-end;
      background: var(--user-bg);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: var(--radius-lg) 4px var(--radius-lg) var(--radius-lg);
    }
    .message.bot {
      align-self: flex-start;
      background: var(--bot-bg);
      border: 1px solid var(--bot-border);
      border-radius: 4px var(--radius-lg) var(--radius-lg) var(--radius-lg);
    }
    .message-actions {
      position: absolute;
      top: 8px;
      left: 8px;
      display: flex;
      gap: 4px;
      opacity: 0;
      transition: opacity var(--transition);
    }
    .message:hover .message-actions { opacity: 1; }
    .msg-action-btn {
      background: rgba(0,0,0,0.5);
      border: none;
      color: #fff;
      padding: 4px 8px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 11px;
      transition: all var(--transition);
    }
    .msg-action-btn:hover { background: var(--accent); }
    .msg-action-btn.copied { background: var(--success); }

    /* ===== Typing Indicator ===== */
    .typing-indicator {
      display: flex;
      gap: 5px;
      padding: 10px 16px;
    }
    .typing-dot {
      width: 8px;
      height: 8px;
      background: var(--text-muted);
      border-radius: 50%;
      animation: typingBounce 1.2s infinite;
    }
    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes typingBounce {
      0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
      30% { opacity: 1; transform: scale(1.2); }
    }

    /* ===== Input Area ===== */
    .input-area {
      padding: 16px 24px;
      border-top: 1px solid var(--border-color);
      background: var(--bg-secondary);
      display: flex;
      gap: 12px;
      align-items: flex-end;
    }
    .input-wrapper {
      flex: 1;
      display: flex;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-xl);
      padding: 6px;
      transition: all var(--transition);
    }
    .input-wrapper:focus-within {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.1);
    }
    .input-wrapper textarea {
      flex: 1;
      background: transparent;
      border: none;
      color: var(--text-primary);
      padding: 10px 16px;
      font-size: 15px;
      resize: none;
      min-height: 48px;
      max-height: 180px;
      font-family: inherit;
      line-height: 1.5;
      outline: none;
    }
    .input-wrapper textarea::placeholder { color: var(--text-muted); }
    .send-btn {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: var(--accent);
      border: none;
      color: #fff;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all var(--transition);
      flex-shrink: 0;
    }
    .send-btn:hover {
      background: var(--accent-hover);
      box-shadow: var(--shadow-glow);
    }
    .send-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .send-btn svg { width: 20px; height: 20px; }

    /* ===== Image Tab ===== */
    .image-panel {
      display: none;
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      flex-direction: column;
      gap: 20px;
    }
    .image-panel.active { display: flex; }
    .image-form {
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .image-form label {
      font-size: 13px;
      color: var(--text-secondary);
      font-weight: 500;
    }
    .image-form input, .image-form select {
      width: 100%;
      padding: 12px 16px;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-md);
      color: var(--text-primary);
      font-size: 14px;
      font-family: inherit;
      transition: all var(--transition);
    }
    .image-form input:focus, .image-form select:focus {
      outline: none;
      border-color: var(--accent);
    }
    .image-form select {
      cursor: pointer;
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239aa0a6' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: left 12px center;
      padding-right: 36px;
    }
    .generate-btn {
      padding: 14px 28px;
      background: var(--accent);
      border: none;
      color: #fff;
      border-radius: var(--radius-xl);
      cursor: pointer;
      font-size: 15px;
      font-weight: 600;
      font-family: inherit;
      transition: all var(--transition);
      align-self: flex-start;
    }
    .generate-btn:hover {
      background: var(--accent-hover);
      box-shadow: var(--shadow-glow);
    }
    .generate-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .image-result {
      display: flex;
      flex-direction: column;
      gap: 16px;
      align-items: center;
    }
    .image-result img {
      max-width: 100%;
      max-height: 500px;
      border-radius: var(--radius-lg);
      border: 1px solid var(--border-color);
      box-shadow: var(--shadow-md);
    }
    .download-btn {
      padding: 10px 20px;
      background: var(--success);
      border: none;
      color: #fff;
      border-radius: var(--radius-xl);
      cursor: pointer;
      font-family: inherit;
      font-size: 14px;
      transition: all var(--transition);
    }
    .download-btn:hover { filter: brightness(1.2); }

    /* ===== Error Toast ===== */
    .toast {
      position: fixed;
      bottom: 100px;
      right: 50%;
      transform: translateX(50%);
      background: var(--danger);
      color: #fff;
      padding: 12px 24px;
      border-radius: var(--radius-xl);
      font-size: 14px;
      z-index: 1000;
      animation: slideUp 0.3s ease;
      box-shadow: var(--shadow-md);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    @keyframes slideUp {
      from { transform: translateX(50%) translateY(20px); opacity: 0; }
      to { transform: translateX(50%) translateY(0); opacity: 1; }
    }
    .toast.success { background: var(--success); }
    .toast-close {
      background: none;
      border: none;
      color: #fff;
      cursor: pointer;
      font-size: 16px;
      margin-right: 8px;
    }

    /* ===== Markdown داخل رسائل البوت ===== */
    .bot-message-content a { color: #a78bfa; text-decoration: underline; }
    .bot-message-content a:hover { color: #c4b5fd; }
    .bot-message-content strong { color: #e2b6c2; font-weight: 600; }
    .bot-message-content em { color: #b9c3db; }
    .bot-message-content code {
      background: #0f1017;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Fira Code', 'Cascadia Code', monospace;
      font-size: 13px;
      direction: ltr;
      display: inline-block;
    }
    .bot-message-content pre {
      background: #0f1017;
      padding: 14px 18px;
      border-radius: var(--radius-md);
      overflow-x: auto;
      margin: 8px 0;
      direction: ltr;
      text-align: left;
    }
    .bot-message-content pre code {
      background: transparent;
      padding: 0;
      font-size: 13px;
      line-height: 1.6;
    }
    .bot-message-content ul, .bot-message-content ol {
      margin: 8px 0;
      padding-right: 24px;
    }
    .bot-message-content li { margin: 4px 0; }
    .bot-message-content blockquote {
      border-right: 3px solid var(--accent);
      padding-right: 12px;
      margin: 8px 0;
      color: var(--text-secondary);
      background: rgba(167,139,250,0.05);
      border-radius: 0 8px 8px 0;
    }

    /* ===== Responsive ===== */
    @media (max-width: 768px) {
      .sidebar {
        position: fixed;
        right: 0;
        top: 0;
        bottom: 0;
        transform: translateX(100%);
        opacity: 0;
        box-shadow: -4px 0 20px rgba(0,0,0,0.5);
      }
      .sidebar.open {
        transform: translateX(0);
        opacity: 1;
      }
      .menu-toggle { display: block; }
      .header { padding: 10px 16px; }
      .tab-bar { padding: 8px 12px; }
      .tab-btn { padding: 8px 14px; font-size: 12px; }
      .chat-area { padding: 12px; }
      .message { max-width: 95%; }
      .input-area { padding: 10px 12px; }
      .image-panel { padding: 12px; }
    }
    @media (max-width: 480px) {
      .sidebar { width: 260px; min-width: 260px; }
      .header-title { font-size: 13px; }
      .message { padding: 10px 14px; font-size: 14px; }
    }

    /* ===== Sidebar Overlay ===== */
    .sidebar-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.6);
      z-index: 99;
    }
    .sidebar-overlay.show { display: block; }
  </style>
</head>
<body>

  <!-- Sidebar Overlay -->
  <div class="sidebar-overlay" id="sidebarOverlay" onclick="closeSidebar()"></div>

  <!-- Sidebar -->
  <div class="sidebar" id="sidebar">
    <div class="sidebar-header">
      <img src="{{ logo_url }}" alt="KX AI Logo" onerror="this.style.display='none';this.nextElementSibling.style.display='block'">
      <h3 style="display:none;">🤖 KX AI</h3>
      <h3>{{ platform_name }}</h3>
    </div>
    <div class="sidebar-content">
      <button class="sidebar-btn" onclick="newChat()">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        New Chat
      </button>

      <div class="sidebar-section">
        <div class="sidebar-section-title">💬 Chat Models</div>
        <div id="chatModelsList"></div>
      </div>

      <div class="sidebar-section">
        <div class="sidebar-section-title">🖼️ Image Models</div>
        <div id="imageModelsList"></div>
      </div>

      <button class="sidebar-btn" onclick="clearChat()" style="margin-top:auto; color:var(--danger); border-color:rgba(239,68,68,0.3);">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
        Clear Chat
      </button>
    </div>
    <div class="sidebar-footer">
      © 2026 KX Team | Powered by KX
    </div>
  </div>

  <!-- Main -->
  <div class="main">
    <!-- Header -->
    <div class="header">
      <div class="header-left">
        <button class="menu-toggle" onclick="toggleSidebar()" aria-label="Menu">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        </button>
        <span class="header-title">🤖 <span>KX AI</span> Platform</span>
      </div>
      <div class="header-actions">
        <span class="header-badge" id="currentModelBadge">WormGPT</span>
      </div>
    </div>

    <!-- Tab Bar -->
    <div class="tab-bar">
      <button class="tab-btn active" data-tab="chat" onclick="switchTab('chat')">💬 Chat</button>
      <button class="tab-btn" data-tab="image" onclick="switchTab('image')">🖼️ Image Generation</button>
    </div>

    <!-- Chat Area -->
    <div class="chat-area" id="chatArea">
      <div class="welcome-screen" id="welcomeScreen">
        <img src="{{ logo_url }}" alt="KX AI" onerror="this.style.display='none'">
        <h1>Welcome to <span>KX AI</span> Platform</h1>
        <p>Choose a model from the sidebar and start chatting. Supports streaming, markdown, and more!</p>
        <p style="color:var(--text-muted);font-size:12px;">Powered by <strong>KX Team</strong></p>
      </div>
    </div>

    <!-- Image Panel -->
    <div class="image-panel" id="imagePanel">
      <div class="image-form">
        <label for="imagePrompt">🖊️ Prompt</label>
        <input type="text" id="imagePrompt" placeholder="Describe your image in detail...">
        <label for="negativePrompt">🚫 Negative Prompt (optional)</label>
        <input type="text" id="negativePrompt" placeholder="Things to avoid...">
        <label for="imageSize">📐 Size</label>
        <select id="imageSize">
          <option value="512x512">512 x 512</option>
          <option value="768x768">768 x 768</option>
          <option value="1024x1024" selected>1024 x 1024</option>
        </select>
        <button class="generate-btn" id="generateBtn" onclick="generateImage()">✨ Generate Image</button>
      </div>
      <div class="image-result" id="imageResult"></div>
    </div>

    <!-- Input Area -->
    <div class="input-area" id="inputArea">
      <div class="input-wrapper">
        <textarea id="userInput" placeholder="Type your message... (Enter to send, Shift+Enter for new line)" rows="1" onkeydown="handleInputKey(event)"></textarea>
        <button class="send-btn" id="sendBtn" onclick="sendMessage()" aria-label="Send">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
        </button>
      </div>
    </div>
  </div>

  <!-- Toast Container -->
  <div id="toastContainer"></div>

  <script>
    // ========== Global State ==========
    let currentTab = 'chat';
    let currentChatModel = 'wormgpt';
    let currentImageModel = 'stable_diffusion';
    let isGenerating = false;
    let chatHistory = [];
    let modelsData = {};

    // ========== DOM Elements ==========
    const chatArea = document.getElementById('chatArea');
    const welcomeScreen = document.getElementById('welcomeScreen');
    const imagePanel = document.getElementById('imagePanel');
    const inputArea = document.getElementById('inputArea');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const currentModelBadge = document.getElementById('currentModelBadge');
    const chatModelsList = document.getElementById('chatModelsList');
    const imageModelsList = document.getElementById('imageModelsList');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const toastContainer = document.getElementById('toastContainer');
    const imageResult = document.getElementById('imageResult');
    const generateBtn = document.getElementById('generateBtn');

    // ========== Load Models ==========
    async function loadModels() {
      try {
        const resp = await fetch('/v1/models');
        const data = await resp.json();
        modelsData = data.models || {};

        // تصنيف النماذج
        const chatModels = {};
        const imageModels = {};
        for (const [key, model] of Object.entries(modelsData)) {
          if (model.category === 'chat') {
            chatModels[key] = model;
          } else if (model.category === 'image') {
            imageModels[key] = model;
          }
        }

        // عرض نماذج الشات
        chatModelsList.innerHTML = '';
        for (const [key, model] of Object.entries(chatModels)) {
          const displayKey = key.startsWith('chat/') ? key.replace('chat/', '') : key;
          const btn = document.createElement('button');
          btn.className = 'model-btn' + (displayKey === currentChatModel ? ' active' : '');
          btn.innerHTML = `<span class="dot"></span>${model.name}`;
          btn.onclick = () => selectChatModel(displayKey, model.name);
          chatModelsList.appendChild(btn);
        }

        // عرض نماذج الصور
        imageModelsList.innerHTML = '';
        for (const [key, model] of Object.entries(imageModels)) {
          const displayKey = key.startsWith('image/') ? key.replace('image/', '') : key;
          const btn = document.createElement('button');
          btn.className = 'model-btn' + (displayKey === currentImageModel ? ' active' : '');
          btn.innerHTML = `<span class="dot" style="background:#10b981;"></span>${model.name}`;
          btn.onclick = () => selectImageModel(displayKey, model.name);
          imageModelsList.appendChild(btn);
        }

        // تحديث الشارة
        updateModelBadge();
      } catch (e) {
        showToast('Failed to load models: ' + e.message, 'error');
      }
    }

    function selectChatModel(key, name) {
      currentChatModel = key;
      updateModelBadge();
      // تحديث الـ active
      chatModelsList.querySelectorAll('.model-btn').forEach(b => b.classList.remove('active'));
      const btns = chatModelsList.querySelectorAll('.model-btn');
      btns.forEach(b => { if (b.textContent.trim() === name) b.classList.add('active'); });
      // التبديل إلى تبويب الشات
      switchTab('chat');
    }

    function selectImageModel(key, name) {
      currentImageModel = key;
      updateModelBadge();
      imageModelsList.querySelectorAll('.model-btn').forEach(b => b.classList.remove('active'));
      const btns = imageModelsList.querySelectorAll('.model-btn');
      btns.forEach(b => { if (b.textContent.trim() === name) b.classList.add('active'); });
      switchTab('image');
    }

    function updateModelBadge() {
      if (currentTab === 'chat') {
        const model = modelsData['chat/' + currentChatModel];
        currentModelBadge.textContent = model ? model.name : currentChatModel;
      } else {
        const model = modelsData['image/' + currentImageModel];
        currentModelBadge.textContent = model ? model.name : currentImageModel;
      }
    }

    // ========== Tab Switching ==========
    function switchTab(tab) {
      currentTab = tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelector(`[data-tab="${tab}"]`)?.classList.add('active');

      if (tab === 'chat') {
        imagePanel.classList.remove('active');
        inputArea.style.display = 'flex';
        chatArea.style.display = 'flex';
      } else {
        imagePanel.classList.add('active');
        inputArea.style.display = 'none';
        chatArea.style.display = 'none';
      }
      updateModelBadge();
    }

    // ========== Sidebar ==========
    function toggleSidebar() {
      sidebar.classList.toggle('open');
      sidebarOverlay.classList.toggle('show');
    }
    function closeSidebar() {
      sidebar.classList.remove('open');
      sidebarOverlay.classList.remove('show');
    }

    // ========== Chat Functions ==========
    function newChat() {
      chatHistory = [];
      chatArea.innerHTML = `
        <div class="welcome-screen" id="welcomeScreen">
          <img src="{{ logo_url }}" alt="KX AI" onerror="this.style.display='none'">
          <h1>Welcome to <span>KX AI</span> Platform</h1>
          <p>Choose a model from the sidebar and start chatting. Supports streaming, markdown, and more!</p>
          <p style="color:var(--text-muted);font-size:12px;">Powered by <strong>KX Team</strong></p>
        </div>`;
      saveChatToStorage();
      closeSidebar();
    }

    function clearChat() {
      if (confirm('Are you sure you want to clear all chat history?')) {
        newChat();
      }
    }

    function addMessage(text, role) {
      // إخفاء شاشة الترحيب
      const ws = document.getElementById('welcomeScreen');
      if (ws) ws.remove();

      const div = document.createElement('div');
      div.className = 'message ' + role;
      div.innerHTML = `
        <div class="message-actions">
          <button class="msg-action-btn" onclick="copyMessage(this)" title="Copy">📋</button>
        </div>
        <div class="bot-message-content">${role === 'bot' ? formatMarkdown(text) : escapeHtml(text)}</div>
      `;
      chatArea.appendChild(div);
      scrollToBottom();
      chatHistory.push({ role, text });
      saveChatToStorage();
      return div;
    }

    function updateBotMessage(div, text) {
      const contentDiv = div.querySelector('.bot-message-content');
      if (contentDiv) {
        contentDiv.innerHTML = formatMarkdown(text);
      }
      scrollToBottom();
    }

    function showTyping() {
      const ws = document.getElementById('welcomeScreen');
      if (ws) ws.remove();

      const div = document.createElement('div');
      div.className = 'message bot';
      div.id = 'typingIndicator';
      div.innerHTML = '<div class="typing-indicator"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div>';
      chatArea.appendChild(div);
      scrollToBottom();
    }

    function removeTyping() {
      const el = document.getElementById('typingIndicator');
      if (el) el.remove();
    }

    function scrollToBottom() {
      chatArea.scrollTop = chatArea.scrollHeight;
    }

    async function sendMessage() {
      const text = userInput.value.trim();
      if (!text || isGenerating) return;
      if (currentTab !== 'chat') {
        switchTab('chat');
        setTimeout(() => sendMessage(), 100);
        return;
      }

      addMessage(text, 'user');
      userInput.value = '';
      autoResizeTextarea();
      showTyping();
      isGenerating = true;
      sendBtn.disabled = true;

      try {
        const response = await fetch('/v1/chat/completions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: currentChatModel,
            messages: [{ role: 'user', content: text }],
            stream: true
          })
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `HTTP ${response.status}`);
        }

        removeTyping();
        const botDiv = addMessage('', 'bot');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
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
                  updateBotMessage(botDiv, fullText);
                }
              } catch(e) {}
            }
          }
        }

        // تحديث آخر رسالة في التاريخ
        if (chatHistory.length > 0 && chatHistory[chatHistory.length - 1].role === 'bot') {
          chatHistory[chatHistory.length - 1].text = fullText;
        }
        saveChatToStorage();
      } catch(e) {
        removeTyping();
        addMessage('⚠️ Error: ' + e.message, 'bot');
      } finally {
        isGenerating = false;
        sendBtn.disabled = false;
        userInput.focus();
      }
    }

    function copyMessage(btn) {
      const msgDiv = btn.closest('.message');
      const contentDiv = msgDiv.querySelector('.bot-message-content');
      const text = contentDiv ? contentDiv.textContent : msgDiv.textContent;
      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = '✅';
        btn.classList.add('copied');
        setTimeout(() => {
          btn.textContent = '📋';
          btn.classList.remove('copied');
        }, 1500);
      }).catch(() => {
        showToast('Failed to copy', 'error');
      });
    }

    function handleInputKey(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
      // Auto-resize on any key
      setTimeout(autoResizeTextarea, 0);
    }

    function autoResizeTextarea() {
      userInput.style.height = 'auto';
      userInput.style.height = Math.min(userInput.scrollHeight, 180) + 'px';
    }

    // ========== Image Generation ==========
    async function generateImage() {
      const prompt = document.getElementById('imagePrompt').value.trim();
      if (!prompt) {
        showToast('Please enter a prompt', 'error');
        return;
      }
      if (isGenerating) return;

      const negativePrompt = document.getElementById('negativePrompt').value.trim();
      const size = document.getElementById('imageSize').value;

      isGenerating = true;
      generateBtn.disabled = true;
      generateBtn.textContent = '⏳ Generating...';
      imageResult.innerHTML = '<p style="color:var(--text-secondary);">Generating image, please wait...</p>';

      try {
        const fullPrompt = negativePrompt ? `${prompt} --no ${negativePrompt}` : prompt;
        const response = await fetch('/v1/images/generations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            model: currentImageModel,
            prompt: fullPrompt,
            size: size
          })
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.error || `HTTP ${response.status}`);
        }

        const data = await response.json();
        if (data.data && data.data[0] && data.data[0].url) {
          const imgUrl = data.data[0].url;
          imageResult.innerHTML = `
            <img src="${imgUrl}" alt="Generated Image" onerror="this.onerror=null;this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22300%22 height=%22300%22><rect fill=%22%231c1e28%22 width=%22300%22 height=%22300%22/><text fill=%22%23ef4444%22 x=%2250%25%22 y=%2250%25%22 text-anchor=%22middle%22 dy=%22.3em%22 font-size=%2216%22>Image failed to load</text></svg>';">
            <button class="download-btn" onclick="downloadImage('${imgUrl}')">⬇ Download Image</button>
          `;
        } else {
          throw new Error('No image URL in response');
        }
      } catch(e) {
        imageResult.innerHTML = `<p style="color:var(--danger);">⚠️ Error: ${e.message}</p>`;
      } finally {
        isGenerating = false;
        generateBtn.disabled = false;
        generateBtn.textContent = '✨ Generate Image';
      }
    }

    function downloadImage(url) {
      const a = document.createElement('a');
      a.href = url;
      a.download = 'kx-ai-image-' + Date.now() + '.png';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }

    // ========== Markdown Parser ==========
    function formatMarkdown(text) {
      if (!text) return '';
      let html = escapeHtml(text);

      // Code blocks (```)
      html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code>${code.trim()}</code></pre>`;
      });

      // Inline code (`)
      html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

      // Bold (**)
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

      // Italic (*)
      html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

      // Links [text](url)
      html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

      // Blockquote (>)
      html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

      // Unordered lists
      html = html.replace(/^[\*\-] (.+)$/gm, '<li>$1</li>');
      html = html.replace(/(<li>.*<\/li>)/gs, (match) => {
        if (!match.includes('</ul>')) return '<ul>' + match + '</ul>';
        return match;
      });

      // Ordered lists
      html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

      // Line breaks
      html = html.replace(/\\n/g, '<br>').replace(/\n/g, '<br>');

      // Clean up multiple brs
      html = html.replace(/<br>\s*<br>/g, '<br><br>');

      return html;
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // ========== Toast ==========
    function showToast(message, type = 'error') {
      const toast = document.createElement('div');
      toast.className = 'toast ' + (type === 'success' ? 'success' : '');
      toast.innerHTML = `
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
      `;
      toastContainer.appendChild(toast);
      setTimeout(() => toast.remove(), 5000);
    }

    // ========== Local Storage ==========
    function saveChatToStorage() {
      try {
        localStorage.setItem('kx_chat_history', JSON.stringify(chatHistory));
        localStorage.setItem('kx_chat_model', currentChatModel);
        localStorage.setItem('kx_image_model', currentImageModel);
      } catch(e) {}
    }

    function loadChatFromStorage() {
      try {
        const saved = localStorage.getItem('kx_chat_history');
        if (saved) {
          chatHistory = JSON.parse(saved);
          // إعادة بناء واجهة الشات
          const ws = document.getElementById('welcomeScreen');
          if (ws && chatHistory.length > 0) ws.remove();
          chatHistory.forEach(msg => {
            const div = document.createElement('div');
            div.className = 'message ' + msg.role;
            div.innerHTML = `
              <div class="message-actions">
                <button class="msg-action-btn" onclick="copyMessage(this)" title="Copy">📋</button>
              </div>
              <div class="bot-message-content">${msg.role === 'bot' ? formatMarkdown(msg.text) : escapeHtml(msg.text)}</div>
            `;
            chatArea.appendChild(div);
          });
          if (chatHistory.length > 0) scrollToBottom();
        }
        const savedChatModel = localStorage.getItem('kx_chat_model');
        if (savedChatModel) currentChatModel = savedChatModel;
        const savedImageModel = localStorage.getItem('kx_image_model');
        if (savedImageModel) currentImageModel = savedImageModel;
      } catch(e) {}
    }

    // ========== Init ==========
    async function init() {
      loadChatFromStorage();
      await loadModels();
      updateModelBadge();
      autoResizeTextarea();
      userInput.addEventListener('input', autoResizeTextarea);
      // إغلاق السايدبار عند النقر على overlay
      sidebarOverlay.addEventListener('click', closeSidebar);
      // إغلاق السايدبار عند ضغط Escape
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeSidebar();
      });
    }

    init();
  </script>
</body>
</html>
'''

# ========== API Routes ==========
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE,
                                  platform_name=PLATFORM_NAME,
                                  logo_url=LOGO_URL,
                                  owner=OWNER)

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
    return jsonify({
        "object": "list",
        "models": all_models,
        "developer": DEVELOPER,
        "powered_by": POWERED_BY
    })

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    try:
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

        # التحقق من وجود النموذج
        if model not in SERVICES.get("chat", {}):
            return jsonify({"error": f"Model '{model}' not found"}), 404

        result, error = call_service("chat", model, text)
        if error:
            return jsonify({"error": error}), 500
        if result is None:
            return jsonify({"error": "Empty response from service"}), 500

        result = str(result)
        request_id = "chatcmpl-" + secrets.token_hex(12)
        created = int(time.time())

        if not stream:
            return jsonify({
                "id": request_id,
                "object": "chat.completion",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": result},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(text.split()),
                    "completion_tokens": len(result.split()),
                    "total_tokens": len(text.split()) + len(result.split())
                },
                "developer": DEVELOPER,
                "powered_by": POWERED_BY
            })
        else:
            def generate():
                words = re.split(r'(\s+)', result)
                for i, word in enumerate(words):
                    chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": word},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    time.sleep(0.015)
                # إرسال chunk النهاية
                final_chunk = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
            return Response(
                stream_with_context(generate()),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/v1/images/generations', methods=['POST'])
def image_generations():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        model = data.get('model', 'stable_diffusion')
        prompt = data.get('prompt', '').strip()
        size = data.get('size', '1024x1024')

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # التحقق من وجود النموذج
        if model not in SERVICES.get("image", {}):
            return jsonify({"error": f"Image model '{model}' not found"}), 404

        result, error = call_service("image", model, prompt)
        if error:
            # إذا كان الخطأ متعلقاً بمفتاح Hugging Face، نعرض رسالة توضيحية
            if '401' in str(error) or '403' in str(error):
                return jsonify({
                    "error": "Image generation requires a valid Hugging Face API key. Set HF_TOKEN environment variable or update the API key in SERVICES configuration.",
                    "hint": "Get a free key from https://huggingface.co/settings/tokens"
                }), 401
            return jsonify({"error": error}), 500

        if result is None:
            return jsonify({"error": "Empty response from image service"}), 500

        # تحويل الصورة إلى base64 لعرضها
        import base64
        img_base64 = base64.b64encode(result).decode('utf-8')
        img_url = f"data:image/png;base64,{img_base64}"

        return jsonify({
            "created": int(time.time()),
            "data": [{
                "url": img_url,
                "model": model,
                "size": size,
                "revised_prompt": prompt
            }],
            "developer": DEVELOPER,
            "powered_by": POWERED_BY
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/v1/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": int(time.time()),
        "developer": DEVELOPER,
        "powered_by": POWERED_BY
    })

@app.route('/v1/status')
def status():
    return jsonify({
        "status": "running",
        "uptime": int(time.time()),
        "models_available": {
            "chat": list(SERVICES.get("chat", {}).keys()),
            "image": list(SERVICES.get("image", {}).keys())
        },
        "total_models": sum(len(v) for v in SERVICES.values()),
        "developer": DEVELOPER,
        "powered_by": POWERED_BY
    })

@app.route('/v1/about')
def about():
    return jsonify({
        "platform": PLATFORM_NAME,
        "version": "1.0.0",
        "developer": DEVELOPER,
        "powered_by": POWERED_BY,
        "description": "KX AI Platform - Multi-model AI chat and image generation platform",
        "features": [
            "Multi-model chat support",
            "Streaming responses",
            "Image generation",
            "Markdown support",
            "Dark mode UI",
            "Responsive design"
        ],
        "repository": "https://github.com/kx-team/kx-ai-platform",
        "contact": CHANNEL
    })

# ========== معالجة الأخطاء العامة ==========
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "developer": DEVELOPER}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error", "developer": DEVELOPER}), 500

# ========== تشغيل التطبيق ==========
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
