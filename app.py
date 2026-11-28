"""רווקים לכולם — shared availability calendar (Jan–May 2027), Streamlit.

Storage: the backend on our server (server/ravakim_api.py) when st.secrets has
`api_url` + `api_token` (needed on Streamlit Community Cloud, whose disk is wiped
on restart); otherwise a local JSON file, for running on your own machine.
"""
import html
import json
import re
import uuid
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="רווקים לכולם", page_icon="📅", layout="wide")

START, END = date(2027, 1, 1), date(2027, 5, 31)
ALL = [START + timedelta(n) for n in range((END - START).days + 1)]
MONTHS = [(1, "ינואר"), (2, "פברואר"), (3, "מרץ"), (4, "אפריל"), (5, "מאי")]
DOW = ["א׳", "ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳"]
HOLIDAYS = {
    date(2027, 1, 23): "ט״ו בשבט",
    date(2027, 2, 21): "פורים קטן",
    date(2027, 3, 22): "תענית אסתר",
    date(2027, 3, 23): "פורים",
    date(2027, 3, 24): "שושן פורים",
    date(2027, 4, 21): "ערב פסח",
    date(2027, 4, 22): "פסח",
    **{date(2027, 4, d): "חול המועד פסח" for d in range(23, 28)},
    date(2027, 4, 28): "שביעי של פסח",
    date(2027, 5, 4): "יום השואה",
    date(2027, 5, 11): "יום הזיכרון",
    date(2027, 5, 12): "יום העצמאות",
    date(2027, 5, 25): "ל״ג בעומר",
}
PALETTE = ["#e63946", "#fb5607", "#f4a261", "#e9c46a", "#2a9d8f", "#06d6a0", "#00b4d8",
           "#3a86ff", "#4361ee", "#8338ec", "#ff006e", "#ff8fab", "#8d5a3b", "#495057"]


def dow(d):  # Sunday = 0
    return (d.weekday() + 1) % 7


def heb(d, weekday=False):
    s = f"{d.day}.{d.month}"
    return f"{DOW[dow(d)]} {s}" if weekday else s


# ---------------------------------------------------------------- storage
class LocalStore:
    path = Path(__file__).with_name("local_data.json")

    def load(self):
        return json.loads(self.path.read_text("utf-8")) if self.path.exists() else {}

    def save(self, pid, person):
        data = self.load()
        data[pid] = person
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")

    def delete(self, pid):
        data = self.load()
        data.pop(pid, None)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")


class ApiStore:
    """The backend on the server (server/ravakim_api.py), reached with a secret token."""

    def __init__(self, url, token):
        self.url, self.token = url.rstrip("/"), token

    def _call(self, method, path, body=None):
        import urllib.request
        req = urllib.request.Request(
            self.url + path, method=method,
            data=None if body is None else json.dumps(body, ensure_ascii=False).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
                     "User-Agent": "ravakim-streamlit"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read() or b"{}")

    def load(self):
        return self._call("GET", "/people")["people"]

    def save(self, pid, person):
        self._call("PUT", f"/people/{pid}",
                   {"name": person["name"], "color": person["color"], "marks": person["marks"]})

    def delete(self, pid):
        self._call("DELETE", f"/people/{pid}")


@st.cache_resource
def get_store():
    try:
        if "api_url" in st.secrets and "api_token" in st.secrets:
            return ApiStore(st.secrets["api_url"], st.secrets["api_token"])
    except FileNotFoundError:
        pass
    return LocalStore()


@st.cache_data(ttl=15, show_spinner=False)
def load_people():
    return get_store().load()


def save_person(pid, person):
    get_store().save(pid, person)
    load_people.clear()


def delete_person(pid):
    get_store().delete(pid)
    load_people.clear()


# ---------------------------------------------------------------- style
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Secular+One&family=Rubik:wght@400;500;700&display=swap');
.stApp, .stApp * {direction: rtl; font-family: Rubik, system-ui, sans-serif;}
.stApp h1 {font-family: "Secular One", Rubik, sans-serif; font-weight: 400;}
.hero {background:#ff5a4e; color:#fff; border-radius:16px; padding:22px 26px; margin-bottom:14px}
.hero h1 {color:#fff; margin:0 0 4px; font-size:clamp(32px,5vw,50px); line-height:1.05; padding:0}
.hero p {margin:0; font-size:17px}
.months {display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr)); gap:20px}
.month h3 {font-family:"Secular One",Rubik,sans-serif; font-weight:400; margin:0 0 6px; font-size:22px}
.cal {display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:4px}
.dow {text-align:center; font-size:13px; opacity:.65}
.day {min-height:64px; border:1px solid rgba(128,128,128,.25); border-radius:8px; padding:3px 5px;
      display:flex; flex-direction:column; gap:2px; background:rgba(128,128,128,.06)}
