#!/usr/bin/env python3
"""極簡雙向留言板 Bridge —— 讓兩台電腦上的 Agent 交換專案意見。

設計原則：只用 Python 標準庫、單一檔案、手動觸發、不做自動互聊。

為什麼要「手動觸發」：如果兩邊 Agent 收到訊息就自動回覆，會變成
A 回 B、B 回 A 的無窮迴圈，燒 token 又不會收斂。所以本工具**只負責收送**，
什麼時候看訊息、要不要回、回多久之後再看，全部由人決定。

用法（其中一台當伺服器，兩邊都用 client 收送）：

    # 1. 挑一台電腦起服務（綁 0.0.0.0 才能被 Radmin VPN 的另一台連到）
    py tools/bridge.py serve

    # 2. 寄訊息
    py tools/bridge.py send --part "§6 OCR" --text "rectify 出來的圖比例不對"

    # 3. 收訊息
    py tools/bridge.py inbox
    py tools/bridge.py inbox --unread

    # 4. 看過之後標記已讀
    py tools/bridge.py ack

    # 隊友那台要指向你的 Radmin IP
    py tools/bridge.py send --server http://26.123.142.162:8791 --from shing \
        --to nok --part "§6 OCR" --text "收到，我改成用 mask 判斷有效區"

環境變數 `BRIDGE_URL` 可省掉每次打 --server。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGE_DIR = os.path.join(PROJ, "shared", "bridge")
MESSAGES_PATH = os.path.join(BRIDGE_DIR, "messages.jsonl")
STATE_PATH = os.path.join(BRIDGE_DIR, "state.json")

DEFAULT_PORT = 8791
DEFAULT_URL = os.environ.get("BRIDGE_URL", f"http://127.0.0.1:{DEFAULT_PORT}")
DEFAULT_PEER = os.environ.get("BRIDGE_PEER", "nok")

# 同一則訊息（同寄件人、同收件人、同內容）在此秒數內重送會被擋下。
# 這是防呆：Agent 若因故重複呼叫 send，不會把留言板洗成一堆重複內容。
DEDUPE_WINDOW_SEC = 300
# 檔案超過此行數就拒絕再寫，避免失控的自動化把硬碟塞滿。
MAX_MESSAGES = 5000

_lock = threading.Lock()


# --------------------------------------------------------------------- 儲存層


def _ensure_dir() -> None:
    os.makedirs(BRIDGE_DIR, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_messages() -> list[dict]:
    """讀回全部訊息。JSONL 壞掉的行（例如中途中斷）直接跳過，不讓整個檔案無法讀。"""
    if not os.path.exists(MESSAGES_PATH):
        return []
    out = []
    with open(MESSAGES_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def append_message(msg: dict) -> None:
    """append 一行 JSON。單次寫入，不需要額外的 lock 檔。"""
    _ensure_dir()
    with open(MESSAGES_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")


def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {"cursors": {}}
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            st = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"cursors": {}}
    st.setdefault("cursors", {})
    return st


def save_state(st: dict) -> None:
    _ensure_dir()
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_PATH)   # 原子替換，避免寫到一半斷電留下半個 JSON


# --------------------------------------------------------------------- 核心邏輯


def _visible_for(msg: dict, peer: str) -> bool:
    """收件人 filter。to 為空或 all 代表廣播，兩邊都看得到。"""
    to = str(msg.get("to", "")).strip()
    if to in ("", "all", "*"):
        return True
    return to == peer


def _received_by(msg: dict, peer: str) -> bool:
    """這則訊息是否落在 peer 的收件匣裡 —— 自己發的不算。

    已讀位置只描述「我收到並看到哪裡」，自己發出去的訊息與這個位置無關，
    所以指標、未讀數、逐則狀態都只用這一條判準。
    """
    if str(msg.get("from", "")).strip() == peer:
        return False
    return _visible_for(msg, peer)


def next_seq(msgs: list[dict]) -> int:
    return max((int(m.get("seq", 0)) for m in msgs), default=0) + 1


def find_duplicate(msgs: list[dict], sender: str, to: str, text: str) -> dict | None:
    """找出時間窗內完全相同的訊息，用來擋重送。"""
    now = time.time()
    for m in reversed(msgs[-40:]):
        if m.get("from") != sender or str(m.get("to", "")) != to:
            continue
        if str(m.get("text", "")).strip() != text.strip():
            continue
        try:
            sent = datetime.fromisoformat(str(m.get("ts"))).timestamp()
        except ValueError:
            continue
        if now - sent <= DEDUPE_WINDOW_SEC:
            return m
    return None


def add_message(sender: str, to: str, part: str, text: str,
                reply_to: int | None = None) -> tuple[bool, dict]:
    """新增一則訊息。回傳 (是否成功, 訊息或錯誤資訊)。"""
    text = (text or "").strip()
    if not text:
        return False, {"error": "text 不可為空"}
    if len(text) > 8000:
        return False, {"error": f"text 太長（{len(text)} 字，上限 8000）"}

    with _lock:
        msgs = load_messages()
        if len(msgs) >= MAX_MESSAGES:
            return False, {"error": f"訊息數已達上限 {MAX_MESSAGES}，請封存或清空 {MESSAGES_PATH}"}

        dup = find_duplicate(msgs, sender, to, text)
        if dup:
            return False, {
                "error": f"與第 {dup['seq']} 則內容完全相同，已擋下（{DEDUPE_WINDOW_SEC} 秒內防重送）",
                "duplicate_of": dup["seq"],
            }

        msg = {
            "seq": next_seq(msgs),
            "ts": _now(),
            "from": sender,
            "to": to or "all",
            "part": (part or "").strip(),
            "text": text,
        }
        if reply_to:
            msg["reply_to"] = int(reply_to)
        append_message(msg)
    return True, msg


def read_inbox(peer: str, only_unread: bool = False, limit: int = 0) -> dict:
    msgs = load_messages()
    cursor = int(load_state()["cursors"].get(peer, 0))
    seen = [m for m in msgs if _visible_for(m, peer)]
    unread = [m for m in seen if int(m.get("seq", 0)) > cursor]
    out = unread if only_unread else seen
    if limit > 0:
        out = out[-limit:]
    return {
        "for": peer,
        "cursor": cursor,
        "total": len(seen),
        "unread_count": len(unread),
        "messages": out,
    }


def ack(peer: str, seq: int | None = None) -> dict:
    with _lock:
        msgs = load_messages()
        visible = [m for m in msgs if _visible_for(m, peer)]
        if seq is None:
            seq = max((int(m.get("seq", 0)) for m in visible), default=0)
        st = load_state()
        cur = max(int(st["cursors"].get(peer, 0)), int(seq))
        st["cursors"][peer] = cur
        save_state(st)
    return {"ok": True, "for": peer, "cursor": cur}


# --------------------------------------------------------------------- HTTP 層


class Handler(BaseHTTPRequestHandler):
    server_version = "Bridge/1.0"

    def log_message(self, fmt, *args):   # 靜音，避免每個請求都洗畫面
        return

    # -- 小工具 --
    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, code: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _query(self) -> dict:
        raw = urllib.parse.urlparse(self.path).query
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}

    def _body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    # -- 路由 --
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        q = self._query()

        if path == "/health":
            return self._send_json(200, {
                "ok": True,
                "messages": len(load_messages()),
                "peer_default": DEFAULT_PEER,
            })

        if path == "/inbox":
            peer = q.get("for") or DEFAULT_PEER
            only_unread = q.get("unread", "") in ("1", "true", "yes")
            try:
                limit = int(q.get("limit", 0))
            except ValueError:
                limit = 0
            return self._send_json(200, read_inbox(peer, only_unread, limit))

        if path in ("/", "/board"):
            return self._send_html(200, render_board())

        return self._send_json(404, {"error": f"未知路徑 {path}"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        data = self._body()

        if path == "/send":
            sender = str(data.get("from") or DEFAULT_PEER).strip()
            to = str(data.get("to") or "all").strip()
            part = str(data.get("part") or "")
            text = str(data.get("text") or "")
            reply_to = data.get("reply_to")
            ok, info = add_message(sender, to, part, text,
                                   int(reply_to) if reply_to else None)
            if not ok:
                return self._send_json(409, {"ok": False, **info})
            print(f"[收到] #{info['seq']} {sender} → {info['to']} "
                  f"[{info['part']}] {info['text'][:60]}")
            return self._send_json(200, {"ok": True, **info})

        if path == "/ack":
            peer = str(data.get("for") or DEFAULT_PEER).strip()
            seq = data.get("seq")
            return self._send_json(200, ack(peer, int(seq) if seq is not None else None))

        return self._send_json(404, {"error": f"未知路徑 {path}"})


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _board_peers(msgs: list[dict], cursors: dict) -> list[str]:
    """頁面上要追蹤已讀狀態的身分：有 cursor 的，加上任何出現過的具名收件人。"""
    peers = set(cursors)
    for m in msgs:
        to = str(m.get("to", "")).strip()
        if to not in ("", "all", "*"):
            peers.add(to)
    return sorted(peers)


def render_board() -> str:
    """給人看的留言板頁面。Agent 不需要它，但肉眼掃一遍比讀 JSON 快。

    已讀狀態的來源是 state.json 的 cursors（就是 ack 推進的那個數字），
    所以頁面顯示的一定和 `inbox --unread` 撈到的一致，不是另外猜的。
    """
    msgs = load_messages()
    cursors = {k: int(v) for k, v in load_state()["cursors"].items()}
    peers = _board_peers(msgs, cursors)
    shown = msgs[-200:]

    # 每個身分的未讀張數（與 read_inbox 同一條判準；自己發的不算）
    chips = []
    for p in peers:
        cur = cursors.get(p, 0)
        unread = sum(1 for m in msgs
                     if _received_by(m, p) and int(m.get("seq", 0)) > cur)
        state = "ok" if unread == 0 else "new"
        chips.append(
            f"<span class='chip {state}'>{_esc(p)}"
            f"<b>已讀到 #{cur}</b>"
            f"<span class='chip-sub'>{'全部已讀' if unread == 0 else f'{unread} 則未讀'}</span>"
            f"</span>")
    chips_html = "".join(chips) or "<span class='chip'>（尚無已讀紀錄）</span>"

    NCOL = 7
    rows: list[str] = []
    # 指標要落在「該身分收到的訊息」的邊界上（上面未讀、下面已讀），
    # 但緊鄰在錨點上方、由他自己發出的訊息要一併跳過 ——
    # 否則他自己的訊息會壓在自己的指針上面，看起來像他沒讀自己的訊息。
    rev = list(reversed(shown))
    insert_at: dict[str, int] = {}
    for p in peers:
        cur = cursors.get(p, 0)
        idx = None
        for i, m in enumerate(rev):
            if _received_by(m, p) and int(m.get("seq", 0)) <= cur:
                idx = i
                break
        if idx is None:
            insert_at[p] = len(rev)          # 沒有已讀紀錄 → 落在表格最底
            continue
        j = idx
        while j - 1 >= 0 and str(rev[j - 1].get("from", "")).strip() == p:
            j -= 1                            # 跳過自己發的那一串
        insert_at[p] = j

    pending = {p: True for p in peers}

    for pos, m in enumerate(rev):
        seq = int(m.get("seq", 0))

        boundary = [p for p in peers if pending[p] and insert_at[p] == pos]
        if boundary:
            for p in boundary:
                pending[p] = False
            labels = "、".join(
                f"{_esc(p)} 已讀到 #{cursors.get(p, 0)}" for p in boundary)
            rows.append(
                f"<tr class='ptr'><td colspan={NCOL}>▲ 已讀指標 —— {labels}"
                f"（此線以上<b>寄給</b>該身分的訊息為未讀；他自己發的不計）</td></tr>")

        recipients = [p for p in peers if _received_by(m, p)]
        unread_for = [p for p in recipients if seq > cursors.get(p, 0)]
        if recipients:
            badges = "".join(
                f"<span class='badge {'ok' if seq <= cursors.get(p, 0) else 'new'}'>"
                f"{_esc(p)} {'已讀' if seq <= cursors.get(p, 0) else '未讀'}</span>"
                for p in recipients)
        else:
            badges = "<span class='badge self'>本方發出</span>"

        reply = (f"<div class='reply'>↳ 回覆 #{m['reply_to']}</div>"
                 if m.get("reply_to") else "")
        rows.append(
                    f"<tr{' class=unread' if unread_for else ''}><td class='seq'>{seq}</td>"
            f"<td>{_esc(m.get('from'))}</td>"
            f"<td>{_esc(m.get('to'))}</td>"
            f"<td>{_esc(m.get('part'))}</td>"
            f"<td class='st'>{badges}</td>"
            f"<td class='t'>{_esc(m.get('text')).replace(chr(10), '<br>')}{reply}</td>"
            f"<td class='ts'>{_esc(str(m.get('ts'))[:19])}</td></tr>")

    for p in peers:            # 沒有更舊的已讀訊息時，指標落在表格最底
        if pending[p]:
            cur = cursors.get(p, 0)
            rows.append(
                f"<tr class='ptr'><td colspan={NCOL}>▲ 已讀指標 —— {_esc(p)} 已讀到 #{cur}"
                f"（以下沒有更舊的訊息）</td></tr>")

    body = "\n".join(rows) or f"<tr><td colspan={NCOL}>（尚無訊息）</td></tr>"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Bridge 留言板</title>
<style>
 body{{font-family:system-ui,-apple-system,"Microsoft JhengHei",sans-serif;
      margin:24px;background:#fafafa;color:#222}}
 h1{{font-size:18px;margin:0 0 8px}} .sub{{color:#666;font-size:13px;margin-bottom:12px}}
 .chips{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}}
 .chip{{display:inline-flex;align-items:baseline;gap:6px;padding:6px 10px;
       border-radius:14px;background:#eef1f4;font-size:12px;color:#445}}
 .chip b{{font-size:12px}} .chip.ok{{background:#e3f4f0;color:#1f7a6d}}
 .chip.new{{background:#fdf0dd;color:#a86a12}}
 .chip-sub{{color:#7a8794;font-size:11px}}
 table{{border-collapse:collapse;width:100%;background:#fff;
       box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:13px}}
 th,td{{padding:8px 10px;border-bottom:1px solid #eee;vertical-align:top;text-align:left}}
 th{{background:#f0f0f3;font-weight:600;position:sticky;top:0;z-index:1}}
 td.seq{{color:#889;font-variant-numeric:tabular-nums;white-space:nowrap}}
 td.t{{max-width:620px;white-space:pre-wrap}} td.ts{{color:#999;font-size:12px;white-space:nowrap}}
 td.st{{white-space:nowrap}}
 .badge{{display:inline-block;margin:1px 3px 1px 0;padding:1px 7px;border-radius:9px;
        font-size:11px;border:1px solid transparent}}
 .badge.ok{{background:#e3f4f0;color:#1f7a6d;border-color:#bfe4dc}}
 .badge.new{{background:#fdf0dd;color:#a86a12;border-color:#f0d3a0;font-weight:600}}
 .badge.self{{background:#f2f2f5;color:#8a8f99;border-color:#e2e4ea}}
 tr.unread td{{background:#fffdf7}}
 tr.unread td.seq{{box-shadow:inset 3px 0 0 #E9A13B}}
 tr.ptr td{{background:#f6f8fa;color:#33658A;font-size:11.5px;
           border-top:2px dashed #c9d4de;border-bottom:2px dashed #c9d4de;
           padding:5px 10px;letter-spacing:.02em}}
 .reply{{color:#94a3ab;font-size:11px;margin-top:4px}}
 .legend{{color:#7a8794;font-size:12px;margin:12px 0 0}}
</style></head><body>
<h1>Bridge 留言板</h1>
<div class="sub">共 {len(msgs)} 則訊息（顯示最近 {min(len(msgs), 200)} 則，最新的在最上面）</div>
<div class="chips">{chips_html}</div>
<table><thead><tr><th>#</th><th>From</th><th>To</th><th>Part</th><th>已讀狀態</th>
<th>內容</th><th>時間</th></tr></thead>
<tbody>{body}</tbody></table>
<div class="legend">已讀狀態取自 <code>state.json</code> 的 cursors，與
<code>bridge.py inbox --unread</code> 用的是同一個數字；
<code>bridge.py ack</code> 之後重新載入本頁即可看到指標移動。</div>
</body></html>"""


