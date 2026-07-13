import streamlit as st
import csv
import io
import re
import pandas as pd

st.set_page_config(
    page_title="Resume Screener",
    page_icon="🔍",
    layout="wide"
)

ALL_SKILLS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "Ruby", "PHP",
    "React", "Vue.js", "Angular", "Next.js", "HTML", "CSS",
    "Node.js", "Django", "FastAPI", "Flask", "Spring Boot",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite",
    "REST APIs", "GraphQL",
    "AWS", "GCP", "Azure",
    "Docker", "Kubernetes", "CI/CD",
    "Machine learning", "TensorFlow", "PyTorch", "scikit-learn",
    "Git", "Linux", "Agile", "Scrum",
]

SAMPLE_RESUMES = """--- CANDIDATE: Priya Sharma ---
Experience: 5 years
Current Role: Senior Engineer at Flipkart
Skills: Python, Django, FastAPI, React, PostgreSQL, Docker, AWS, REST APIs, GraphQL, TypeScript
Education: B.Tech Computer Science, IIT Delhi
Notable: Led microservices migration cutting latency by 40%. FastAPI open source contributor. Mentored 3 junior engineers.

--- CANDIDATE: Arjun Mehta ---
Experience: 3 years
Current Role: Frontend Developer at Zomato
Skills: JavaScript, TypeScript, React, Vue.js, Node.js, MongoDB, REST APIs
Education: B.E. Computer Science, VIT Vellore
Notable: Built real time order tracking UI for 2M plus daily users. No Python or cloud experience.

--- CANDIDATE: Sneha Kapoor ---
Experience: 6 years
Current Role: Full Stack Engineer at Razorpay
Skills: Python, Node.js, React, PostgreSQL, AWS, Docker, CI/CD, REST APIs, GraphQL, TypeScript
Education: M.Tech Software Engineering, BITS Pilani
Notable: Shipped payment gateway integrations at scale. AWS Certified. Previously at two startups.

--- CANDIDATE: Rahul Verma ---
Experience: 2 years
Current Role: Junior Developer at TCS
Skills: Java, Spring Boot, MySQL, JavaScript
Education: B.Tech Information Technology, Pune University
Notable: Good academic record. Limited experience with cloud and modern JS frameworks.

--- CANDIDATE: Nisha Patel ---
Experience: 4 years
Current Role: Backend Engineer at Swiggy
Skills: Python, FastAPI, PostgreSQL, Redis, Docker, GCP, REST APIs
Education: B.Tech Computer Science, NIT Trichy
Notable: Built order system handling 100k plus orders per day. ML side projects with scikit-learn."""


def parse_resumes(raw_text):
    candidates = []
    blocks = raw_text.strip().split("--- CANDIDATE:")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        name = lines[0].replace("---", "").strip()
        if not name:
            continue
        skills    = []
        years     = 0
        role      = ""
        education = ""
        notes     = ""
        for line in lines[1:]:
            low = line.lower()
            if low.startswith("skills:"):
                raw = line.split(":", 1)[1]
                skills = [s.strip() for s in raw.split(",") if s.strip()]
            elif low.startswith("experience:"):
                nums = re.findall(r'\d+', line)
                years = int(nums[0]) if nums else 0
            elif low.startswith("current role:"):
                role = line.split(":", 1)[1].strip()
            elif low.startswith("education:"):
                education = line.split(":", 1)[1].strip()
            elif low.startswith("notable:"):
                notes = line.split(":", 1)[1].strip()
        candidates.append({
            "name":         name,
            "current_role": role or "Not specified",
            "years_exp":    years,
            "skills":       skills,
            "education":    education,
            "notes":        notes,
        })
    return candidates


