import streamlit as st
import csv
import io
import re
import yaml
from pathlib import Path

# Try all document reading libraries
try:
    import PyPDF2
    PDF_OK = True
except ImportError:
    PDF_OK = False

try:
    import docx2txt
    DOCX_OK = True
except ImportError:
    try:
        from docx import Document as DocxDocument
        DOCX_OK = True
        USE_DOCX2TXT = False
    except ImportError:
        DOCX_OK = False

st.set_page_config(
    page_title="Resume Screener",
    page_icon="🔍",
    layout="wide"
)

# ================================================
#  LOAD CONFIG FROM YAML
# ================================================

def load_config():
    config_path = Path("skills_config.yaml")
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {
        "all_skills": [
            "Python", "JavaScript", "TypeScript", "Java",
            "React", "Vue.js", "Node.js", "Django", "FastAPI",
            "PostgreSQL", "MySQL", "MongoDB", "Redis",
            "REST APIs", "GraphQL", "AWS", "GCP", "Azure",
            "Docker", "Kubernetes", "CI/CD",
            "Machine learning", "TensorFlow", "PyTorch", "scikit-learn",
            "Git", "Linux",
        ],
        "skill_map": {
            "python": "Python", "javascript": "JavaScript",
            "react": "React", "node": "Node.js", "aws": "AWS",
            "docker": "Docker", "postgres": "PostgreSQL",
        },
        "group_map": {
            "cloud": ["AWS", "GCP", "Azure"],
            "frontend": ["React", "Vue.js", "Angular", "JavaScript"],
            "backend": ["Python", "Node.js", "Django", "FastAPI"],
            "devops": ["Docker", "Kubernetes", "CI/CD"],
            "ml": ["Machine learning", "TensorFlow", "PyTorch", "scikit-learn"],
        },
        "skill_questions": {
            "Python": "Walk me through a complex Python project you built.",
            "React": "How do you manage state in a large React app?",
            "AWS": "Which AWS services have you used and what did you build?",
            "Docker": "Walk me through containerising an app with Docker.",
        }
    }

CONFIG          = load_config()
ALL_SKILLS      = CONFIG.get("all_skills", [])
SKILL_MAP       = CONFIG.get("skill_map", {})
GROUP_MAP       = CONFIG.get("group_map", {})
SKILL_QUESTIONS = CONFIG.get("skill_questions", {})

# ================================================
#  SAMPLE DATA
# ================================================

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

# ================================================
#  FILE READING — fixed to handle all cases
# ================================================

def read_pdf(file) -> str:
    if not PDF_OK:
        return ""
    try:
        reader = PyPDF2.PdfReader(file)
        text   = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
        return text.strip()
    except Exception:
        return ""

def read_docx(file) -> str:
    try:
        # Try docx2txt first — most reliable
        import docx2txt
        text = docx2txt.process(file)
        return text.strip() if text else ""
    except Exception:
        pass
    try:
        # Fallback to python-docx
        from docx import Document as DocxDoc
        doc  = DocxDoc(file)
        text = "\n".join(p.text for p in doc.paragraphs)
        return text.strip()
    except Exception:
        return ""

def read_txt(file) -> str:
    try:
        return file.read().decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""

def extract_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return read_pdf(uploaded_file)
    elif name.endswith(".docx") or name.endswith(".doc"):
        return read_docx(uploaded_file)
    elif name.endswith(".txt"):
        return read_txt(uploaded_file)
    return ""

