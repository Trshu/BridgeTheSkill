"""BridgeTheSkill Alpha user interface."""
import logging
import sqlite3

import streamlit as st

import database
from alpha_analysis import analyze

st.set_page_config(page_title="BridgeTheSkill")
st.title("BridgeTheSkill")
st.write("Choose a career and select the skills you already have.")

try:
    roles = {role["id"]: role for role in database.get_roles()}
    skills = {skill["id"]: skill["name"] for skill in database.get_skills()}
except sqlite3.Error:
    st.error("The catalog could not be opened. Run python init_db.py and restart the app.")
    st.stop()

if not roles or not skills:
    st.error("The catalog is empty. Run python init_db.py and restart the app.")
    st.stop()

with st.form("skills_form"):
    role_id = st.selectbox("Target career", list(roles),
                           format_func=lambda item: roles[item]["title"])
    skill_ids = st.multiselect("Existing skills", list(skills),
                               format_func=skills.__getitem__,
                               help="Leave empty if you have none of the listed skills.")
    submitted = st.form_submit_button("Analyze skills")

if submitted:
    try:
        with st.spinner("Checking your skills and finding courses..."):
            missing, courses, source = analyze(role_id, skill_ids)
    except Exception:
        logging.getLogger(__name__).exception("Skill analysis failed")
        st.error("Analysis could not be completed. Check the application logs for details.")
    else:
        st.subheader("Missing skills")
        if missing:
            st.text(", ".join(missing))
        else:
            st.success("You selected all required skills for this career.")
        st.subheader("Recommended courses")
        if missing:
            st.caption(source)
        if courses:
            for index, course in enumerate(courses, 1):
                st.text(f"{index}. {course['title']}")
                st.text(course["explanation"])
        elif missing:
            st.info("No courses were found for these gaps.")
        else:
            st.info("No gap-based courses are needed.")