def score_candidate(candidate, required_skills, min_years):
    skills_lower = [s.lower() for s in candidate["skills"]]
    matched = [s for s in required_skills if s.lower() in skills_lower]
    missing = [s for s in required_skills if s.lower() not in skills_lower]
    years   = candidate["years_exp"]

    tech_score = round((len(matched) / len(required_skills)) * 100) if required_skills else 0

    if years >= min_years + 2:
        exp_score = 100
    elif years >= min_years:
        exp_score = 80
    elif years >= min_years - 1:
        exp_score = 50
    else:
        exp_score = 20

    overall = min(100, round((tech_score * 0.6) + (exp_score * 0.4)))

    if overall >= 80:
        verdict = "Strong yes"
    elif overall >= 65:
        verdict = "Yes"
    elif overall >= 45:
        verdict = "Maybe"
    else:
        verdict = "No"

    red_flags = []
    if years < min_years:
        red_flags.append(f"Only {years} yrs exp, need {min_years}+")
    if tech_score < 40:
        red_flags.append("Missing many required skills")

    if verdict in ("Strong yes", "Yes"):
        summary = f"Strong fit. Matches {len(matched)}/{len(required_skills)} skills with {years} yrs exp. Key strengths: {', '.join(matched[:3]) or 'N/A'}."
    elif verdict == "Maybe":
        summary = f"Potential fit. Matches {len(matched)}/{len(required_skills)} skills but missing {', '.join(missing[:3]) or 'N/A'}."
    else:
        summary = f"Weak fit. Only {len(matched)}/{len(required_skills)} skills matched. Missing {', '.join(missing[:4]) or 'N/A'}."

    return {
        "name":             candidate["name"],
        "current_role":     candidate["current_role"],
        "years_exp":        years,
        "score":            overall,
        "technical_score":  tech_score,
        "experience_score": exp_score,
        "verdict":          verdict,
        "matched_skills":   matched[:5],
        "missing_skills":   missing[:3],
        "red_flags":        red_flags,
        "summary":          summary,
        "education":        candidate["education"],
        "notes":            candidate["notes"],
        "skills":           candidate["skills"],
    }