def parse_from_text(text: str, filename: str) -> dict:
    name  = (
        filename
        .replace(".pdf","").replace(".docx","").replace(".doc","").replace(".txt","")
        .replace("_"," ").replace("-"," ")
        .title().strip()
    )
    skills    = []
    years     = 0
    role      = ""
    education = ""
    notes     = ""

    text_lower = text.lower()

    # Extract skills
    for skill in ALL_SKILLS:
        if skill.lower() in text_lower:
            skills.append(skill)

    # Extract years of experience
    patterns = [
        r'(\d+)\+?\s*years?\s*of\s*experience',
        r'(\d+)\+?\s*years?\s*experience',
        r'experience\s*[:\-]?\s*(\d+)\+?\s*years?',
        r'(\d+)\+?\s*yrs?\s*of\s*exp',
    ]
    for p in patterns:
        m = re.search(p, text_lower)
        if m:
            years = int(m.group(1))
            break

    # Extract role — look for job title keywords
    lines = text.split("\n")
    role_keywords = [
        "engineer", "developer", "manager", "analyst",
        "architect", "lead", "intern", "designer",
        "consultant", "director", "head of", "vp of"
    ]
    for line in lines[:30]:
        line_clean = line.strip()
        if any(kw in line_clean.lower() for kw in role_keywords) and len(line_clean) < 100:
            role = line_clean
            break

    # Extract education
    edu_kws = ["b.tech", "m.tech", "b.e.", "m.e.", "bsc", "msc",
                "bachelor", "master", "phd", "iit", "bits", "nit",
                "university", "college", "institute"]
    for line in lines:
        if any(kw in line.lower() for kw in edu_kws):
            education = line.strip()
            break

    # Use first 300 chars as notes
    notes = text[:300].replace("\n", " ").strip()

    return {
        "name":         name,
        "current_role": role or "Not specified",
        "years_exp":    years,
        "skills":       list(dict.fromkeys(skills)),  # remove duplicates
        "education":    education,
        "notes":        notes,
    }

# ================================================
#  PARSE PASTED RESUMES
# ================================================

def parse_resumes(raw_text: str) -> list:
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

# ================================================
#  SCORING
# ================================================

def score_candidate(candidate: dict, required_skills: list, min_years: int) -> dict:
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
        **candidate,
        "score":            overall,
        "technical_score":  tech_score,
        "experience_score": exp_score,
        "verdict":          verdict,
        "matched_skills":   matched[:5],
        "missing_skills":   missing[:3],
        "red_flags":        red_flags,
        "summary":          summary,
    }

# ================================================
#  Q&A
# ================================================

def answer_question(question: str, candidates: list) -> str:
    q = question.lower().strip()

    if not candidates:
        return "No candidates loaded yet."

    if any(x in q for x in ["best", "top", "strongest", "recommend", "hire"]):
        scored = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)
        top    = scored[0]
        return (
            f"**{top['name']}** is the top candidate with **{top.get('score','N/A')}%** match "
            f"and verdict **{top.get('verdict','N/A')}**. "
            f"{top['years_exp']} years exp as {top['current_role']}. "
            f"Key skills: {', '.join(top['skills'][:4])}."
        )

    if any(x in q for x in ["list all", "all candidates", "everyone", "how many", "who do we have"]):
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

    if any(x in q for x in ["education", "degree", "university", "college", "study"]):
        lines = [f"**{c['name']}** — {c['education'] or 'Not specified'}" for c in candidates]
        return "Education details:\n\n" + "\n\n".join(lines)

    if any(x in q for x in ["note", "notable", "achievement", "project"]):
        lines = [f"**{c['name']}** — {c['notes'] or 'Not specified'}" for c in candidates]
        return "Achievements and notes:\n\n" + "\n\n".join(lines)

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

    if "vs" in q or "compare" in q or "better" in q or "difference" in q:
        matched_people = []
        for c in candidates:
            for part in c["name"].lower().split():
                if part in q and c not in matched_people:
                    matched_people.append(c)
        if len(matched_people) >= 2:
            a, b    = matched_people[0], matched_people[1]
            score_a = a.get("score", 0)
            score_b = b.get("score", 0)
            winner  = a["name"] if score_a >= score_b else b["name"]
            return (
                f"**{a['name']}** vs **{b['name']}**:\n\n"
                f"- {a['name']}: {a['years_exp']} yrs, skills: {', '.join(a['skills'][:4])}, score: {score_a}%\n\n"
                f"- {b['name']}: {b['years_exp']} yrs, skills: {', '.join(b['skills'][:4])}, score: {score_b}%\n\n"
                f"**{winner}** has the overall edge."
            )

    for keyword, skill_list in GROUP_MAP.items():
        if keyword in q:
            found = [c for c in candidates if any(s in c["skills"] for s in skill_list)]
            if found:
                lines = [f"**{c['name']}** — {', '.join(s for s in skill_list if s in c['skills'])}" for c in found]
                return f"Candidates with **{keyword}** skills:\n\n" + "\n\n".join(lines)
            return f"No candidates found with **{keyword}** skills."

    for keyword, skill in SKILL_MAP.items():
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
        "I can answer:\n\n"
        "- *Who is the best fit?*\n"
        "- *List all candidates*\n"
        "- *Who has Python / React / AWS?*\n"
        "- *Who has the most experience?*\n"
        "- *Who has frontend / backend / cloud / ml skills?*\n"
        "- *Compare Priya vs Sneha*\n"
        "- *Tell me about Arjun*\n"
        "- *What is everyone's education?*\n"
        "- *Who should I shortlist?*\n"
        "- *Who has skill gaps?*"
    )

