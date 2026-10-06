"""Deterministic story importance and confidence engine for Kaivor News FP016."""
from __future__ import annotations
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import re
from typing import Any

CATEGORY_BASE = {"world":55,"uk":52,"business":52,"technology":48,"science":44,"sport":30,"puzzles":10}
IMPACT_GROUPS = [
 (25,"conflict/security",("war","strike","strikes","drone","missile","attack","troops","military","ceasefire","russia","ukraine","iran","israel","gaza","houthi")),
 (16,"critical infrastructure",("bridge","airport","rail","railway","power","grid","pipeline","port","infrastructure","blackout")),
 (15,"politics/elections",("government","minister","chancellor","president","prime minister","election","parliament","vote","law","policy","resign")),
 (15,"economy/markets",("inflation","interest rate","rates","jobs","employment","recession","gdp","economy","market","markets","bank","tariff","trade")),
 (12,"technology/security",("ai","artificial intelligence","chip","semiconductor","cyber","hack","software","robot","data breach")),
 (8,"science/public health",("study","research","trial","scientists","discovery","climate","vaccine","disease","space","nasa")),
]

def _clean(v:Any)->str: return re.sub(r"\s+"," ",str(v or "")).strip()
def parse_published(v:Any):
    text=_clean(v)
    if not text:return None
    for c in (text,text[:-1]+"+00:00" if text.endswith("Z") else text):
        try:
            d=datetime.fromisoformat(c)
            if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc)
        except ValueError: pass
    try:
        d=parsedate_to_datetime(text)
        if d.tzinfo is None:d=d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except (TypeError,ValueError,IndexError): return None

def _story_text(members): return " ".join(f"{m.get('title','')} {m.get('description','')}" for m in members).lower()
def _impact_signal(text):
    matches=[(w,l) for w,l,ks in IMPACT_GROUPS if any(k in text for k in ks)]
    return max(matches,default=(0,"general news"))
def _recency_bonus(members,now):
    ds=[parse_published(m.get('published')) for m in members]; ds=[d for d in ds if d]
    if not ds:return 0,"publication time unavailable"
    age_seconds=max(0.0, ((now or datetime.now(timezone.utc))-max(ds)).total_seconds()); hours=age_seconds/3600
    if hours<=6:return 8,"reported within the last 6 hours"
    if hours<=24:return 5,"reported within the last 24 hours"
    if hours<=72:return 2,"reported within the last 72 hours"
    return 0,"not among the most recent reports"

def calculate_importance(members, *, now=None, story_status=""):
    if not members:return {"score":0,"label":"Low","reasons":["No reports are available to assess."]}
    text=_story_text(members); category=_clean(members[0].get('category')).lower(); base=CATEGORY_BASE.get(category,40)
    impact_bonus,impact_label=_impact_signal(text)
    sources=int(members[0].get('source_count') or members[0].get('independent_source_count') or 1)
    reports=int(members[0].get('report_count') or max(1,len(members)))
    if sources>=3: coverage_bonus,coverage_reason=12,"coverage spans 3+ independent source groups"
    elif sources==2: coverage_bonus,coverage_reason=8,"coverage spans 2 independent source groups"
    elif reports>1: coverage_bonus,coverage_reason=4,"multiple reports are tracking the same story"
    else: coverage_bonus,coverage_reason=0,"single report"
    recency_bonus,recency_reason=_recency_bonus(members,now); activity_bonus=3 if story_status in {"Developing","Evolving"} else 0
    score=min(100,max(0,base+impact_bonus+coverage_bonus+recency_bonus+activity_bonus)); label="High" if score>=75 else "Medium" if score>=50 else "Low"
    reasons=[f"Category baseline: {category or 'general news'}.",f"Impact signal: {impact_label} (+{impact_bonus}).",f"Coverage signal: {coverage_reason} (+{coverage_bonus}).",f"Recency: {recency_reason} (+{recency_bonus})."]
    if activity_bonus: reasons.append(f"Story status is {story_status.lower()} (+{activity_bonus}).")
    return {"score":score,"label":label,"reasons":reasons}

def calculate_confidence(members):
    if not members:return {"score":0,"label":"Low","reasons":["No reports are available."]}
    sources=int(members[0].get('source_count') or members[0].get('independent_source_count') or 1); reports=int(members[0].get('report_count') or max(1,len(members)))
    if sources>=3: score,label,reason=90,"High","Kaivor has reports from 3 or more independent source groups."
    elif sources==2: score,label,reason=70,"Moderate","Kaivor has reports from 2 independent source groups."
    elif reports>1: score,label,reason=45,"Low","Kaivor has multiple reports, but they come from the same source group."
    else: score,label,reason=30,"Low","Kaivor currently has only one report from one source group."
    return {"score":score,"label":label,"reasons":[reason,"Confidence describes the evidence currently held by Kaivor, not a guarantee that every detail is correct."]}

def build_importance_model(members, *, now=None, story_status=""):
    return {"importance":calculate_importance(members,now=now,story_status=story_status),"confidence_assessment":calculate_confidence(members)}