def answer_question(question, candidates):
    q = question.lower().strip()

    if not candidates:
        return "No candidates loaded yet."

    if any(x in q for x in ["best", "top", "strongest", "recommend", "hire"]):
        scored = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
        top = scored[0]
        return (
            f"**{top['name']}** is the top candidate with **{top.get('score', 'N/A')}%** match "
            f"and verdict **{top.get('verdict', 'N/A')}**. "
            f"{top['years_exp']} years exp as {top['current_role']}. "
            f"Key skills: {', '.join(top['skills'][:4])}."
        )

    if any(x in q for x in ["list all", "all candidates", "everyone", "who do we have", "how many"]):
        lines = [f"**{i}. {c['name']}** — {c['current_role']}, {c['years_exp']} yrs" for i, c in enumerate(candidates, 1)]
        return f"**{len(candidates)} candidates loaded:**\n\n" + "\n\n".join(lines)

    if any(x in q for x in ["shortlist", "interview", "call", "select"]):
        found = [c for c in candidates if c.get("verdict") in ("Strong yes", "Yes")]
        if found:
            lines = [f"**{c['name']}** ({c.get('score','N/A')}% — {c.get('verdict','')})" for c in found]
            return "Recommended for interview:\n\n" + "\n\n".join(lines)
        scored = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
        return f"Top 3 to consider: **{', '.join(c['name'] for c in scored[:3])}**."

    if any(x in q for x in ["most experience", "most exp", "experienced"]):
        top = max(candidates, key=lambda x: x["years_exp"])
        return f"**{top['name']}** has the most experience — **{top['years_exp']} years** as {top['current_role']}."

    if any(x in q for x in ["least experience", "junior", "least exp"]):
        bot = min(candidates, key=lambda x: x["years_exp"])
        return f"**{bot['name']}** has the least experience — **{bot['years_exp']} years** as {bot['current_role']}."

    if any(x in q for x in ["education", "degree", "university", "college", "study", "studied"]):
        lines = [f"**{c['name']}** — {c['education'] or 'Not specified'}" for c in candidates]
        return "Education details:\n\n" + "\n\n".join(lines)

    if any(x in q for x in ["years", "experience", "exp"]) and not any(x in q for x in ["most", "least"]):
        lines = sorted(candidates, key=lambda x: x["years_exp"], reverse=True)
        result = [f"**{c['name']}** — {c['years_exp']} years" for c in lines]
        return "Experience breakdown:\n\n" + "\n\n".join(result)

    if any(x in q for x in ["skill", "skills", "know", "knows", "capable", "tech"]):
        lines = [f"**{c['name']}** — {', '.join(c['skills'][:6]) or 'Not listed'}" for c in candidates]
        return "Skills for all candidates:\n\n" + "\n\n".join(lines)

    if any(x in q for x in ["gap", "missing", "lack", "weak"]):
        found = [c for c in candidates if c.get("missing_skills")]
        if found:
            lines = [f"**{c['name']}** — missing: {', '.join(c['missing_skills'])}" for c in found]
            return "Skill gaps:\n\n" + "\n\n".join(lines)
        return "Screen candidates against a JD first to see skill gaps."

    if any(x in q for x in ["reject", "worst", "not good", "lowest"]):
        found = [c for c in candidates if c.get("verdict") == "No"]
        if found:
            lines = [f"**{c['name']}** ({c.get('score','N/A')}%)" for c in found]
            return "Not recommended:\n\n" + "\n\n".join(lines)
        return "All candidates have some potential."

    if any(x in q for x in ["note", "notable", "achievement", "project", "accomplish"]):
        lines = [f"**{c['name']}** — {c['notes'] or 'Not specified'}" for c in candidates]
        return "Achievements and notes:\n\n" + "\n\n".join(lines)

    if "vs" in q or "compare" in q or "better" in q or "difference" in q:
        matched_people = []
        for c in candidates:
            for part in c["name"].lower().split():
                if part in q and c not in matched_people:
                    matched_people.append(c)
        if len(matched_people) >= 2:
            a, b = matched_people[0], matched_people[1]
            score_a = a.get("score", 0)
            score_b = b.get("score", 0)
            winner  = a["name"] if score_a >= score_b else b["name"]
            return (
                f"**{a['name']}** vs **{b['name']}**:\n\n"
                f"- {a['name']}: {a['years_exp']} yrs, skills: {', '.join(a['skills'][:4])}, score: {score_a}%\n\n"
                f"- {b['name']}: {b['years_exp']} yrs, skills: {', '.join(b['skills'][:4])}, score: {score_b}%\n\n"
                f"**{winner}** has the overall edge."
            )

    skill_map = {
        "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
        "java": "Java", "react": "React", "vue": "Vue.js", "angular": "Angular",
        "node": "Node.js", "django": "Django", "fastapi": "FastAPI", "flask": "Flask",
        "spring": "Spring Boot", "postgres": "PostgreSQL", "mysql": "MySQL",
        "mongodb": "MongoDB", "redis": "Redis", "aws": "AWS", "gcp": "GCP",
        "azure": "Azure", "docker": "Docker", "kubernetes": "Kubernetes",
        "ci/cd": "CI/CD", "cicd": "CI/CD", "graphql": "GraphQL", "rest": "REST APIs",
        "git": "Git", "linux": "Linux", "tensorflow": "TensorFlow",
        "pytorch": "PyTorch", "scikit": "scikit-learn",
    }

    group_map = {
        "cloud":       ["AWS", "GCP", "Azure"],
        "frontend":    ["React", "Vue.js", "Angular", "JavaScript", "TypeScript", "HTML", "CSS"],
        "backend":     ["Python", "Node.js", "Django", "FastAPI", "Flask", "Spring Boot", "Java"],
        "fullstack":   ["React", "Vue.js", "Python", "Node.js", "Django", "FastAPI"],
        "full stack":  ["React", "Vue.js", "Python", "Node.js", "Django", "FastAPI"],
        "devops":      ["Docker", "Kubernetes", "CI/CD", "AWS", "GCP", "Azure"],
        "ml":          ["Machine learning", "TensorFlow", "PyTorch", "scikit-learn"],
        "machine learning": ["Machine learning", "TensorFlow", "PyTorch", "scikit-learn"],
        "database":    ["PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite"],
    }

    for keyword, skill_list in group_map.items():
        if keyword in q:
            found = [c for c in candidates if any(s in c["skills"] for s in skill_list)]
            if found:
                lines = [f"**{c['name']}** — {', '.join(s for s in skill_list if s in c['skills'])}" for c in found]
                return f"Candidates with **{keyword}** skills:\n\n" + "\n\n".join(lines)
            return f"No candidates found with **{keyword}** skills."

    for keyword, skill in skill_map.items():
        if keyword in q:
            found = [c for c in candidates if skill in c["skills"]]
            if found:
                lines = [f"**{c['name']}** — {c['current_role']}" for c in found]
                return f"Candidates with **{skill}**:\n\n" + "\n\n".join(lines)
            return f"No candidates have **{skill}** experience."

    for c in candidates:
        for part in c["name"].lower().split():
            if part in q:
                score_str = f"\n- **Score:** {c['score']}% — {c['verdict']}" if c.get("score") else ""
                return (
                    f"**{c['name']}**\n"
                    f"- **Role:** {c['current_role']}\n"
                    f"- **Experience:** {c['years_exp']} years\n"
                    f"- **Education:** {c['education'] or 'Not specified'}\n"
                    f"- **Skills:** {', '.join(c['skills']) or 'Not listed'}\n"
                    f"- **Notes:** {c['notes'] or 'None'}"
                    f"{score_str}"
                )

    return (
        "I can answer questions like:\n\n"
        "- *Who is the best fit?*\n"
        "- *List all candidates*\n"
        "- *Who has Python / React / AWS?*\n"
        "- *Who has the most experience?*\n"
        "- *Who has frontend / backend / cloud skills?*\n"
        "- *Compare Priya vs Sneha*\n"
        "- *Tell me about Arjun*\n"
        "- *What is everyone's education?*\n"
        "- *Who should I shortlist?*\n"
        "- *Who has skill gaps?*"
    )