.day.free {background:#fff0a3; color:#4a3d00; border-color:transparent}
.day.blank {visibility:hidden}
.day .n {font-weight:700; font-size:15px; line-height:1.1}
.day .hol {font-size:11px; color:#e5383b; font-weight:500; line-height:1.1}
.day .ps {display:flex; flex-wrap:wrap; gap:2px; margin-top:auto}
.day .p {width:15px; height:15px; border-radius:50%; font-size:9px; line-height:15px; text-align:center;
         color:#fff; font-weight:700}
.chip {display:inline-flex; align-items:center; gap:6px; padding:3px 10px; margin:0 0 6px 6px;
       border-radius:999px; border:1px solid rgba(128,128,128,.3); font-size:14px; white-space:nowrap}
.chip.free {background:#fff0a3; color:#4a3d00; border-color:transparent; font-weight:500}
.dot {width:12px; height:12px; border-radius:50%; display:inline-block}
@media (max-width:600px){ .day{min-height:52px; padding:2px} .day .p{width:11px;height:11px;font-size:0} }
</style>
<div class="hero"><h1>רווקים לכולם</h1>
<p>בחרו שם וצבע, וסמנו את הימים שבהם אתם <b>לא</b> יכולים (ינואר–מאי 2027). ימים שכולם פנויים בהם נצבעים בצהוב.</p></div>
""", unsafe_allow_html=True)

people = load_people()
esc = html.escape


def safe_color(c):
    return c if isinstance(c, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", c) else "#888888"


# ---------------------------------------------------------------- identity
qp_me = st.query_params.get("me")
if "me" not in st.session_state:
    st.session_state.me = qp_me if qp_me in people else None
me = st.session_state.me if st.session_state.me in people else None

with st.container(border=True):
    if me:
        p = people[me]
        c1, c2 = st.columns([3, 1])
        c1.markdown(f'מחובר/ת בתור <span class="dot" style="background:{safe_color(p["color"])}"></span> '
                    f'<b>{esc(p["name"])}</b>. שמרו את הקישור של הדף הזה כדי לחזור ישר אליכם.',
                    unsafe_allow_html=True)
        if c2.button("החלפת משתמש", use_container_width=True):
            st.session_state.me = None
            st.query_params.clear()
            st.rerun()
    else:
        st.markdown("**מי את/ה?**")
        names = sorted(people.items(), key=lambda kv: kv[1]["name"])
        t1, t2 = st.tabs(["אני חדש/ה כאן", "כבר נרשמתי"])
        with t1:
            taken = {v["color"] for v in people.values()}
            free_colors = [c for c in PALETTE if c not in taken] or PALETTE
            name = st.text_input("השם שלי", max_chars=24, placeholder="למשל: עדו")
            color = st.color_picker("הצבע שלי", free_colors[0])
            if color in taken:
                st.caption("שימו לב: מישהו אחר כבר בחר את הצבע הזה.")
            if st.button("הצטרפות", type="primary"):
                color = safe_color(color)
                if not name.strip():
                    st.warning("כתבו שם כדי להצטרף.")
                elif any(v["name"] == name.strip() for v in people.values()):
                    st.warning("השם הזה כבר קיים. אם זה את/ה, בחרו בלשונית 'כבר נרשמתי'.")
                else:
                    pid = "p" + uuid.uuid4().hex[:10]
                    save_person(pid, {"name": name.strip(), "color": color, "marks": {}})
                    st.session_state.me = pid
                    st.query_params["me"] = pid
                    st.rerun()
        with t2:
            if names:
                pick = st.selectbox("בחרו את השם שלכם", [k for k, _ in names],
                                    format_func=lambda k: people[k]["name"], index=None,
                                    placeholder="בחירה…")
                if pick and st.button("זה אני"):
                    st.session_state.me = pick
                    st.query_params["me"] = pick
                    st.rerun()
            else:
                st.caption("עוד אף אחד לא נרשם.")

# ---------------------------------------------------------------- calendar (everyone)
busy = {d: [] for d in ALL}
for pid, p in sorted(people.items(), key=lambda kv: kv[1]["name"]):
    for k in p["marks"]:
        try:
            d = date.fromisoformat(k)
        except ValueError:
            continue
        if d in busy:
            busy[d].append(p)

CAL_CSS = """
.rk {direction: rtl; font-family: inherit; user-select: none; -webkit-user-select: none}
.rk .months {display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr)); gap:20px}
.rk h3 {font-family:"Secular One",Rubik,sans-serif; font-weight:400; margin:0 0 6px; font-size:22px}
.rk .cal {display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:4px}
.rk .dow {text-align:center; font-size:13px; opacity:.65}
.rk .day {min-height:64px; border:1px solid rgba(128,128,128,.28); border-radius:8px; padding:3px 5px;
          display:flex; flex-direction:column; gap:2px; background:rgba(128,128,128,.06);
          cursor:pointer; text-align:start; font:inherit; color:inherit; touch-action:manipulation}
.rk .day:hover {border-color: rgba(128,128,128,.7)}
.rk .day:focus-visible {outline:3px solid #3a86ff; outline-offset:1px}
.rk .day.free {background:#fff0a3; color:#4a3d00; border-color:transparent}
.rk .day.mine {box-shadow: inset 0 0 0 3px var(--mc)}
.rk .day.pv-add {box-shadow: inset 0 0 0 3px var(--mc); background: color-mix(in srgb, var(--mc) 22%, transparent)}
.rk .day.pv-del {opacity:.4}
.rk .day.blank {visibility:hidden; cursor:default}
.rk .n {font-weight:700; font-size:15px; line-height:1.1}
.rk .hol {font-size:11px; color:#e5383b; font-weight:500; line-height:1.1}
.rk .ps {display:flex; flex-wrap:wrap; gap:2px; margin-top:auto}
.rk .p {width:15px; height:15px; border-radius:50%; font-size:9px; line-height:15px; text-align:center; color:#fff; font-weight:700}
.rk .msg {margin:0 0 10px; padding:8px 12px; border-radius:8px; background:#ff5a4e; color:#fff; font-weight:500}
.rk .msg:empty {display:none}
@media (max-width:600px){ .rk .day{min-height:52px; padding:2px} .rk .p{width:11px;height:11px;font-size:0} }
"""

CAL_JS = """
const DOW = ['א׳','ב׳','ג׳','ד׳','ה׳','ו׳','ש׳'];
export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  let root = parentElement.querySelector('.rk');
  if (!root) { root = document.createElement('div'); root.className = 'rk'; root.dir = 'rtl'; parentElement.appendChild(root); }
  root.style.setProperty('--mc', data.myColor || '#888');
  root.innerHTML = '';
  const msg = document.createElement('p'); msg.className = 'msg'; root.appendChild(msg);
  const wrap = document.createElement('div'); wrap.className = 'months'; root.appendChild(wrap);
  const cells = {}, order = [];
  for (const m of data.months) {
    const box = document.createElement('div');
    const h = document.createElement('h3'); h.textContent = m.title; box.appendChild(h);
    const grid = document.createElement('div'); grid.className = 'cal';
    for (const d of DOW) { const x = document.createElement('div'); x.className = 'dow'; x.textContent = d; grid.appendChild(x); }
    for (let i = 0; i < m.lead; i++) { const x = document.createElement('div'); x.className = 'day blank'; grid.appendChild(x); }
    for (const day of m.days) {
      const c = document.createElement('button'); c.type = 'button'; c.dataset.d = day.d;
      c.className = 'day' + (day.free ? ' free' : '') + (day.mine ? ' mine' : '');
      const n = document.createElement('span'); n.className = 'n'; n.textContent = day.n; c.appendChild(n);
      if (day.hol) { const t = document.createElement('span'); t.className = 'hol'; t.textContent = day.hol; c.appendChild(t); }
      const ps = document.createElement('span'); ps.className = 'ps';
      for (const p of day.ps) { const b = document.createElement('span'); b.className = 'p'; b.style.background = p.c; b.textContent = p.i; b.title = p.t; ps.appendChild(b); }
      c.appendChild(ps);
      c.title = day.tip; c.setAttribute('aria-label', day.aria); c.setAttribute('aria-pressed', String(day.mine));
      cells[day.d] = c; order.push(day.d); grid.appendChild(c);
    }
    box.appendChild(grid); wrap.appendChild(box);
  }
  const idx = Object.fromEntries(order.map((d, i) => [d, i]));
  let drag = null;
  const preview = () => { for (const d of order) cells[d].classList.remove('pv-add', 'pv-del');
    if (drag) for (const d of drag.set) cells[d].classList.add(drag.mode === 'add' ? 'pv-add' : 'pv-del'); };
  const range = (a, b) => { const [i, j] = [idx[a], idx[b]].sort((x, y) => x - y); return order.slice(i, j + 1); };
  const send = (days, mode) => setTriggerValue('toggle', { days, mode, t: Date.now() });
  root.onpointerdown = (e) => {
    const c = e.target.closest('button.day'); if (!c) return;
    if (!data.canMark) { msg.textContent = 'כדי לסמן, הצטרפו קודם (שם + צבע) בחלק העליון של הדף.'; return; }
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    drag = { mode: c.classList.contains('mine') ? 'del' : 'add', start: c.dataset.d, set: [c.dataset.d], mouse: e.pointerType === 'mouse' };
    if (drag.mouse) e.preventDefault();
    preview();
  };
  root.onpointermove = (e) => {
    if (!drag || !drag.mouse) return;
    const rn = root.getRootNode();
    const el = (rn.elementFromPoint ? rn : document).elementFromPoint(e.clientX, e.clientY);
    const c = el && el.closest ? el.closest('button.day') : null;
    if (c && c.dataset.d) { drag.set = range(drag.start, c.dataset.d); preview(); }
  };
  const up = () => { if (!drag) return; const { set, mode } = drag; drag = null; send(set, mode); };
  const cancel = () => { drag = null; preview(); };
  root.onkeydown = (e) => {
    const c = e.target.closest && e.target.closest('button.day');
    if (!c || !(e.key === 'Enter' || e.key === ' ')) return;
    e.preventDefault();
    if (!data.canMark) { msg.textContent = 'כדי לסמן, הצטרפו קודם (שם + צבע) בחלק העליון של הדף.'; return; }
    send([c.dataset.d], c.classList.contains('mine') ? 'del' : 'add');
  };
  window.addEventListener('pointerup', up);
  window.addEventListener('pointercancel', cancel);
  return () => { window.removeEventListener('pointerup', up); window.removeEventListener('pointercancel', cancel); };
}
"""


@st.cache_resource
def calendar_component():
    return st.components.v2.component("ravakim_calendar", css=CAL_CSS, js=CAL_JS)


my_marks = people[me]["marks"] if me else {}
payload = {"canMark": bool(me), "myColor": safe_color(people[me]["color"]) if me else "#888888", "months": []}
for m, mname in MONTHS:
    days = [d for d in ALL if d.month == m]
    out = []
    for d in days:
        b = busy[d]
        k = d.isoformat()
        who = ", ".join(p["name"] + (f" ({p['marks'][k]})" if p["marks"].get(k) else "") for p in b)
        free = bool(people) and not b
        tip = ("לא יכולים: " + who) if b else ("כולם פנויים" if free else "")
        out.append({"d": k, "n": d.day, "hol": HOLIDAYS.get(d, ""), "free": free, "mine": k in my_marks,
                    "tip": tip, "aria": f"{heb(d, True)}{', ' + HOLIDAYS[d] if d in HOLIDAYS else ''}. {tip}",
                    "ps": [{"i": p["name"][:1], "c": safe_color(p["color"]),
                            "t": p["name"] + (" — " + p["marks"][k] if p["marks"].get(k) else "")} for p in b]})
    payload["months"].append({"title": f"{mname} 2027", "lead": dow(days[0]), "days": out})

if me:
    st.caption("לחצו על יום בלוח כדי לסמן שאתם לא יכולים בו, ושוב כדי לבטל. עם עכבר אפשר לגרור על כמה ימים ברצף. כל שינוי נשמר מיד.")
else:
    st.caption("כדי לסמן ימים, הצטרפו קודם עם שם וצבע.")
res = calendar_component()(data=payload, key="calendar", on_toggle_change=lambda: None)
hit = res.get("toggle") if res else None
if hit and me:
    new = dict(my_marks)
    for k in hit.get("days", []):
        if not isinstance(k, str):
            continue
        try:
            if date.fromisoformat(k) not in busy:
                continue
        except ValueError:
            continue
        if hit.get("mode") == "add":
            new.setdefault(k, "")
        else:
            new.pop(k, None)
    if new != my_marks:
        save_person(me, {**people[me], "marks": new})
        st.rerun()
st.write("")

# ---------------------------------------------------------------- best dates + people
c1, c2 = st.columns(2)
with c1, st.container(border=True):
    st.markdown("**הטווחים הכי טובים**")
    if not people:
        st.caption("יופיע כאן אחרי שמישהו יסמן.")
    else:
        runs, s = [], None
        for i, d in enumerate(ALL):
            if not busy[d] and s is None:
                s = i
            if s is not None and (busy[d] or i == len(ALL) - 1):
                runs.append((s, i if not busy[d] else i - 1))
                s = None
        if runs:
            runs.sort(key=lambda r: (-(r[1] - r[0]), r[0]))
            chips = "".join(
                f'<span class="chip free">{"<bdi>" + heb(ALL[a], True) + "</bdi>" if a == b else "<bdi>" + heb(ALL[a]) + "</bdi> – <bdi>" + heb(ALL[b]) + "</bdi>"}'
                f' · {"יום אחד" if a == b else str(b - a + 1) + " ימים"}</span>' for a, b in runs[:8])
            st.markdown(chips, unsafe_allow_html=True)
        else:
            low = min(len(v) for v in busy.values())
            best = [d for d in ALL if len(busy[d]) == low][:8]
            st.caption(f"אין יום שכולם פנויים. הכי קרוב ({low} לא יכולים):")
            st.markdown("".join(f'<span class="chip">{heb(d, True)}</span>' for d in best), unsafe_allow_html=True)
with c2, st.container(border=True):
    st.markdown("**מי בפנים**")
    if people:
        st.markdown("".join(
            f'<span class="chip"><span class="dot" style="background:{safe_color(p["color"])}"></span>'
            f'{esc(p["name"])} · {len(p["marks"])} ימים</span>'
            for p in sorted(people.values(), key=lambda p: p["name"])), unsafe_allow_html=True)
    else:
        st.caption("עוד אף אחד לא הצטרף. תהיו הראשונים!")

# ---------------------------------------------------------------- my marks
if me:
    p = people[me]
    marks = dict(p["marks"])
    with st.expander("סימון טווח ימים בבת אחת"):
        rng = st.date_input("מתאריך עד תאריך", value=(), min_value=START, max_value=END, format="DD/MM/YYYY")
        a, b = st.columns(2)
        if a.button("סימון כלא פנוי", disabled=len(rng) != 2, use_container_width=True):
            d = rng[0]
            while d <= rng[1]:
                marks.setdefault(d.isoformat(), "")
                d += timedelta(1)
            save_person(me, {**p, "marks": marks})
            st.rerun()
        if b.button("ביטול הסימון בטווח", disabled=len(rng) != 2, use_container_width=True):
            marks = {k: v for k, v in marks.items() if not rng[0] <= date.fromisoformat(k) <= rng[1]}
            save_person(me, {**p, "marks": marks})
            st.rerun()

    if marks:
        with st.expander("הוספת הערה ליום שסימנתי"):
            keys = sorted(marks)
            k = st.selectbox("יום", keys, format_func=lambda k: heb(date.fromisoformat(k), True))
            note = st.text_input("הערה (לא חובה)", value=marks.get(k, ""), max_chars=60,
                                 placeholder="למשל: מילואים", key=f"note_{k}")
            if st.button("שמירת הערה"):
                marks[k] = note.strip()
                save_person(me, {**p, "marks": marks})
                st.rerun()

    with st.expander("הסרת עצמי מהלוח"):
        if st.checkbox("כן, למחוק את השם שלי ואת כל הסימונים"):
            if st.button("הסרה", type="primary"):
                delete_person(me)
                st.session_state.me = None
                st.query_params.clear()
                st.rerun()

# ---------------------------------------------------------------- notes
notes = sorted(((date.fromisoformat(k), p, v) for p in people.values()
                for k, v in p["marks"].items() if v and date.fromisoformat(k) in busy),
               key=lambda t: (t[0], t[1]["name"]))
if notes:
    with st.container(border=True):
        st.markdown("**הערות**")
        st.markdown("<br>".join(
            f'{heb(d, True)} · <span class="dot" style="background:{safe_color(p["color"])}"></span> '
            f'<b>{esc(p["name"])}</b> — {esc(v)}' for d, p, v in notes), unsafe_allow_html=True)

st.caption("חגים מסומנים באדום. הנתונים מתעדכנים כל כמה שניות; רעננו כדי לראות סימונים חדשים של אחרים.")
