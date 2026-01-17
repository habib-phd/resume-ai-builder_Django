from django.shortcuts import render
from django.http import HttpResponse
from transformers import pipeline
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import re
import logging

logging.getLogger("transformers").setLevel(logging.ERROR)

# Load GPT-2 model
generator = pipeline(
    "text-generation",
    model="gpt2-medium"
)
generator.tokenizer.pad_token_id = generator.model.config.eos_token_id

# ------------------------------
# Helper Functions
# ------------------------------

def remove_repetition(text):
    lines = text.split("\n")
    seen = set()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in seen:
            cleaned.append(stripped)
            seen.add(stripped)
    return "\n".join(cleaned)

def clean_text(text):
    # Remove extra whitespace and unwanted characters
    text = re.sub(r'\s+\n', '\n', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def format_resume_prompt(name, experience, skills, education, age):
    return f"""
You are an AI that writes professional resumes. 
Write a clean, professional resume in plain text. Include:

- Short summary paragraph at the top.
- Bullet points for each experience and skill.
- Sections with clear headings: Name, Summary, Experience, Skills, Education, Age.
- Do not include any unrelated text, commentary, or ads.

Name: {name}
Experience: {experience}
Skills: {skills}
Education: {education}
Age: {age}
"""

# ------------------------------
# Views
# ------------------------------

def home(request):
    # Pre-fill fields from session if available
    context = {
        "name": request.session.get("name", ""),
        "experience": request.session.get("experience", ""),
        "skills": request.session.get("skills", ""),
        "education": request.session.get("education", ""),
        "age": request.session.get("age", "")
    }
    return render(request, 'form.html', context)


def generate_resume(request):
    name = "Habib"
    experience = ""
    skills = ""
    education = ""
    age = ""

    if request.method == "POST":
        name = request.POST.get("name", "")
        experience = request.POST.get("experience", "")
        skills = request.POST.get("skills", "")
        education = request.POST.get("education", "")
        age = request.POST.get("age", "N/A")

        # Save input in session for pre-fill
        request.session["name"] = name
        request.session["experience"] = experience
        request.session["skills"] = skills
        request.session["education"] = education
        request.session["age"] = age

        prompt = format_resume_prompt(name, experience, skills, education, age)

        # Generate resume with controlled output
        result = generator(
            prompt,
            max_new_tokens=250,
            temperature=0.5,   # Lower randomness for professional text
            top_k=50,
            top_p=0.95,
            repetition_penalty=2.0
        )[0]["generated_text"]

        # Clean and deduplicate
        result = remove_repetition(result)
        result = clean_text(result)

        request.session['resume_text'] = result
        return render(request, "resume_preview.html", {"resume_text": result})

    # For GET request, show form with pre-filled inputs
    return render(request, "form.html", {
        "name": name,
        "experience": experience,
        "skills": skills,
        "education": education,
        "age": age
    })


def download_pdf(request):
    resume_text = request.session.get('resume_text', '')
    if not resume_text:
        return HttpResponse("No resume generated yet.", status=400)

    # ------------------------------
    # ReportLab PDF generation
    # ------------------------------
    # Use a Unicode font to support all characters
    pdfmetrics.registerFont(TTFont('DejaVu', '/System/Library/Fonts/Supplemental/DejaVuSans.ttf'))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="resume.pdf"'

    c = canvas.Canvas(response, pagesize=LETTER)
    width, height = LETTER
    c.setFont("DejaVu", 12)

    y = height - 50
    for line in resume_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Bold headings if line ends with colon
        if line.endswith(":"):
            c.setFont("DejaVu", 14)
        else:
            c.setFont("DejaVu", 12)

        # Add bullet points
        if line.startswith("-"):
            line = "• " + line[1:].strip()

        c.drawString(50, y, line)
        y -= 18
        if y < 50:
            c.showPage()
            c.setFont("DejaVu", 12)
            y = height - 50

    c.save()
    return response
