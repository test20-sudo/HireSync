from flask import Flask, request, render_template, jsonify
import PyPDF2
import re
import google.generativeai as genai
import random
from serpapi import GoogleSearch
import os

app = Flask(__name__)

genai.configure(api_key='AIzaSyAYaBIKu3m-LcHGj-11tBJpmo6yMKU-NB4')
model = genai.GenerativeModel('gemini-1.5-pro')

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        num_pages = len(reader.pages)
        text = ""
        for page_num in range(num_pages):
            page = reader.pages[page_num]
            text += page.extract_text()
        text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
        text = re.sub(r"\s+", " ", text)
    return text

def summarize_resume(keywords_list):
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"Give a small 3-4 line summary on skill levels and expertise based on the resume. Then highlight strong and weak points in 3 points each. Use first person verbs. Lastly ask for preferred job location.\n{keywords_list}"
    try:
        response = model.generate_content(prompt)
        summary = re.sub(r"[*#_]", "", response.text.strip())
        return summary
    except Exception as e:
        return f"Error generating content: {str(e)}"

def extract_job_terms(summary):
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
Extract all the coding languages and technical domain and its related terms in the field of web development, machine learning, app development, content creation, graphics design, and UI/UX from the following summary:
    {summary}
     **Web Development:**
    - Coding Languages: HTML, CSS, JavaScript, Python, PHP
    - Frameworks/Libraries: React, Angular, Node.js, Django
    - Other Terms: REST APIs, web server, front-end, back-end
    
    **Machine Learning:**
    - Coding Languages: Python, R
    - Libraries/Frameworks: TensorFlow, PyTorch, Scikit-learn
    - Other Terms: Data analysis, model training, deep learning, AI
    - Also terms related to Computer Vision and NLP if found
    
    **App Development:**
    - Coding Languages: Java, Kotlin, Swift, C#
    - Platforms: Android, iOS
    - Other Terms: Mobile development, SDKs, user interface
    
    **Content Creation:**
    - Tools: WordPress, Canva, Adobe Creative Suite
    - Other Terms: SEO, blogging, content marketing
    
    **Graphics Design:**
    - Software: Adobe Photoshop, Illustrator, InDesign
    - Other Terms: Visual design, branding, typography
    
    **UI/UX:**
    - Design Tools: Figma, Sketch, Adobe XD
    - Other Terms: User experience, user interface, wireframing, prototyping
    
    If any of the terms related to this are present in the list, return those and also specify from which domain. Display only the terms for example: 
    C, C++, Python, Machine learning. Keep it in one line. Also include coding popular coding platforms like CodeChef, Codeforces, LeetCode etc.
    Keep the terms simple and separate by commas.
"""
    try:
        response = model.generate_content(prompt)
        terms = re.sub(r"[*#_]", "", response.text.strip())
        return [term.strip() for term in terms.split(',') if term.strip()]
    except Exception as e:
        return []

def select_search_terms(terms, search_level):
    if not terms:
        return []
        
    num_terms = {
        'basic': 3,
        'medium': 6,
        'comprehensive': 9
    }.get(search_level, 3)
    
    if len(terms) <= num_terms:
        return terms
        
    return random.sample(terms, num_terms)

def search_jobs(terms, location, api_key, search_level):
    job_listings = []
    total_jobs_found = 0
    
    jobs_per_term = {
        'basic': 10,
        'medium': 15,
        'comprehensive': 10
    }.get(search_level, 10)

    selected_terms = select_search_terms(terms, search_level)

    for term in selected_terms:
        try:
            search_query = f"{term} in {location}"
            params = {
                "engine": "google_jobs",
                "q": search_query,
                "hl": "en",
                "api_key": api_key
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            jobs_results = results.get("jobs_results", [])
            total_jobs_found += len(jobs_results)

            for job in jobs_results[:jobs_per_term]:
                job_listings.append({
                    'title': job['title'],
                    'company_name': job['company_name'],
                    'location': job['location'],
                    'link': job['apply_options'][0]['link'] if job.get('apply_options') else '#',
                    'searched_term': term
                })
        except Exception as e:
            continue

    return job_listings, total_jobs_found

# Global variable to store the uploaded file path
uploaded_file_path = None

@app.route('/', methods=['GET', 'POST'])
def index():
    global uploaded_file_path
    
    if request.method == 'POST':
        if 'resume' not in request.files:
            return "No file part"
        file = request.files['resume']
        if file.filename == '':
            return "No selected file"
        if file:
            # Save file in root directory
            uploaded_file_path = "uploaded_resume.pdf"
            file.save(uploaded_file_path)
            paragraph = extract_text_from_pdf(uploaded_file_path)
            summary = summarize_resume(paragraph)
            terms = extract_job_terms(paragraph)  # Changed from summary to paragraph for better term extraction
            return render_template('index.html', summary=summary, terms=terms)
    return render_template('index.html')

@app.route('/jobs', methods=['POST'])
def jobs():
    global uploaded_file_path
    
    location = request.form['location']
    api_key = request.form['api_key']
    search_level = request.form['search_level']
    
    # Extract terms from the uploaded resume again if needed
    if not request.form.getlist('terms[]') and uploaded_file_path:
        paragraph = extract_text_from_pdf(uploaded_file_path)
        terms = extract_job_terms(paragraph)
    else:
        terms = request.form.getlist('terms[]')
    
    job_listings, total_jobs_found = search_jobs(terms, location, api_key, search_level)
    
    return jsonify({
        'job_listings': job_listings, 
        'total_jobs_found': total_jobs_found,
        'search_level': search_level,
        'selected_terms': terms
    })

if __name__ == "__main__":
    app.run(debug=True)
