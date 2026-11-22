#!/usr/bin/env python3
"""
gemini_chrome_bridge.py: Send prompts to the live Google Chrome Gemini tab and fetch the response.
Uses native macOS AppleScript to communicate directly with the active Chrome session.
"""

import argparse
import base64
import html
import json
import subprocess
import sys
import time


def execute_chrome_js(js_code: str, activate: bool = False) -> str:
    """Execute JavaScript in the front Chrome tab via osascript with base64 encoding."""
    b64 = base64.b64encode(js_code.encode("utf-8")).decode("ascii")
    activate_stmt = "activate\n    delay 0.2\n" if activate else ""
    apple_script = f'''
tell application "Google Chrome"
    {activate_stmt}set res to execute front window's active tab javascript "(() => {{ try {{ return Function(decodeURIComponent(escape(atob('{b64}'))))(); }} catch(e) {{ return 'JS_ERR: ' + e.toString(); }} }})()"
    return res
end tell
'''
    proc = subprocess.run(
        ["osascript", "-"],
        input=apple_script,
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"AppleScript error: {proc.stderr.strip()}")
    res = proc.stdout.strip()
    if res.startswith("JS_ERR:"):
        raise RuntimeError(f"JavaScript execution error in Chrome: {res[7:].strip()}")
    return res


def send_prompt_and_get_response(prompt_text: str, timeout_sec: int = 180) -> str:
    """Send text to active Gemini tab and poll until response generation completes."""
    # 1. Verify URL
    url = execute_chrome_js("return window.location.href;")
    if "gemini.google.com" not in url:
        raise RuntimeError(f"Active tab is not Google Gemini. Found URL: {url}")

    # 2. Record initial model response count
    init_check_js = """
    const responses = Array.from(document.querySelectorAll('model-response, message-content, .model-response-text'));
    return JSON.stringify({ count: responses.length });
    """
    initial_res = json.loads(execute_chrome_js(init_check_js))
    initial_count = initial_res.get("count", 0)

    # 3. Inject text via TrustedHTML paragraphs (preserves full markdown without execCommand truncation)
    paras = "".join(f"<p>{html.escape(l) if l.strip() else '<br>'}</p>" for l in prompt_text.split("\n"))
    inject_js = f"""
    const editor = document.querySelector('rich-textarea div[contenteditable="true"], div[contenteditable="true"]');
    if (!editor) return JSON.stringify({{ ok: false, error: "Input editor not found" }});
    
    let policy;
    try {{
        policy = window.trustedTypes.createPolicy('geminiBridgePolicy', {{ createHTML: s => s }});
    }} catch(e) {{
        policy = {{ createHTML: s => s }};
    }}

    editor.focus();
    editor.innerHTML = policy.createHTML({json.dumps(paras)});
    editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
    editor.dispatchEvent(new Event('change', {{ bubbles: true }}));

    return JSON.stringify({{ ok: true }});
    """
    res = json.loads(execute_chrome_js(inject_js, activate=True))
    if not res.get("ok"):
        raise RuntimeError(f"Failed to inject text: {res.get('error')}")

    time.sleep(0.5)

    # Verify injection succeeded and was not truncated
    check_inject_js = """
    const editor = document.querySelector('rich-textarea div[contenteditable="true"], div[contenteditable="true"]');
    return JSON.stringify({ len: editor ? editor.innerText.length : 0 });
    """
    injected_info = json.loads(execute_chrome_js(check_inject_js))
    injected_len = injected_info.get("len", 0)
    expected_min = min(len(prompt_text) * 4 // 5, 2000)
    if len(prompt_text) > 100 and injected_len < expected_min:
        raise RuntimeError(f"Text injection truncated: expected ~{len(prompt_text)} chars, but editor only has {injected_len} chars.")

    # 4. Wait for send button to become active and click it
    click_send_js = """
    const sendBtn = document.querySelector('button[aria-label*="Send message"], button.send-button');
    if (sendBtn && !sendBtn.disabled && sendBtn.getAttribute('aria-disabled') !== 'true') {
        sendBtn.click();
        return JSON.stringify({ ok: true });
    }
    return JSON.stringify({ ok: false, reason: "Send button not ready" });
    """
    clicked = False
    for _ in range(12):
        time.sleep(0.5)
        click_res = json.loads(execute_chrome_js(click_send_js))
        if click_res.get("ok"):
            clicked = True
            break

    if not clicked:
        raise RuntimeError("Send button remained disabled after text injection.")

    sys.stderr.write("Prompt sent to Gemini. Waiting for response generation...\n")

    # 5. Poll for completion of the new response
    poll_js = """
    const stopBtn = document.querySelector('button[aria-label*="Stop response"], div[aria-label*="Thinking"]');
    const isStreaming = !!stopBtn;

    const responses = Array.from(document.querySelectorAll('model-response, message-content, .model-response-text'));
    let responseText = "";
    if (responses.length > 0) {
        responseText = responses[responses.length - 1].innerText.trim();
    }

    return JSON.stringify({
        count: responses.length,
        isStreaming: isStreaming,
        responseText: responseText
    });
    """

    start_time = time.time()
    last_text = ""
    stable_count = 0

    while time.time() - start_time < timeout_sec:
        time.sleep(2)
        raw_poll = execute_chrome_js(poll_js)
        if not raw_poll:
            continue
        try:
            status = json.loads(raw_poll)
        except json.JSONDecodeError:
            continue

        count = status.get("count", 0)
        text = status.get("responseText", "")
        streaming = status.get("isStreaming", False)

        # Ensure we are looking at the new response
        if count > initial_count and text:
            if text == last_text and not streaming:
                stable_count += 1
                if stable_count >= 2:
                    return text
            else:
                stable_count = 0
            last_text = text

    if last_text and count > initial_count:
        return last_text

    raise TimeoutError(f"No response received from Gemini within {timeout_sec} seconds.")


def main():
    parser = argparse.ArgumentParser(description="Send prompt to active Chrome Gemini tab and get response.")
    parser.add_argument("--message", "-m", help="Text message or review prompt.")
    parser.add_argument("--file", "-f", help="Path to file containing text to review.")
    parser.add_argument("--timeout", "-t", type=int, default=180, help="Timeout in seconds.")
    args = parser.parse_args()

    if args.message:
        prompt = args.message
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            prompt = f.read()
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read()
    else:
        prompt = "Review this code for bugs in 2 concise bullets:\ndef is_even(n):\n    return n % 2 == 0"

    try:
        response = send_prompt_and_get_response(prompt, timeout_sec=args.timeout)
        print("\n=== GEMINI NEON REVIEW RESPONSE ===\n")
        print(response)
    except Exception as e:
        sys.stderr.write(f"Execution Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
