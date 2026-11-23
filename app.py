"""רווקים לכולם — shared availability calendar (Jan–Mar 2027), Streamlit.

Storage: a Google Sheet when st.secrets has `gcp_service_account` + `sheet_url`
(needed on Streamlit Community Cloud, whose disk is wiped on restart);
otherwise a local JSON file, for running on your own machine.
"""
import html
import json
import re
import uuid
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="רווקים לכולם", page_icon="📅", layout="wide")

START, END = date(2027, 1, 1), date(2027, 3, 31)
ALL = [START + timedelta(n) for n in range((END - START).days + 1)]
MONTHS = [(1, "ינואר"), (2, "פברואר"), (3, "מרץ")]
DOW = ["א׳", "ב׳", "ג׳", "ד׳", "ה׳", "ו׳", "ש׳"]
HOLIDAYS = {
    date(2027, 1, 23): "ט״ו בשבט",
    date(2027, 2, 21): "פורים קטן",
    date(2027, 3, 22): "תענית אסתר",
    date(2027, 3, 23): "פורים",
    date(2027, 3, 24): "שושן פורים",
}
PALETTE = ["#e63946", "#fb5607", "#f4a261", "#e9c46a", "#2a9d8f", "#06d6a0", "#00b4d8",
           "#3a86ff", "#4361ee", "#8338ec", "#ff006e", "#ff8fab", "#8d5a3b", "#495057"]
HEADER = ["id", "name", "color", "marks", "updated"]


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


class SheetStore:
    def __init__(self):
        import gspread
        gc = gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
        self.ws = gc.open_by_url(st.secrets["sheet_url"]).sheet1
        if self.ws.row_values(1) != HEADER:
            self.ws.update(range_name="A1:E1", values=[HEADER])

    def load(self):
        out = {}
        for r in self.ws.get_all_records(expected_headers=HEADER, numericise_ignore=["all"]):
            try:
                marks = json.loads(r["marks"] or "{}")
            except ValueError:
                marks = {}
            if r["id"]:
                out[str(r["id"])] = {"name": str(r["name"]), "color": r["color"], "marks": marks}
        return out

    def _row(self, pid):
        ids = self.ws.col_values(1)
        return ids.index(pid) + 1 if pid in ids else None

    def save(self, pid, person):
        vals = [pid, person["name"], person["color"],
                json.dumps(person["marks"], ensure_ascii=False), date.today().isoformat()]
        r = self._row(pid)
        if r:
            self.ws.update(range_name=f"A{r}:E{r}", values=[vals])
        else:
            self.ws.append_row(vals, value_input_option="RAW")

    def delete(self, pid):
        r = self._row(pid)
        if r:
            self.ws.delete_rows(r)


@st.cache_resource
def get_store():
    try:
        if "gcp_service_account" in st.secrets and "sheet_url" in st.secrets:
            return SheetStore()
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
<p>בחרו שם וצבע, וסמנו את הימים שבהם אתם <b>לא</b> יכולים (ינואר–מרץ 2027). ימים שכולם פנויים בהם נצבעים בצהוב.</p></div>
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

months_html = []
for m, mname in MONTHS:
    days = [d for d in ALL if d.month == m]
    cells = "".join(f'<div class="dow">{x}</div>' for x in DOW)
    cells += '<div class="day blank"></div>' * dow(days[0])
    for d in days:
        b = busy[d]
        free = bool(people) and not b
        dots = "".join(
            f'<span class="p" style="background:{safe_color(p["color"])}" '
            f'title="{esc(p["name"] + (" — " + p["marks"][d.isoformat()] if p["marks"].get(d.isoformat()) else ""))}">'
            f'{esc(p["name"][:1])}</span>' for p in b)
        hol = f'<span class="hol">{HOLIDAYS[d]}</span>' if d in HOLIDAYS else ""
        cells += f'<div class="day{" free" if free else ""}"><span class="n">{d.day}</span>{hol}<span class="ps">{dots}</span></div>'
    months_html.append(f'<div class="month"><h3>{mname} 2027</h3><div class="cal">{cells}</div></div>')
st.markdown(f'<div class="months">{"".join(months_html)}</div>', unsafe_allow_html=True)
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
                f'<span class="chip free">{heb(ALL[a], True) if a == b else heb(ALL[a]) + " – " + heb(ALL[b])}'
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
    st.subheader("הימים שאני לא יכול/ה")
    st.caption("לחצו על ימים כדי לסמן או לבטל. כל שינוי נשמר מיד.")

    def on_pills(month):
        chosen = set(st.session_state[f"pills_{month}_{me}"] or [])
        new = {k: v for k, v in marks.items() if date.fromisoformat(k).month != month}
        for d in chosen:
            new[d.isoformat()] = marks.get(d.isoformat(), "")
        save_person(me, {**p, "marks": new})

    for m, mname in MONTHS:
        days = [d for d in ALL if d.month == m]
        st.pills(mname, days, selection_mode="multi", key=f"pills_{m}_{me}",
                 default=[d for d in days if d.isoformat() in marks],
                 format_func=lambda d: f"{DOW[dow(d)]} {d.day}", on_change=on_pills, args=(m,))

    with st.expander("סימון טווח ימים בבת אחת"):
        rng = st.date_input("מתאריך עד תאריך", value=(), min_value=START, max_value=END, format="DD/MM/YYYY")
        a, b = st.columns(2)
        if a.button("סימון כלא פנוי", disabled=len(rng) != 2, use_container_width=True):
            d = rng[0]
            while d <= rng[1]:
                marks.setdefault(d.isoformat(), "")
                d += timedelta(1)
            save_person(me, {**p, "marks": marks})
            for m, _ in MONTHS:
                st.session_state.pop(f"pills_{m}_{me}", None)
            st.rerun()
        if b.button("ביטול הסימון בטווח", disabled=len(rng) != 2, use_container_width=True):
            marks = {k: v for k, v in marks.items() if not rng[0] <= date.fromisoformat(k) <= rng[1]}
            save_person(me, {**p, "marks": marks})
            for m, _ in MONTHS:
                st.session_state.pop(f"pills_{m}_{me}", None)
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