# ================================================
#  INTERVIEW QUESTIONS
# ================================================

def generate_interview_qs(c: dict) -> list:
    questions = []
    count = 0
    for skill in c["skills"]:
        if skill in SKILL_QUESTIONS and count < 2:
            questions.append(f"**[Technical — {skill}]** {SKILL_QUESTIONS[skill]}")
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

# ================================================
#  CSV EXPORT
# ================================================

def make_csv(candidates: list) -> str:
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
#  CHARTS
# ================================================

def show_charts(candidates: list):
    if not any(c.get("score") for c in candidates):
        st.info("Screen candidates against a JD first to see charts.")
        return

    names  = [c["name"].split()[0] for c in candidates]
    scores = [c.get("score", 0) for c in candidates]

    st.subheader("Score Comparison")
    st.bar_chart(dict(zip(names, scores)), use_container_width=True, height=300)

    st.divider()
    st.subheader("Technical vs Experience Score")
    chart_data = {
        c["name"].split()[0]: {
            "Technical":  c.get("technical_score", 0),
            "Experience": c.get("experience_score", 0),
        }
        for c in candidates
    }
    tech_data = {n: v["Technical"]  for n, v in chart_data.items()}
    exp_data  = {n: v["Experience"] for n, v in chart_data.items()}
    col1, col2 = st.columns(2)
    with col1:
        st.write("Technical Score")
        st.bar_chart(tech_data, use_container_width=True, height=250)
    with col2:
        st.write("Experience Score")
        st.bar_chart(exp_data, use_container_width=True, height=250)

    st.divider()
    st.subheader("Top Skills Across All Candidates")
    skill_count = {}
    for c in candidates:
        for s in c["skills"]:
            skill_count[s] = skill_count.get(s, 0) + 1
    top_skills = dict(sorted(skill_count.items(), key=lambda x: x[1], reverse=True)[:10])
    if top_skills:
        st.bar_chart(top_skills, use_container_width=True, height=300)

    st.divider()
    st.subheader("Verdict Breakdown")
    verdict_count = {"Strong yes": 0, "Yes": 0, "Maybe": 0, "No": 0}
    for c in candidates:
        v = c.get("verdict", "")
        if v in verdict_count:
            verdict_count[v] += 1
    st.bar_chart(verdict_count, use_container_width=True, height=250)

# ================================================
#  SESSION STATE
# ================================================

if "candidates" not in st.session_state:
    st.session_state["candidates"] = []
if "scored" not in st.session_state:
    st.session_state["scored"] = False
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ================================================
#  UI
# ================================================

st.title("🔍 Resume Screener")
st.caption("Upload resume files or paste them — then ask any question. Free, no API key, works in any browser.")