def generate_interview_qs(c):
    skill_qs = {
        "Python":       "Walk me through a complex Python project you built. What were the key decisions?",
        "FastAPI":      "How have you used FastAPI in production? How did you handle auth and performance?",
        "Django":       "How did you structure a large Django project and handle migrations at scale?",
        "React":        "How do you manage state in a large React app? Redux vs Context?",
        "PostgreSQL":   "How have you optimised slow PostgreSQL queries in production?",
        "Docker":       "Walk me through containerising an application with Docker end to end.",
        "AWS":          "Which AWS services have you used and what did you build with them?",
        "GCP":          "What GCP services have you used and what were the main challenges?",
        "GraphQL":      "Why GraphQL over REST? What tradeoffs did you consider?",
        "TypeScript":   "How has TypeScript improved your codebase? Give a specific example.",
        "Node.js":      "How do you handle async and errors in Node.js at scale?",
        "CI/CD":        "Describe your CI/CD pipeline. What tools and why?",
        "REST APIs":    "How do you design and version REST APIs? How do you handle breaking changes?",
        "Redis":        "How have you used Redis in production? What caching strategies?",
        "Vue.js":       "Vue vs React — key differences and when would you pick Vue?",
        "MongoDB":      "When would you choose MongoDB over SQL? Give a real example.",
        "Kubernetes":   "How have you used Kubernetes in production? What problems did it solve?",
        "Java":         "How have you used Java in a large production system?",
        "Machine learning": "Walk me through an ML project end to end — data, model, deployment.",
        "scikit-learn": "What ML models have you built with scikit-learn and how did you evaluate them?",
    }

    questions = []
    count = 0
    for skill in c["skills"]:
        if skill in skill_qs and count < 2:
            questions.append(f"**[Technical — {skill}]** {skill_qs[skill]}")
            count += 1

    if c.get("missing_skills"):
        for skill in c["missing_skills"][:2]:
            questions.append(
                f"**[Gap — {skill}]** You do not have much {skill} experience. "
                f"How would you approach learning it?"
            )

    questions.append(
        "**[Behavioural]** Tell me about a time you delivered a project under tight deadlines. "
        "What did you do and what was the outcome?"
    )
    questions.append(
        "**[Situational]** If you joined and found messy code with no tests, "
        "what would your first steps be while still shipping features?"
    )

    return questions[:6]


