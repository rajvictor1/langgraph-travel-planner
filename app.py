from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from travel_agent.graph import build_graph
from travel_agent.models import TripRequest
from travel_agent.parser import parse_with_openai

load_dotenv()
st.set_page_config(page_title="Atlas · Transparent travel planning", page_icon="✦", layout="wide")

st.markdown("""
<style>
  :root { color-scheme: dark; --bg:#080a0c; --surface:#111417; --surface-2:#171b1f; --line:rgba(255,255,255,.09); --text:#f3f1ea; --muted:#9a9da2; --accent:#b69a7d; --success:#85d89a; }
  .stApp { background:var(--bg); color:var(--text); }
  [data-testid="stSidebar"] { background:var(--surface); border-right:1px solid var(--line); }
  [data-testid="stSidebar"] > div { background:var(--surface); }
  .block-container { max-width:1180px; padding-top:2.25rem; padding-bottom:4rem; }
  h1, h2, h3, h4 { color:var(--text)!important; letter-spacing:-.035em; }
  p, label, [data-testid="stCaptionContainer"] { color:var(--muted); }
  .atlas-brand { display:flex; align-items:center; gap:10px; margin-bottom:30px; }
  .atlas-mark { width:30px; height:30px; display:grid; place-items:center; background:var(--accent); color:#080a0c; border-radius:8px; font-weight:800; }
  .atlas-name { font-size:.76rem; font-weight:700; letter-spacing:.13em; text-transform:uppercase; color:var(--text); }
  .lab-pill { margin-left:4px; padding:4px 8px; border:1px solid var(--line); border-radius:6px; color:var(--muted); font-size:.64rem; letter-spacing:.11em; text-transform:uppercase; }
  .eyebrow { color:var(--accent); font-size:.7rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }
  .hero { font-size:clamp(2.8rem,6vw,5.1rem); line-height:.96; font-weight:650; letter-spacing:-.06em; margin:.65rem 0 1.25rem; color:var(--text); }
  .hero span { color:var(--muted); }
  .sub { color:var(--muted); font-size:1rem; line-height:1.65; max-width:690px; margin-bottom:2rem; }
  div[data-testid="stMetric"] { background:var(--surface); border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:18px 20px; }
  div[data-testid="stMetric"]:first-child { border-left:1px solid var(--line); border-radius:16px 0 0 16px; }
  div[data-testid="stMetric"]:last-child { border-right:1px solid var(--line); border-radius:0 16px 16px 0; }
  [data-testid="stMetricLabel"] { color:var(--muted); text-transform:uppercase; letter-spacing:.09em; font-size:.68rem; }
  [data-testid="stMetricValue"] { color:var(--text); font-weight:600; }
  div[data-testid="stStatusWidget"], [data-testid="stExpander"] { background:var(--surface); border:1px solid var(--line); border-radius:14px; }
  [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stNumberInput"] input, [data-baseweb="select"] > div { background:var(--surface-2)!important; border-color:var(--line)!important; color:var(--text)!important; border-radius:10px!important; }
  .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background:var(--accent); color:#080a0c; border:0; border-radius:11px; font-weight:700; min-height:44px; }
  .stButton > button:not([kind="primary"]) { background:var(--surface); color:var(--text); border:1px solid var(--line); border-radius:11px; }
  [data-testid="stToggle"] { background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:10px 14px; width:max-content; }
  hr { border-color:var(--line)!important; }
  .mock-note { color:var(--muted); font-size:.72rem; margin-top:24px; padding-top:16px; border-top:1px solid var(--line); }
  @media (max-width: 760px) { .block-container { padding:1.5rem 1rem 3rem; } .hero{font-size:2.65rem;} div[data-testid="stHorizontalBlock"]{gap:.65rem;} }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def graph():
    conn = sqlite3.connect(Path("travel_agent.db"), check_same_thread=False)
    return build_graph(SqliteSaver(conn))


def csv_list(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def render_plan(state: dict):
    plan = state.get("selected_plan", {})
    costs = plan.get("costs", {})
    if not plan:
        return
    st.subheader("Your proposed trip")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", f"{costs.get('currency', 'INR')} {costs.get('total', 0):,.0f}")
    c2.metric("Planning attempt", f"{state.get('planning_attempt', 1)} of 3")
    c3.metric("Nights", plan.get("nights", 0))
    c4.metric("Status", state.get("status", "—").replace("_", " ").title())
    flight, stay = plan.get("flight"), plan.get("stay")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Flight")
        if flight:
            st.write(f"**{flight['airline']} · {flight['id']}**")
            st.caption(f"{flight['origin']} → {flight['destination']} · {flight['stops']} stop(s) · {flight['class']}")
        else:
            st.warning("No matching flight")
    with right:
        st.markdown("#### Stay")
        if stay:
            st.write(f"**{stay['name']}**")
            st.caption(f"{stay['style'].replace('_', ' ').title()} · {stay['rating']} rating · {costs.get('currency', 'INR')} {stay['nightly']:,.0f}/night")
        else:
            st.warning("No matching stay")
    st.markdown("#### Things to do")
    if plan.get("activities"):
        st.write(" · ".join(a["name"] for a in plan["activities"]))
    else:
        st.caption("No matching activities")
    with st.expander("Cost breakdown"):
        st.write({k: f"{costs.get('currency', 'INR')} {v:,.0f}" for k, v in costs.items() if k not in {"total", "currency"}})


def render_audit(events: list[dict]):
    for item in events:
        with st.status(f"{item['node'].replace('_', ' ').title()} · {item['message']}", state="complete", expanded=False):
            st.caption(item["time"])
            if item.get("details"):
                st.json(item["details"])


def interrupt_payload(state: dict) -> dict:
    interrupts = state.get("__interrupt__", ())
    if not interrupts:
        return {}
    first = interrupts[0]
    return first.value if hasattr(first, "value") else first


if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "current_state" not in st.session_state:
    st.session_state.current_state = None

st.markdown('<div class="atlas-brand"><div class="atlas-mark">A</div><div class="atlas-name">Atlas</div><div class="lab-pill">LangGraph Lab</div></div>', unsafe_allow_html=True)
st.markdown('<div class="eyebrow">Transparent travel planning</div>', unsafe_allow_html=True)
st.markdown('<div class="hero">Plan the trip.<br><span>See every decision.</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Build a budget-aware itinerary, inspect every LangGraph node, and remain in control at the approval checkpoint.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Trip requirements")
    prompt = st.text_area("Describe your trip", "Plan a four-day Goa trip from Delhi for two people under ₹60,000. We like beaches and food.", height=120)
    origin = st.text_input("Departure", "Delhi")
    alternatives = st.text_input("Alternative departures", "Jaipur")
    destination = st.text_input("Destination", "Goa")
    start_date = st.date_input("Start date")
    duration = st.number_input("Duration (days)", 1, 30, 4)
    travellers = st.number_input("Travellers", 1, 12, 2)
    budget = st.number_input("Total budget (INR)", 1000, 10000000, 60000, step=1000)
    flight_class = st.selectbox("Flight class", ["economy", "business"])
    flight_type = st.selectbox("Flight type", ["any", "nonstop", "one_stop"])
    max_layover = st.slider("Maximum layover (hours)", 0.0, 24.0, 4.0, .5)
    stay_style = st.selectbox("Stay style", ["hotel", "luxury", "hostel", "airbnb", "room_share", "any"])
    activities = st.text_input("Interests", "beach, food")
    date_flex = st.slider("Date flexibility (days)", 0, 5, 2)
    extension = st.slider("Trip extension allowed (days)", 0, 3, 0)
    run = st.button("Create my plan", type="primary", use_container_width=True)

show_sherlock = st.toggle("Sherlock mode", value=False, help="Reveal the structured LangGraph execution timeline.")

if run:
    editable = TripRequest(
        raw_request=prompt, origin=origin, alternative_origins=csv_list(alternatives), destination=destination,
        start_date=start_date.isoformat(), duration_days=duration, travellers=travellers, budget=budget,
        flight_class=flight_class, flight_type=flight_type, max_layover_hours=max_layover,
        stay_style=stay_style, activities=csv_list(activities), date_flex_days=date_flex, extension_days=extension,
    )
    try:
        request = parse_with_openai(prompt, editable)
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        result = graph().invoke({"request": request.model_dump(), "planning_attempt": 1, "audit_events": []}, config)
        st.session_state.current_state = result
    except Exception as exc:
        st.error(f"The planner could not start: {exc}")

state = st.session_state.current_state
if not show_sherlock:
    if not state:
        st.info("Enter your trip requirements and select **Create my plan**.")
    else:
        render_plan(state)
        if "__interrupt__" in state:
            payload = interrupt_payload(state)
            if payload.get("type") == "missing_information":
                st.subheader("A few details are missing")
                with st.form("missing-details"):
                    supplied = {}
                    for field in payload.get("missing_fields", []):
                        label = field.replace("_", " ").title()
                        supplied[field] = st.number_input(label, min_value=1.0) if field in {"budget", "duration_days", "travellers"} else st.text_input(label)
                    if st.form_submit_button("Continue planning", type="primary"):
                        config = {"configurable": {"thread_id": st.session_state.thread_id}}
                        st.session_state.current_state = graph().invoke(Command(resume=supplied), config)
                        st.rerun()
            else:
                st.divider()
                st.subheader("Your decision")
                feedback = st.text_input("Change request", placeholder="For example: Make the hotel cheaper, but keep the nonstop flight")
                approve, revise = st.columns(2)
                if approve.button("Approve itinerary", type="primary", use_container_width=True):
                    config = {"configurable": {"thread_id": st.session_state.thread_id}}
                    st.session_state.current_state = graph().invoke(Command(resume={"approved": True}), config)
                    st.rerun()
                if revise.button("Revise itinerary", use_container_width=True, disabled=not feedback.strip()):
                    config = {"configurable": {"thread_id": st.session_state.thread_id}}
                    st.session_state.current_state = graph().invoke(Command(resume={"approved": False, "feedback": feedback}), config)
                    st.rerun()
        elif state.get("status") == "approved":
            st.success("Itinerary approved. No booking or payment has been made.")
        elif state.get("status") in {"no_match", "not_approved"}:
            st.warning("The planner reached the three-attempt limit. Review the audit log and relax a constraint to start a new trip.")

else:
    st.subheader("Structured audit")
    st.caption("Shows node activity, inputs, outputs and routing reasons—not private model reasoning.")
    if state:
        render_audit(state.get("audit_events", []))
    else:
        st.info("Audit events will appear after a planning run.")

st.markdown('<div class="mock-note">MOCK INVENTORY · Illustrative pricing only · No reservation or payment is made.</div>', unsafe_allow_html=True)
