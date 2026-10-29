import json
from pathlib import Path

import pandas as pd
import streamlit as st

APP_TITLE = "뇌졸중 예측 실습실"
APP_ICON = "🧠"
DATA_URL = "https://raw.githubusercontent.com/maxhome2022-rgb/data/refs/heads/main/stroke.csv"

# 기록은 main.py와 같은 위치의 '내_기록' 폴더에 저장됩니다.
RECORD_DIR = Path(__file__).parent / "내_기록"
RECORD_FILE = RECORD_DIR / "데이터_소개_기록.json"

# 브라우저 탭 제목과 아이콘 (다른 streamlit 명령보다 먼저 호출해야 합니다)
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")


# ---------- 데이터 / 기록 불러오기·저장 ----------
@st.cache_data(show_spinner="데이터를 불러오는 중입니다...")
def load_data() -> pd.DataFrame:
    return pd.read_csv(DATA_URL, encoding="utf-8")


def load_record() -> dict:
    """저장된 우리말 뜻과 출처를 불러옵니다. 파일이 없거나 깨졌으면 빈 기록을 돌려줍니다."""
    empty = {"meanings": {}, "source": ""}
    if not RECORD_FILE.exists():
        return empty
    try:
        data = json.loads(RECORD_FILE.read_text(encoding="utf-8"))
        return {
            "meanings": dict(data.get("meanings", {})),
            "source": str(data.get("source", "")),
        }
    except (OSError, ValueError):
        return empty


def save_record(record: dict) -> bool:
    try:
        RECORD_DIR.mkdir(parents=True, exist_ok=True)
        RECORD_FILE.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True
    except OSError:
        return False


def describe_values(series: pd.Series) -> str:
    """열의 값 종류를 짧은 글로 설명합니다."""
    values = series.dropna()
    if values.empty:
        return "값 없음"
    kinds = values.unique()
    if series.dtype == "object" or len(kinds) <= 10:
        shown = sorted(kinds, key=str)
        return ", ".join(str(v) for v in shown)
    low, high = values.min(), values.max()
    return f"숫자 ({low:g} ~ {high:g}), {len(kinds)}가지"


def number_card(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div style="border:1px solid rgba(128,128,128,0.35); border-radius:14px;
                    padding:22px 16px; text-align:center;">
            <div style="font-size:1rem; opacity:0.75;">{label}</div>
            <div style="font-size:2.6rem; font-weight:700; line-height:1.3;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- 화면 ----------
st.title(f"{APP_ICON} {APP_TITLE}")
st.header("1. 데이터 소개")
st.write("이 앱에서 사용할 뇌졸중 데이터가 어떤 데이터인지 먼저 살펴봅니다.")

try:
    df = load_data()
except Exception as e:  # 네트워크 오류 등
    st.error(f"데이터를 불러오지 못했습니다. 인터넷 연결과 주소를 확인해 주세요.\n\n{e}")
    st.stop()

# 처음 한 번만 저장된 기록을 불러와 화면 상태에 넣어 둡니다 (새로고침하면 다시 불러옴).
if "record" not in st.session_state:
    st.session_state.record = load_record()
    saved = st.session_state.record["meanings"]
    st.session_state.base_table = pd.DataFrame(
        {
            "열 이름": list(df.columns),
            "우리말 뜻": [saved.get(c, "") for c in df.columns],
            "값의 종류": [describe_values(df[c]) for c in df.columns],
            "빈 값 개수": [int(df[c].isna().sum()) for c in df.columns],
        }
    )

# 1) 큰 숫자 카드 네 개
total = len(df)
stroke_count = int((df["stroke"] == 1).sum())
ratio = stroke_count / total * 100 if total else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    number_card("전체 사람 수", f"{total:,}명")
with c2:
    number_card("열 개수", f"{df.shape[1]}개")
with c3:
    number_card("stroke가 1인 사람 수", f"{stroke_count:,}명")
with c4:
    number_card("stroke가 1인 비율", f"{ratio:.2f}%")

# 2) 열 설명 표 (우리말 뜻 칸만 직접 입력)
st.subheader("열 설명 표")
st.caption("‘우리말 뜻’ 칸을 눌러 교재를 보고 직접 적어 보세요. 적은 내용은 자동으로 저장됩니다.")
edited = st.data_editor(
    st.session_state.base_table,
    key="meaning_editor",
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    disabled=["열 이름", "값의 종류", "빈 값 개수"],
    column_config={
        "열 이름": st.column_config.TextColumn("열 이름"),
        "우리말 뜻": st.column_config.TextColumn("우리말 뜻", help="교재를 보고 직접 적어 주세요."),
        "값의 종류": st.column_config.TextColumn("값의 종류", width="large"),
        "빈 값 개수": st.column_config.NumberColumn("빈 값 개수"),
    },
)

# 3) 처음 다섯 줄
st.subheader("데이터 처음 다섯 줄")
st.dataframe(df.head(5), use_container_width=True)

# 4) 데이터 출처
st.subheader("데이터 출처")
source_text = st.text_area(
    "출처",
    value=st.session_state.record["source"],
    height=120,
    placeholder="교재에 나온 데이터 출처를 여기에 적어 주세요. (입력 후 칸 밖을 누르면 저장됩니다)",
    label_visibility="collapsed",
)

# ---------- 바뀐 내용이 있으면 json 파일에 저장 ----------
new_record = {
    "meanings": {
        row["열 이름"]: (row["우리말 뜻"] or "")
        for _, row in edited.iterrows()
        if (row["우리말 뜻"] or "").strip()
    },
    "source": source_text,
}

if new_record != st.session_state.record:
    if save_record(new_record):
        st.session_state.record = new_record
        st.toast("내_기록 폴더에 저장했어요.", icon="💾")
    else:
        st.error("기록을 저장하지 못했습니다. 폴더 쓰기 권한을 확인해 주세요.")