def make_csv(candidates):
    output = io.StringIO()
    fields = [
        "rank", "name", "current_role", "years_exp",
        "score", "technical_score", "experience_score",
        "verdict", "matched_skills", "missing_skills",
        "red_flags", "summary", "education", "notes"
    ]
    w = csv.DictWriter(output, fieldnames=fields)
    w.writeheader()
    for i, c in enumerate(candidates, 1):
        w.writerow({
            "rank":             i,
            "name":             c["name"],
            "current_role":     c["current_role"],
            "years_exp":        c["years_exp"],
            "score":            f"{c.get('score', 0)}%",
            "technical_score":  f"{c.get('technical_score', 0)}%",
            "experience_score": f"{c.get('experience_score', 0)}%",
            "verdict":          c.get("verdict", "Not screened"),
            "matched_skills":   " | ".join(c.get("matched_skills", [])),
            "missing_skills":   " | ".join(c.get("missing_skills", [])),
            "red_flags":        " | ".join(c.get("red_flags", [])),
            "summary":          c.get("summary", ""),
            "education":        c.get("education", ""),
            "notes":            c.get("notes", ""),
        })
    return output.getvalue()


# ================================================
#  UI
# ================================================

st.title("🔍 Resume Screener")
st.caption("Upload as many resumes as you want — then ask any question about them. Free, no API key needed.")

if "candidates" not in st.session_state:
    st.session_state["candidates"] = []
if "scored" not in st.session_state:
    st.session_state["scored"] = False
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

with st.sidebar:
    st.header("⚙️ Settings")
    min_years = st.slider("Minimum years experience", 1, 15, 4)
    st.divider()
    st.markdown("**Resume format:**")
    st.code(
        "--- CANDIDATE: Full Name ---\n"
        "Experience: 5 years\n"
        "Current Role: Engineer at Company\n"
        "Skills: Python, React, AWS\n"
        "Education: B.Tech, IIT Delhi\n"
        "Notable: Key achievements"
    )
    st.divider()
    if st.session_state["candidates"]:
        st.success(f"✅ {len(st.session_state['candidates'])} candidates loaded")
    else:
        st.info("No candidates loaded yet")
    st.divider()
    st.success("100% free. No API key. Works offline.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📤 Upload Resumes",
    "📋 Screen Against JD",
    "💬 Ask Questions",
    "🎤 Interview Questions",
    "📁 Export",
])

