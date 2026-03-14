import json
import os
import threading
import time
import uuid
from pathlib import Path
from quart import Quart, request, jsonify
from playwright.sync_api import sync_playwright

app = Quart(__name__)
RESULTS = {}
CAMOUFOX_WS_URL = os.getenv('CAMOUFOX_WS_URL', 'ws://camoufox:9222/camoufox')
LOG_FILE = Path('/tmp/adapter_tasks.log')


def log(event, **kw):
    row = {'ts': time.time(), 'event': event, **kw}
    with LOG_FILE.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def processing(task_id: str):
    return {'errorId': 0, 'status': 'processing', 'taskId': task_id}


def unsolvable(desc: str = 'Workers could not solve the Captcha'):
    return {'errorId': 1, 'errorCode': 'ERROR_CAPTCHA_UNSOLVABLE', 'errorDescription': desc[:1000]}


def ready(token: str):
    return {'errorId': 0, 'status': 'ready', 'solution': {'token': token}}


INJECT_SNIPPET = r'''
(() => {
  window.__TS_TOKEN = '';
  window.__TS_SITEKEY = window.__TS_SITEKEY || '';
  window.onTurnstileCallback = function(token) {
    window.__TS_TOKEN = token || '';
    let tokenInput = document.querySelector('input[name="cf-turnstile-response"]');
    if (!tokenInput) {
      tokenInput = document.createElement('input');
      tokenInput.type = 'hidden';
      tokenInput.name = 'cf-turnstile-response';
      document.body.appendChild(tokenInput);
    }
    tokenInput.value = token || '';
  };
  document.querySelectorAll('.cf-turnstile').forEach(el => el.remove());
  const captchaDiv = document.createElement('div');
  captchaDiv.className = 'cf-turnstile';
  captchaDiv.setAttribute('data-sitekey', window.__TS_SITEKEY || '');
  captchaDiv.setAttribute('data-callback', 'onTurnstileCallback');
  captchaDiv.style.position = 'fixed';
  captchaDiv.style.top = '20px';
  captchaDiv.style.left = '20px';
  captchaDiv.style.zIndex = '9999';
  captchaDiv.style.backgroundColor = 'white';
  captchaDiv.style.padding = '15px';
  document.body.appendChild(captchaDiv);
  const renderNow = () => {
    if (window.turnstile && window.turnstile.render) {
      window.__TS_WIDGET_ID = window.turnstile.render(captchaDiv, {
        sitekey: window.__TS_SITEKEY,
        callback: function(token) { window.onTurnstileCallback(token); },
        'error-callback': function(e) { window.__TS_ERROR = String(e || 'error'); }
      });
      return true;
    }
    return false;
  };
  if (!renderNow()) {
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
    script.async = true;
    script.defer = true;
    script.onload = () => setTimeout(renderNow, 1000);
    document.head.appendChild(script);
  }
})()
'''


def token_snapshot(page):
    js = r'''
() => {
  const input = document.querySelector('input[name="cf-turnstile-response"]');
  let resp = '';
  try {
    if (window.turnstile && typeof window.turnstile.getResponse === 'function') {
      resp = String(window.turnstile.getResponse(window.__TS_WIDGET_ID) || window.turnstile.getResponse() || '');
    }
  } catch (e) {}
  return {
    inputValue: input ? String(input.value || '') : '',
    callbackToken: String(window.__TS_TOKEN || ''),
    getResponseToken: resp,
    tsError: String(window.__TS_ERROR || ''),
    widgetId: String(window.__TS_WIDGET_ID || ''),
  };
}
'''
    return page.evaluate(js)


def try_click(page, task_id: str):
    selectors = [
        'iframe[src*="challenges.cloudflare.com"]',
        'iframe[src*="turnstile"]',
        '.cf-turnstile',
        '[data-sitekey]',
        '*[class*="turnstile"]',
    ]
    for sel in selectors:
        try:
            page.locator(sel).first.click(timeout=1000)
            log('click_ok', task_id=task_id, selector=sel)
            return True
        except Exception:
            pass
    return False


def solve_worker(task_id: str, url: str, sitekey: str):
    started = time.time()
    log('task_start', task_id=task_id, url=url, sitekey_len=len(sitekey or ''))
    try:
        with sync_playwright() as p:
            browser = p.firefox.connect(CAMOUFOX_WS_URL, timeout=10000)
            log('ws_connected', task_id=task_id)
            page = browser.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            log('goto_ok', task_id=task_id, current_url=page.url, title=page.title())
            page.evaluate(f"window.__TS_SITEKEY = {sitekey!r}")
            page.evaluate(INJECT_SNIPPET)
            log('inject_done', task_id=task_id)
            for attempt in range(36):
                snap = token_snapshot(page)
                token = snap.get('callbackToken') or snap.get('getResponseToken') or snap.get('inputValue')
                if token:
                    RESULTS[task_id] = ready(token)
                    log('token_ready', task_id=task_id, token_prefix=token[:8], source=('callback' if snap.get('callbackToken') else 'getResponse' if snap.get('getResponseToken') else 'input'), elapsed=round(time.time()-started,2))
                    browser.close()
                    return
                if attempt > 2 and attempt % 3 == 0:
                    try_click(page, task_id)
                if attempt in {0,3,6,10,15,20,25,30,35}:
                    log('poll', task_id=task_id, attempt=attempt, snap=snap)
                time.sleep(min(0.5 + attempt * 0.05, 2.0))
            browser.close()
        RESULTS[task_id] = unsolvable(f'no token after {time.time()-started:.2f}s')
        log('unsolvable', task_id=task_id, elapsed=round(time.time()-started,2))
    except Exception as e:
        RESULTS[task_id] = unsolvable(str(e))
        log('exception', task_id=task_id, error=str(e))


@app.get('/')
async def index():
    return jsonify({'ok': True, 'service': 'camoufox-turnstile-adapter', 'ws': CAMOUFOX_WS_URL, 'results': len(RESULTS)})

@app.get('/debug/tasks')
async def debug_tasks():
    return jsonify(RESULTS)

@app.get('/turnstile')
async def turnstile():
    url = request.args.get('url')
    sitekey = request.args.get('sitekey')
    if not url or not sitekey:
        return jsonify({'errorId': 1, 'errorCode': 'ERROR_WRONG_PAGEURL', 'errorDescription': "Both 'url' and 'sitekey' are required"})
    task_id = str(uuid.uuid4())
    RESULTS[task_id] = processing(task_id)
    log('task_created', task_id=task_id)
    threading.Thread(target=solve_worker, args=(task_id, url, sitekey), daemon=True).start()
    return jsonify({'errorId': 0, 'taskId': task_id})

@app.get('/result')
async def result():
    task_id = request.args.get('id', '')
    if task_id not in RESULTS:
        return jsonify({'errorId': 1, 'errorCode': 'ERROR_CAPTCHA_UNSOLVABLE', 'errorDescription': 'Task not found'})
    return jsonify(RESULTS[task_id])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5072)