with st.sidebar:
    st.header("⚙️ Settings")
    min_years = st.slider("Minimum years experience", 1, 15, 4)
    st.divider()
    st.markdown("**Paste format:**")
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

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📤 Upload Resumes",
    "📋 Screen Against JD",
    "💬 Ask Questions",
    "🎤 Interview Questions",
    "📊 Charts",
    "📁 Export CSV",
])

# ── TAB 1 ──────────────────────────────────────
with tab1:
    st.subheader("Upload Resumes")

    method = st.radio(
        "How do you want to add resumes?",
        ["Upload files (PDF, Word, TXT)", "Paste text"],
        horizontal=True
    )

    if method == "Upload files (PDF, Word, TXT)":
        st.write("Upload one file per candidate. PDF, DOCX, and TXT supported.")

        uploaded_files = st.file_uploader(
            "Upload resume files",
            type=["pdf", "docx", "doc", "txt"],
            accept_multiple_files=True
        )

        if uploaded_files:
            if st.button("✅ Load Uploaded Resumes", type="primary", use_container_width=True):
                parsed = []
                errors = []
                for f in uploaded_files:
                    text = extract_text(f)
                    if text.strip():
                        candidate = parse_from_text(text, f.name)
                        parsed.append(candidate)
                    else:
                        errors.append(f.name)

                if errors:
                    st.warning(
                        f"Could not read these files: {', '.join(errors)}\n\n"
                        "Try saving them as .txt format instead."
                    )

                if parsed:
                    st.session_state["candidates"]   = parsed
                    st.session_state["scored"]       = False
                    st.session_state["chat_history"] = []
                    st.success(f"Loaded {len(parsed)} candidates!")
                    st.rerun()
                else:
                    st.error(
                        "Could not read any files.\n\n"
                        "**Quick fix:** Open Word → File → Save As → Plain Text (.txt) → upload that instead."
                    )

    else:
        if st.button("📥 Load Sample Data", use_container_width=True):
            st.session_state["resumes_raw"] = SAMPLE_RESUMES
            st.rerun()

        resumes_input = st.text_area(
            "Paste resumes here",
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
                    st.error("Could not read candidates. Check the format.")
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

# ── TAB 2 ──────────────────────────────────────
with tab2:
    st.subheader("Screen Against a Job Description")

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

        if st.session_state.get("scored"):
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

# ── TAB 3 ──────────────────────────────────────
with tab3:
    st.subheader("💬 Ask Anything About the Candidates")

    if not st.session_state["candidates"]:
        st.info("Load resumes first in the Upload Resumes tab.")
    else:
        candidates = st.session_state["candidates"]

        st.write("**Quick questions:**")
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
                placeholder="Who has React? / Compare Priya vs Sneha / Tell me about Arjun"
            )
            submitted = st.form_submit_button("Ask ↗", use_container_width=True)
            if submitted and typed.strip():
                st.session_state["chat_history"].append({
                    "question": typed,
                    "answer":   answer_question(typed, candidates)
                })

        if st.session_state["chat_history"]:
            st.divider()
            for item in reversed(st.session_state["chat_history"]):
                st.markdown(f"**Q: {item['question']}**")
                st.markdown(item["answer"])
                st.divider()
            if st.button("🗑️ Clear history"):
                st.session_state["chat_history"] = []
                st.rerun()

# ── TAB 4 ──────────────────────────────────────
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

# ── TAB 5 ──────────────────────────────────────
with tab5:
    st.subheader("📊 Visual Reports")

    if not st.session_state["candidates"]:
        st.info("Load resumes first in the Upload Resumes tab.")
    else:
        show_charts(st.session_state["candidates"])

# ── TAB 6 ──────────────────────────────────────
with tab6:
    st.subheader("📁 Export Results to CSV")

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
            "Score":   f"{c.get('score','N/A')}%" if c.get("score") else "Not screened",
            "Verdict": c.get("verdict", "Not screened"),
            "Role":    c["current_role"],
            "Exp":     f"{c['years_exp']} yrs",
            "Skills":  ", ".join(c["skills"][:4]),
        } for c in candidates]
        st.table(rows)