with tab1:
    st.subheader("Upload Resumes")
    st.write("Paste as many resumes as you want. Use the format shown in the sidebar.")

    if st.button("📥 Load Sample Resumes", use_container_width=True):
        st.session_state["resumes_raw"] = SAMPLE_RESUMES
        st.rerun()

    resumes_input = st.text_area(
        "Paste all resumes here",
        value=st.session_state.get("resumes_raw", ""),
        height=400,
        placeholder="--- CANDIDATE: Name ---\nExperience: 5 years\nCurrent Role: Engineer at Company\nSkills: Python, React, AWS\nEducation: B.Tech\nNotable: Key info\n\n--- CANDIDATE: Another Name ---\n..."
    )

    if st.button("✅ Load Resumes", type="primary", use_container_width=True):
        if not resumes_input.strip():
            st.error("Paste some resumes first!")
        elif "--- CANDIDATE:" not in resumes_input:
            st.error("Use the format: --- CANDIDATE: Name --- (see sidebar)")
        else:
            parsed = parse_resumes(resumes_input)
            if not parsed:
                st.error("Could not read any candidates. Check the format in the sidebar.")
            else:
                st.session_state["candidates"]   = parsed
                st.session_state["resumes_raw"]  = resumes_input
                st.session_state["scored"]       = False
                st.session_state["chat_history"] = []
                st.success(f"Loaded {len(parsed)} candidates!")
                st.rerun()

    if st.session_state["candidates"]:
        st.divider()
        st.subheader(f"Loaded Candidates ({len(st.session_state['candidates'])})")
        for i, c in enumerate(st.session_state["candidates"], 1):
            with st.expander(f"{i}. {c['name']} — {c['current_role']}"):
                st.write(f"**Experience:** {c['years_exp']} years")
                st.write(f"**Education:** {c['education'] or 'Not specified'}")
                st.write(f"**Skills:** {', '.join(c['skills']) or 'Not listed'}")
                st.write(f"**Notes:** {c['notes'] or 'None'}")

with tab2:
    st.subheader("Screen Against a Job Description")
    st.write("Paste a JD to get match scores for every candidate.")

    if not st.session_state["candidates"]:
        st.info("Load resumes first in the Upload Resumes tab.")
    else:
        jd_input = st.text_area(
            "Paste Job Description",
            value=st.session_state.get("jd_val", ""),
            height=250,
            placeholder="Senior Full-Stack Engineer\n\nRequirements:\n- 4+ years experience\n- Python and JavaScript\n- React or Vue.js\n- AWS or GCP\n- Docker and CI/CD..."
        )

        if st.button("🔍 Screen All Candidates", type="primary", use_container_width=True):
            if not jd_input.strip():
                st.error("Paste a job description first!")
            else:
                with st.spinner("Scoring all candidates..."):
                    required = [s for s in ALL_SKILLS if s.lower() in jd_input.lower()]
                    if not required:
                        required = ALL_SKILLS[:8]
                    scored = sorted(
                        [score_candidate(c, required, min_years) for c in st.session_state["candidates"]],
                        key=lambda x: x["score"],
                        reverse=True
                    )
                    st.session_state["candidates"] = scored
                    st.session_state["jd_val"]     = jd_input
                    st.session_state["scored"]     = True
                    st.success(f"Screened {len(scored)} candidates!")

        if st.session_state.get("scored") and st.session_state["candidates"]:
            candidates = st.session_state["candidates"]
            st.divider()

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total",       len(candidates))
            m2.metric("Strong Fits", len([c for c in candidates if c.get("score", 0) >= 75]))
            m3.metric("Avg Score",   f"{round(sum(c.get('score',0) for c in candidates)/len(candidates))}%")
            m4.metric("Top Pick",    candidates[0]["name"].split()[0])

            st.divider()
            icons = {"Strong yes": "🟢", "Yes": "🔵", "Maybe": "🟡", "No": "🔴"}

            for i, c in enumerate(candidates, 1):
                icon = icons.get(c.get("verdict", ""), "⚪")
                with st.expander(
                    f"#{i}  {c['name']}  —  {c.get('score',0)}%  {icon} {c.get('verdict','')}",
                    expanded=(i == 1)
                ):
                    sc1, sc2, sc3 = st.columns(3)
                    sc1.metric("Overall",    f"{c.get('score',0)}%")
                    sc2.metric("Technical",  f"{c.get('technical_score',0)}%")
                    sc3.metric("Experience", f"{c.get('experience_score',0)}%")
                    st.write(f"**Role:** {c['current_role']}")
                    st.write(f"**Exp:** {c['years_exp']} years")
                    st.write(f"**Education:** {c['education'] or 'N/A'}")
                    ca, cb = st.columns(2)
                    with ca:
                        if c.get("matched_skills"):
                            st.success(f"✅ Has: {', '.join(c['matched_skills'])}")
                    with cb:
                        if c.get("missing_skills"):
                            st.warning(f"❌ Missing: {', '.join(c['missing_skills'])}")
                    if c.get("red_flags"):
                        st.error(f"⚠️ {' | '.join(c['red_flags'])}")
                    st.info(c.get("summary", ""))