def run_server(host: str, port: int) -> None:
    _ensure_dir()
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    msgs = load_messages()
    print(f"Bridge 已啟動：http://{host}:{port}")
    print(f"留言板頁面   ：http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}/")
    print(f"訊息檔       ：{MESSAGES_PATH}（目前 {len(msgs)} 則）")
    print(f"預設身分     ：{DEFAULT_PEER}（用 --from 或環境變數 BRIDGE_PEER 改）")
    if host == "0.0.0.0":
        print("\n隊友那台請用你的 Radmin VPN IP 連：")
        print(f"    py tools/bridge.py inbox --server http://<你的RadminIP>:{port}")
    print("\n按 Ctrl+C 停止。")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()


# --------------------------------------------------------------------- client


def _request(url: str, method: str = "GET", payload: dict | None = None,
             timeout: float = 10.0) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"ok": False, "error": f"HTTP {e.code}"}


def _fmt_msgs(res: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return
    msgs = res.get("messages", [])
    print(f"── {res.get('for')} 的收件匣 ── 共 {res.get('total', 0)} 則，"
          f"未讀 {res.get('unread_count', 0)} 則（cursor={res.get('cursor')}）")
    if not msgs:
        print("（沒有訊息）")
        return
    cursor = int(res.get("cursor", 0))
    for m in msgs:
        mark = "●" if int(m.get("seq", 0)) > cursor else " "
        part = f"[{m['part']}]" if m.get("part") else ""
        print(f"\n{mark} #{m.get('seq')}  {m.get('ts', '')[:19]}  "
              f"{m.get('from')} → {m.get('to')}  {part}")
        for line in str(m.get("text", "")).splitlines():
            print(f"    {line}")
    if res.get("unread_count"):
        print(f"\n（● 表示未讀。看完用：py tools/bridge.py ack）")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    ap = argparse.ArgumentParser(
        description="極簡雙向留言板 Bridge（Radmin VPN 上用）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_serve = sub.add_parser("serve", help="啟動伺服器（挑一台電腦跑就好）")
    p_serve.add_argument("--host", default="0.0.0.0", help="綁定位址，預設 0.0.0.0")
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT)

    p_send = sub.add_parser("send", help="寄一則訊息")
    p_send.add_argument("--text", required=True)
    p_send.add_argument("--part", default="", help="負責的部分，例如 '§6 OCR'")
    p_send.add_argument("--to", default="all", help="收件人，預設 all（兩邊都看得到）")
    p_send.add_argument("--from", dest="sender", default=DEFAULT_PEER)
    p_send.add_argument("--reply-to", type=int, default=None, help="回覆第幾則")
    p_send.add_argument("--server", default=DEFAULT_URL)

    for name, help_text in (("inbox", "收訊息"), ("ack", "標記已讀")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--for", dest="peer", default=DEFAULT_PEER, help="以自己的身分收")
        p.add_argument("--server", default=DEFAULT_URL)
        if name == "inbox":
            p.add_argument("--unread", action="store_true", help="只看未讀")
            p.add_argument("--limit", type=int, default=0, help="只顯示最後 N 則")
            p.add_argument("--json", action="store_true", help="輸出原始 JSON")
        else:
            p.add_argument("--seq", type=int, default=None, help="標記到第幾則，預設全部")

    p_stat = sub.add_parser("status", help="檢查伺服器是否活著")
    p_stat.add_argument("--server", default=DEFAULT_URL)

    args = ap.parse_args()

    if args.cmd == "serve":
        run_server(args.host, args.port)
        return

    base = args.server.rstrip("/")

    if args.cmd == "send":
        res = _request(f"{base}/send", "POST", {
            "from": args.sender, "to": args.to,
            "part": args.part, "text": args.text,
            "reply_to": args.reply_to,
        })
        if res.get("ok"):
            print(f"已寄出 #{res['seq']}：{args.sender} → {args.to}")
            if args.part:
                print(f"  部分：{args.part}")
        else:
            print(f"寄送失敗：{res.get('error')}")
            sys.exit(1)

    elif args.cmd == "inbox":
        qs = urllib.parse.urlencode({
            "for": args.peer,
            "unread": "1" if args.unread else "0",
            "limit": args.limit,
        })
        res = _request(f"{base}/inbox?{qs}")
        if "messages" not in res:
            print(f"收信失敗：{res.get('error', res)}")
            sys.exit(1)
        _fmt_msgs(res, args.json)

    elif args.cmd == "ack":
        res = _request(f"{base}/ack", "POST", {"for": args.peer, "seq": args.seq})
        if res.get("ok"):
            print(f"{args.peer} 的已讀位置推進到 #{res['cursor']}")
        else:
            print(f"失敗：{res.get('error')}")
            sys.exit(1)

    elif args.cmd == "status":
        res = _request(f"{base}/health")
        if res.get("ok"):
            print(f"伺服器正常：{base}（目前 {res.get('messages', 0)} 則訊息）")
        else:
            print(f"連不上 {base}：{res.get('error', res)}")
            sys.exit(1)


if __name__ == "__main__":
    main()