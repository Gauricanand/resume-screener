# 🔍 Resume Screener

A free AI-style resume screening tool. No API key needed. Works in any browser.

## Live App
[Click here to use the app](https://yourname-resume-screener.streamlit.app)

## What it does
- Upload resume files directly (PDF, Word, TXT)
- Screen candidates against a Job Description
- Ask any question about the candidates
- Generate tailored interview questions per candidate
- Export full results to CSV
- Visual charts showing candidate scores and skill coverage

## Resume format (if pasting manually)
--- CANDIDATE: Full Name ---
Experience: 5 years
Current Role: Engineer at Company
Skills: Python, React, AWS
Education: B.Tech, IIT Delhi
Notable: Key achievements here

## Questions you can ask
- Who is the best fit?
- Who has Python experience?
- Who has cloud experience?
- Who has the most experience?
- Who should I shortlist?
- Compare Priya vs Sneha
- Tell me about Arjun
- Who has frontend / backend / full stack skills?
- Who has machine learning skills?
- What is everyone's education?

## Tech Stack
- Python
- Streamlit
- PyYAML
- PyPDF2
- python-docx

## How to run locally
pip install streamlit openpyxl pyyaml pypdf2 python-docx
streamlit run app.py

## Project Structure
resume-screener/
    app.py              Main application
    skills_config.yaml  All skills and mappings config
    requirements.txt    Python dependencies
    README.md           This file

## Deploy free on Streamlit Cloud
1. Fork this repo
2. Go to share.streamlit.io
3. Connect your GitHub
4. Pick this repo and deploy
5. Get a free public link instantly