with tab3:
    st.subheader("💬 Ask Anything About the Candidates")

    if not st.session_state["candidates"]:
        st.info("Load resumes first in the Upload Resumes tab.")
    else:
        candidates = st.session_state["candidates"]

        st.write("**Quick questions — click any:**")
        qc1, qc2, qc3 = st.columns(3)
        quick_qs = [
            "Who is the best fit?",
            "List all candidates",
            "Who has the most experience?",
            "Who has Python experience?",
            "Who has cloud experience?",
            "Who has full stack skills?",
            "Who should I shortlist?",
            "Who has skill gaps?",
            "What is everyone's education?",
            "Who has machine learning skills?",
            "Who has frontend skills?",
            "Who has backend skills?",
        ]
        for idx, qq in enumerate(quick_qs):
            col = [qc1, qc2, qc3][idx % 3]
            if col.button(qq, key=f"qq_{idx}"):
                st.session_state["chat_history"].append({
                    "question": qq,
                    "answer":   answer_question(qq, candidates)
                })

        st.divider()

        with st.form("question_form", clear_on_submit=True):
            typed = st.text_input(
                "Type any question:",
                placeholder="Who has React? / Compare Priya vs Sneha / Tell me about Arjun / Who studied at IIT?"
            )
            submitted = st.form_submit_button("Ask ↗", use_container_width=True)
            if submitted and typed.strip():
                st.session_state["chat_history"].append({
                    "question": typed,
                    "answer":   answer_question(typed, candidates)
                })

        if st.session_state["chat_history"]:
            st.divider()
            st.subheader("Answers")
            for item in reversed(st.session_state["chat_history"]):
                st.markdown(f"**Q: {item['question']}**")
                st.markdown(item["answer"])
                st.divider()

            if st.button("🗑️ Clear history"):
                st.session_state["chat_history"] = []
                st.rerun()

with tab4:
    st.subheader("🎤 Interview Question Generator")

    if not st.session_state["candidates"]:
        st.info("Load resumes first in the Upload Resumes tab.")
    else:
        candidates = st.session_state["candidates"]
        selected   = st.selectbox("Pick a candidate:", [c["name"] for c in candidates])

        if st.button("Generate Questions", type="primary", use_container_width=True):
            c  = next(x for x in candidates if x["name"] == selected)
            qs = generate_interview_qs(c)
            st.write(f"**6 tailored questions for {c['name']}:**")
            st.divider()
            for i, q in enumerate(qs, 1):
                st.markdown(f"**{i}.** {q}")
                st.write("")

with tab5:
    st.subheader("📁 Export Results")

    if not st.session_state["candidates"]:
        st.info("Load resumes first in the Upload Resumes tab.")
    else:
        candidates = st.session_state["candidates"]

        st.download_button(
            label="⬇️ Download CSV",
            data=make_csv(candidates),
            file_name="screened_candidates.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary"
        )

        st.divider()
        st.subheader("Preview")
        rows = [{
            "Name":    c["name"],
            "Score":   f"{c.get('score', 'N/A')}%" if c.get("score") else "Not screened",
            "Verdict": c.get("verdict", "Not screened"),
            "Role":    c["current_role"],
            "Exp":     f"{c['years_exp']} yrs",
            "Skills":  ", ".join(c["skills"][:4]),
        } for c in candidates]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
