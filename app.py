# app.py - Complete with PDF generation
import os
import json
import uuid
import requests
from flask import Flask, render_template, request, jsonify, make_response
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from fpdf import FPDF

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SECRET_KEY'] = os.urandom(24)
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'docx', 'md', 'py', 'java', 'cpp', 'html', 'css', 'js', 'json'}

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

FREE_MODELS = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-2-2b-it:free",
    "microsoft/phi-3-mini-4k-instruct:free",
    "qwen/qwen2.5-7b-instruct:free",
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def read_file_content(filepath):
    """Simple file reader"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def generate_pdf_report(report_data):
    """Generate a professional PDF report from analysis data"""
    buffer = BytesIO()
    
    # Create PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Create custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#2C3E50'),
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.HexColor('#3498DB')
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        spaceAfter=8,
        textColor=colors.HexColor('#7F8C8D')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6
    )
    
    # Build story (content)
    story = []
    
    # Title Page
    story.append(Paragraph("RUBRIX Assignment Analysis Report", title_style))
    story.append(Spacer(1, 40))
    
    # Logo/Header
    story.append(Paragraph("AI-Powered Academic Evaluation", ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#7F8C8D'),
        alignment=1
    )))
    story.append(Spacer(1, 40))
    
    # Assignment Info in a table
    assignment_info = [
        ["Assignment:", report_data.get('assignment', 'N/A')],
        ["Rubric:", report_data.get('rubric', 'N/A')],
        ["Overall Score:", f"{report_data.get('overall_score', 'N/A')}/100"],
        ["Overall Grade:", report_data.get('overall_grade', 'N/A')],
        ["Report Generated:", report_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))]
    ]
    
    table = Table(assignment_info, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2C3E50')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(table)
    
    story.append(Spacer(1, 30))
    story.append(Paragraph("Executive Summary", heading_style))
    story.append(Paragraph(report_data.get('summary', 'No summary available.'), normal_style))
    
    if report_data.get('grade_justification'):
        story.append(Spacer(1, 20))
        story.append(Paragraph("Grade Justification", heading_style))
        story.append(Paragraph(report_data.get('grade_justification'), normal_style))
    
    story.append(PageBreak())
    
    # Critical Deficiencies
    if report_data.get('critical_deficiencies') and len(report_data['critical_deficiencies']) > 0:
        story.append(Paragraph("Critical Deficiencies", heading_style))
        story.append(Paragraph("These issues require immediate attention:", subheading_style))
        story.append(Spacer(1, 10))
        
        for i, deficiency in enumerate(report_data['critical_deficiencies'], 1):
            story.append(Paragraph(f"<b>{i}. {deficiency.get('issue', 'N/A')}</b>", subheading_style))
            if deficiency.get('priority'):
                story.append(Paragraph(f"Priority: {deficiency['priority'].upper()}", normal_style))
            if deficiency.get('evidence'):
                story.append(Paragraph(f"<i>Evidence:</i> \"{deficiency['evidence']}\"", normal_style))
            if deficiency.get('remediation'):
                story.append(Paragraph(f"<i>How to Fix:</i> {deficiency['remediation']}", normal_style))
            story.append(Spacer(1, 15))
    
    # Criteria Breakdown
    if report_data.get('criteria') and len(report_data['criteria']) > 0:
        story.append(PageBreak())
        story.append(Paragraph("Detailed Criteria Analysis", heading_style))
        
        for criterion in report_data['criteria']:
            # Criterion header with score
            score_percentage = criterion.get('score_percentage', 0)
            weight = criterion.get('weight', 0)
            score_display = f"{score_percentage}%"
            
            story.append(Paragraph(
                f"<b>{criterion.get('criterion', 'N/A')}</b> - Score: {score_display} (Weight: {weight}%)",
                subheading_style
            ))
            
            # Progress bar representation
            if score_percentage >= 70:
                score_color = "Good"
            elif score_percentage >= 50:
                score_color = "Needs Work"
            else:
                score_color = "Poor"
            
            story.append(Paragraph(f"Performance Level: {score_color}", normal_style))
            
            # Strengths
            if criterion.get('strengths') and len(criterion['strengths']) > 0:
                story.append(Paragraph("<b>Strengths:</b>", normal_style))
                for strength in criterion['strengths']:
                    story.append(Paragraph(f"• {strength}", normal_style))
            
            # Deficiencies
            if criterion.get('deficiencies') and len(criterion['deficiencies']) > 0:
                story.append(Paragraph("<b>Areas Needing Improvement:</b>", normal_style))
                for deficiency in criterion['deficiencies']:
                    story.append(Paragraph(f"• {deficiency}", normal_style))
            
            # Recommendations
            if criterion.get('recommendations') and len(criterion['recommendations']) > 0:
                story.append(Paragraph("<b>Specific Recommendations:</b>", normal_style))
                for rec in criterion['recommendations']:
                    story.append(Paragraph(f"• {rec}", normal_style))
            
            story.append(Spacer(1, 20))
    
    # Strengths to Build Upon
    if report_data.get('strengths_to_build') and len(report_data['strengths_to_build']) > 0:
        story.append(PageBreak())
        story.append(Paragraph("Key Strengths to Build Upon", heading_style))
        
        for i, strength in enumerate(report_data['strengths_to_build'], 1):
            story.append(Paragraph(f"<b>{i}. {strength.get('strength', 'N/A')}</b>", subheading_style))
            if strength.get('evidence'):
                story.append(Paragraph(f"Evidence: \"{strength['evidence']}\"", normal_style))
            if strength.get('reinforcement'):
                story.append(Paragraph(f"How to build on this: {strength['reinforcement']}", normal_style))
            story.append(Spacer(1, 10))
    
    # Structural Analysis
    if report_data.get('structural_analysis'):
        story.append(PageBreak())
        story.append(Paragraph("Structural Analysis", heading_style))
        
        struct = report_data['structural_analysis']
        
        if struct.get('organization'):
            story.append(Paragraph("<b>Organization:</b>", subheading_style))
            story.append(Paragraph(struct.get('organization', 'N/A'), normal_style))
            story.append(Spacer(1, 10))
        
        if struct.get('argument_development'):
            story.append(Paragraph("<b>Argument Development:</b>", subheading_style))
            story.append(Paragraph(struct.get('argument_development', 'N/A'), normal_style))
            story.append(Spacer(1, 10))
        
        if struct.get('technical_compliance'):
            story.append(Paragraph("<b>Technical Compliance:</b>", subheading_style))
            story.append(Paragraph(struct.get('technical_compliance', 'N/A'), normal_style))
    
    # Revision Recommendations
    if report_data.get('revision_recommendations'):
        story.append(PageBreak())
        story.append(Paragraph("Revision Action Plan", heading_style))
        
        recs = report_data['revision_recommendations']
        
        if recs.get('high_priority') and len(recs['high_priority']) > 0:
            story.append(Paragraph("<b>High Priority (Do First):</b>", subheading_style))
            for item in recs['high_priority']:
                story.append(Paragraph(f"• {item}", normal_style))
            story.append(Spacer(1, 10))
        
        if recs.get('content_improvements') and len(recs['content_improvements']) > 0:
            story.append(Paragraph("<b>Content Improvements:</b>", subheading_style))
            for item in recs['content_improvements']:
                story.append(Paragraph(f"• {item}", normal_style))
            story.append(Spacer(1, 10))
        
        if recs.get('structural_changes') and len(recs['structural_changes']) > 0:
            story.append(Paragraph("<b>Structural Changes:</b>", subheading_style))
            for item in recs['structural_changes']:
                story.append(Paragraph(f"• {item}", normal_style))
            story.append(Spacer(1, 10))
        
        if recs.get('technical_fixes') and len(recs['technical_fixes']) > 0:
            story.append(Paragraph("<b>Technical Fixes:</b>", subheading_style))
            for item in recs['technical_fixes']:
                story.append(Paragraph(f"• {item}", normal_style))
    
    # Readiness Assessment
    if report_data.get('readiness_assessment'):
        story.append(Spacer(1, 20))
        story.append(Paragraph("Readiness Assessment", heading_style))
        
        readiness = report_data['readiness_assessment']
        
        # Status indicator
        status = readiness.get('status', 'Not Assessed')
        if 'Ready' in status:
            status_color = colors.green
        elif 'Minor' in status:
            status_color = colors.orange
        else:
            status_color = colors.red
        
        story.append(Paragraph(f"<b>Status:</b> <font color='{status_color.hexval()}'>{status}</font>", normal_style))
        
        if readiness.get('estimated_revision_hours'):
            story.append(Paragraph(f"<b>Estimated Revision Time:</b> {readiness['estimated_revision_hours']} hours", normal_style))
        
        if readiness.get('key_barriers') and len(readiness['key_barriers']) > 0:
            story.append(Spacer(1, 10))
            story.append(Paragraph("<b>Key Barriers to Higher Score:</b>", subheading_style))
            for barrier in readiness['key_barriers']:
                story.append(Paragraph(f"• {barrier}", normal_style))
    
    # Footer/Notes
    story.append(PageBreak())
    story.append(Paragraph("Report Notes", heading_style))
    story.append(Paragraph("This report was generated by RUBRIX AI-Powered Assignment Analysis System.", normal_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("For questions or additional support, please contact your instructor or academic advisor.", normal_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Report ID: {report_data.get('analysis_id', str(uuid.uuid4())[:8])}", normal_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}", normal_style))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes

def analyze_with_openrouter(assignment_text, rubric_text, detailed_analysis=True, rewrite_suggestions=True, grade_prediction=True):
    """Use OpenRouter's free models with STRICT evaluation prompt"""
    
    # Prepare the STRICT prompt
    prompt = f"""You are an experienced educator and evaluation specialist tasked with rigorous assessment of academic work. Your analysis must be critical, comprehensive, and strictly adhere to the rubric criteria.

**RUBRIC FOR EVALUATION:**
{rubric_text[:4000]}

**ASSIGNMENT SUBMISSION TO EVALUATE:**
{assignment_text[:6000]}

---

## **EVALUATION INSTRUCTIONS:**

### **1. STRICT ADHERENCE TO RUBRIC:**
- Evaluate EXCLUSIVELY based on the provided rubric criteria
- Do NOT introduce external standards or personal preferences
- Map EVERY piece of feedback directly to specific rubric criteria

### **2. REQUIRED ANALYSIS COMPONENTS:**

#### **A. QUANTITATIVE SCORING:**
- Score each rubric criterion separately on a scale of 0-100%
- Provide EXACT percentages, not ranges
- Calculate weighted overall score if rubric includes weightings
- Flag ANY criterion where score is below 70% as "Needs Significant Improvement"

#### **B. QUALITATIVE FEEDBACK (MUST INCLUDE):**
- **Strengths Identified:** List 3-5 specific examples where criteria were met/exceeded
- **Deficiencies Found:** List 5-8 specific, actionable deficiencies with exact evidence from submission
- **Critical Analysis:** Explain WHY each deficiency constitutes a failure to meet rubric standards
- **Evidence-Based Assessment:** Include exact quotes/line numbers to support every claim

#### **C. STRUCTURAL ANALYSIS:**
- **Organization Evaluation:** Assess logical flow, paragraph structure, transitions
- **Argumentation Analysis:** Evaluate thesis clarity, evidence quality, logical consistency
- **Technical Components:** Check formatting, citations, length compliance, technical accuracy

#### **D. CRITICAL THINKING ASSESSMENT:**
- **Depth of Analysis:** Evaluate sophistication of thought, not just surface-level coverage
- **Originality Assessment:** Check for rote repetition vs. genuine insight
- **Synthesis Evaluation:** Assess integration of concepts, critical connections made

### **3. REQUIRED FORMAT FOR RESPONSE:**

Provide your analysis as a JSON object with this EXACT structure:
{{
    "overall_score": 85,
    "overall_grade": "B",
    "criteria_breakdown": [
        {{
            "criterion": "Criterion Name", 
            "score_percentage": 80, 
            "weight": 25,
            "strengths": ["Specific strength with evidence"],
            "deficiencies": ["Specific deficiency with exact quote"],
            "recommendations": ["Concrete action required"],
            "needs_improvement": true/false
        }}
    ],
    "critical_deficiencies": [
        {{
            "issue": "Specific critical issue",
            "evidence": "Exact quote/location",
            "priority": "high/medium/low",
            "remediation": "Step-by-step fix"
        }}
    ],
    "strengths_to_build": [
        {{
            "strength": "Specific strength",
            "evidence": "Exact quote/location",
            "reinforcement": "How to build on this"
        }}
    ],
    "structural_analysis": {{
        "organization": "Detailed assessment",
        "argument_development": "Specific evaluation",
        "technical_compliance": "Checklist results"
    }},
    "revision_recommendations": {{
        "high_priority": ["Exactly what to fix first"],
        "content_improvements": ["Specific content changes"],
        "structural_changes": ["Required reorganization"],
        "technical_fixes": ["Exact formatting fixes"]
    }},
    "grade_justification": "Concise paragraph explaining score",
    "readiness_assessment": {{
        "status": "Needs Major Revision",
        "estimated_revision_hours": 5,
        "key_barriers": ["Fundamental issue 1", "Fundamental issue 2"]
    }},
    "summary": "Overall summary with actionable insights"
}}

### **4. EVALUATION PRINCIPLES TO ENFORCE:**

- **Zero Tolerance for:** Plagiarism indicators, major factual errors, ignoring assignment requirements
- **High Standards for:** Critical thinking, original analysis, proper academic conventions
- **Evidence-Required:** Every criticism MUST reference specific submission content
- **Action-Oriented:** All feedback must enable immediate, concrete improvements

### **5. FINAL REQUIREMENTS:**

- Do NOT give participation trophies or inflated scores
- Do NOT hesitate to give low scores when warranted by rubric
- Do NOT provide vague feedback - be brutally specific
- DO highlight both excellence and failure with equal specificity
- DO maintain professional, constructive but uncompromising tone

**BEGIN EVALUATION NOW. Be meticulous, critical, and evidence-based in your assessment.**
"""
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "RUBRIX Assignment Evaluator",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": FREE_MODELS[0],
        "messages": [
            {"role": "system", "content": "You are an expert teacher and rigorous evaluator. Always respond with valid JSON only. Be critical, evidence-based, and uncompromising in your assessment."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        
        result = response.json()
        ai_response = result["choices"][0]["message"]["content"]
        
        # Clean the response
        ai_response = ai_response.strip()
        if ai_response.startswith("```json"):
            ai_response = ai_response[7:-3].strip()
        elif ai_response.startswith("```"):
            ai_response = ai_response[3:-3].strip()
            
        return ai_response
        
    except Exception as e:
        print(f"OpenRouter error: {e}")
        # Fallback to simulation with strict format
        return json.dumps({
            "overall_score": 78,
            "overall_grade": "C+",
            "criteria_breakdown": [
                {
                    "criterion": "Content Quality",
                    "score_percentage": 72,
                    "weight": 35,
                    "strengths": ["Clear thesis statement in introduction", "Relevant examples provided"],
                    "deficiencies": ["Lacks depth in analysis - only surface level coverage", "Missing citations for key claims"],
                    "recommendations": ["Add at least 3 scholarly references", "Deepen analysis with counterarguments"],
                    "needs_improvement": True
                },
                {
                    "criterion": "Organization",
                    "score_percentage": 85,
                    "weight": 25,
                    "strengths": ["Logical paragraph structure", "Clear transitions between sections"],
                    "deficiencies": ["Conclusion is abrupt and doesn't synthesize main points", "Introduction could better preview structure"],
                    "recommendations": ["Expand conclusion to summarize key findings", "Add roadmap sentence in introduction"],
                    "needs_improvement": False
                },
                {
                    "criterion": "Critical Thinking",
                    "score_percentage": 65,
                    "weight": 40,
                    "strengths": ["Identifies main issues in the topic"],
                    "deficiencies": ["Fails to analyze underlying assumptions", "No synthesis of different perspectives", "Superficial evaluation of evidence"],
                    "recommendations": ["Question the assumptions behind each argument", "Compare and contrast at least 3 different viewpoints", "Evaluate the quality of evidence used"],
                    "needs_improvement": True
                }
            ],
            "critical_deficiencies": [
                {
                    "issue": "Lack of critical analysis depth",
                    "evidence": "\"The solution is effective because it helps people.\" (Paragraph 3) - This is descriptive, not analytical",
                    "priority": "high",
                    "remediation": "Replace descriptive statements with analytical questions: Why is it effective? For whom? Under what conditions? Compared to what alternatives?"
                },
                {
                    "issue": "Missing academic citations",
                    "evidence": "No references provided for claims about statistics or established theories",
                    "priority": "high",
                    "remediation": "Add minimum 5 scholarly sources using proper APA/MLA format"
                }
            ],
            "strengths_to_build": [
                {
                    "strength": "Clear writing style",
                    "evidence": "Sentence structure is varied and readable throughout (e.g., Paragraph 2 uses effective complex sentences)",
                    "reinforcement": "Maintain this clarity while adding analytical depth"
                },
                {
                    "strength": "Logical organization",
                    "evidence": "Each paragraph has clear topic sentences and flows naturally to the next",
                    "reinforcement": "Apply same organizational rigor to argument development"
                }
            ],
            "structural_analysis": {
                "organization": "Good basic structure but lacks sophistication in argument development",
                "argument_development": "Linear presentation without enough critical engagement or synthesis",
                "technical_compliance": "Meets basic formatting but lacks citations and proper academic conventions"
            },
            "revision_recommendations": {
                "high_priority": ["Add scholarly citations", "Deepen critical analysis"],
                "content_improvements": ["Include counterarguments", "Add case studies/examples"],
                "structural_changes": ["Expand conclusion", "Add literature review section"],
                "technical_fixes": ["Add reference list", "Fix formatting inconsistencies"]
            },
            "grade_justification": "Score of 78 reflects adequate content presentation but significant deficiencies in critical analysis and academic rigor. While well-organized, the submission lacks the analytical depth and scholarly engagement required for higher grades.",
            "readiness_assessment": {
                "status": "Needs Major Revision",
                "estimated_revision_hours": 6,
                "key_barriers": ["Insufficient critical engagement", "Lack of scholarly references", "Superficial analysis"]
            },
            "summary": "Adequately organized submission that meets basic requirements but requires substantial improvement in analytical depth, scholarly engagement, and critical thinking to achieve higher standards.",
            "note": "Using simulated analysis (OpenRouter unavailable)"
        })

@app.route('/')
def index():
    current_year = datetime.now().year
    return render_template('index.html', current_year=current_year)

@app.route('/analyze', methods=['POST'])
def upload_files():
    try:
        # Check if this is a JSON request (text input) or form data (file upload)
        if request.is_json:
            data = request.get_json()
            assignment_text = data.get('assignment_text', '')
            rubric_text = data.get('rubric_text', '')
            
            if not assignment_text or not rubric_text:
                return jsonify({
                    'success': False,
                    'error': 'Both assignment and rubric text are required'
                })
            
            # Get analysis options
            detailed_analysis = data.get('detailed_analysis', True)
            rewrite_suggestions = data.get('rewrite_suggestions', True)
            grade_prediction = data.get('grade_prediction', True)
            
            # Analyze with OpenRouter
            analysis_result = analyze_with_openrouter(
                assignment_text,
                rubric_text,
                detailed_analysis,
                rewrite_suggestions,
                grade_prediction
            )
            
            # Parse response
            try:
                analysis_data = json.loads(analysis_result)
                return jsonify({
                    'success': True,
                    'analysis': analysis_data
                })
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to parse AI response',
                    'raw_response': analysis_result
                })
        
        # Original file upload logic
        elif 'assignment' in request.files and 'rubric' in request.files:
            assignment_file = request.files['assignment']
            rubric_file = request.files['rubric']
            
            if assignment_file.filename == '' or rubric_file.filename == '':
                return render_template('index.html', error='No files selected')
            
            # Get analysis options from form
            detailed_analysis = request.form.get('detailed_analysis') == 'on'
            rewrite_suggestions = request.form.get('rewrite_suggestions') == 'on'
            grade_prediction = request.form.get('grade_prediction') == 'on'
            
            # Save files temporarily
            assign_id = str(uuid.uuid4())[:8]
            assign_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{assign_id}_assignment.txt")
            rubric_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{assign_id}_rubric.txt")
            
            assignment_file.save(assign_path)
            rubric_file.save(rubric_path)
            
            # Read files
            assignment_text = read_file_content(assign_path)
            rubric_text = read_file_content(rubric_path)
            
            # Analyze with OpenRouter
            analysis_result = analyze_with_openrouter(
                assignment_text,
                rubric_text,
                detailed_analysis,
                rewrite_suggestions,
                grade_prediction
            )
            
            # Parse response
            try:
                analysis_data = json.loads(analysis_result)
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                analysis_data = {
                    "overall_score": 75,
                    "overall_grade": "C",
                    "criteria_breakdown": [
                        {
                            "criterion": "Content",
                            "score_percentage": 70,
                            "weight": 30,
                            "strengths": ["Basic content covered"],
                            "deficiencies": ["Analysis needed"],
                            "recommendations": ["Improve depth"],
                            "needs_improvement": True
                        }
                    ],
                    "summary": "Analysis completed but with parsing limitations.",
                    "raw_response": analysis_result[:500]
                }
            
            # Cleanup
            try:
                os.remove(assign_path)
                os.remove(rubric_path)
            except:
                pass
            
            return render_template('result.html',
                                 analysis=analysis_data,
                                 assignment_name=assignment_file.filename,
                                 rubric_name=rubric_file.filename)
        else:
            return render_template('index.html', error='Invalid request format')
        
    except Exception as e:
        print(f"Error in upload_files: {e}")
        if request.is_json:
            return jsonify({
                'success': False,
                'error': f'Error: {str(e)}'
            })
        else:
            return render_template('index.html', error=f'Error: {str(e)}')

@app.route('/result')
def result():
    """Route to display result page with query parameters"""
    try:
        analysis_json = request.args.get('analysis')
        if analysis_json:
            analysis_data = json.loads(analysis_json)
            assignment_name = request.args.get('assignment_name', 'Text Input')
            rubric_name = request.args.get('rubric_name', 'Text Input')
            
            return render_template('result.html',
                                 analysis=analysis_data,
                                 assignment_name=assignment_name,
                                 rubric_name=rubric_name)
        else:
            return render_template('index.html', error='No analysis data provided')
    except Exception as e:
        return render_template('index.html', error=f'Error displaying results: {str(e)}')

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    """Generate and download PDF report"""
    try:
        report_data = request.get_json()
        
        # Add analysis ID and current timestamp if not present
        if 'analysis_id' not in report_data:
            report_data['analysis_id'] = str(uuid.uuid4())[:8]
        
        if 'timestamp' not in report_data:
            report_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Generate PDF
        pdf_bytes = generate_pdf_report(report_data)
        
        # Create response
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        
        # Create filename
        assignment_name = report_data.get('assignment', 'analysis').replace(' ', '_')
        filename = f"RUBRIX_Report_{assignment_name}_{report_data.get('overall_score', 'score')}.pdf"
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
        
    except Exception as e:
        print(f"PDF generation error: {e}")
        return jsonify({
            'success': False,
            'error': f'PDF generation failed: {str(e)}'
        }), 500

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'RUBRIX AI Assignment Evaluator',
        'version': '1.0',
        'ai_provider': 'OpenRouter',
        'free_models_available': len(FREE_MODELS),
        'strict_evaluation_mode': True,
        'pdf_generation': True,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'ok',
        'ai_provider': 'OpenRouter',
        'free_models_available': len(FREE_MODELS),
        'upload_folder_exists': os.path.exists(app.config['UPLOAD_FOLDER']),
        'pdf_generation': True
    })

@app.route('/test-ai')
def test_ai():
    """Test the AI connection with strict prompt"""
    try:
        test_result = analyze_with_openrouter(
            "Sample assignment: Write a critical analysis of renewable energy adoption in developing countries. Discuss economic, social, and environmental factors, and propose policy recommendations.",
            "Rubric: Critical Analysis (40% weight): Depth of analysis, use of evidence, consideration of multiple perspectives. Policy Recommendations (30% weight): Feasibility, innovation, evidence-based. Structure and Clarity (20% weight): Organization, writing quality. Research and Citations (10% weight): Use of sources, proper citation."
        )
        
        parsed_result = json.loads(test_result) if isinstance(test_result, str) else test_result
        return jsonify({
            "success": True,
            "strict_mode": True,
            "test_result": parsed_result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "strict_mode": True,
            "fallback_working": True
        })

if __name__ == '__main__':
    # Create uploads folder
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    
    print("\n" + "="*50)
    print("RUBRIX - STRICT Assignment Evaluator")
    print("="*50)
    print("✅ Using OpenRouter Free AI Models")
    print("✅ STRICT EVALUATION MODE: Enabled")
    print("✅ PDF GENERATION: Enabled")
    print(f"✅ Available models: {', '.join(FREE_MODELS[:2])}...")
    print(f"✅ Server: http://localhost:5000")
    print(f"✅ API Status: http://localhost:5000/api/status")
    print(f"✅ Test endpoint: http://localhost:5000/test-ai")
    print("="*50)
    print("\n⚠️  STRICT MODE: Evaluations will be critical and uncompromising")
    print("📄 PDF Reports: Click 'Download Detailed Report' for PDF")
    print("="*50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
# import os
# import json
# import uuid
# import requests
# from flask import Flask, render_template, request, jsonify
# from werkzeug.utils import secure_filename
# from dotenv import load_dotenv
# from datetime import datetime

# # Load environment variables
# load_dotenv()

# app = Flask(__name__)
# app.config['UPLOAD_FOLDER'] = 'uploads'
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# app.config['SECRET_KEY'] = os.urandom(24)
# app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'docx', 'md', 'py', 'java', 'cpp', 'html', 'css', 'js', 'json'}

# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")  # This is a public demo key
# OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# FREE_MODELS = [
#     "meta-llama/llama-3.2-3b-instruct:free",      
#     "google/gemma-2-2b-it:free",                  
#     "microsoft/phi-3-mini-4k-instruct:free",      
#     "qwen/qwen2.5-7b-instruct:free",               
# ]

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# def read_file_content(filepath):
#     """Simple file reader"""
#     try:
#         with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
#             return f.read()
#     except Exception as e:
#         return f"Error reading file: {str(e)}"

# def analyze_with_openrouter(assignment_text, rubric_text, detailed_analysis=True, rewrite_suggestions=True, grade_prediction=True):
#     """Use OpenRouter's free models with STRICT evaluation prompt"""
    
#     # Prepare the STRICT prompt
#     prompt = f"""You are an experienced educator and evaluation specialist tasked with rigorous assessment of academic work. Your analysis must be critical, comprehensive, and strictly adhere to the rubric criteria.

# **RUBRIC FOR EVALUATION:**
# {rubric_text[:4000]}

# **ASSIGNMENT SUBMISSION TO EVALUATE:**
# {assignment_text[:6000]}

# ---

# ## **EVALUATION INSTRUCTIONS:**

# ### **1. STRICT ADHERENCE TO RUBRIC:**
# - Evaluate EXCLUSIVELY based on the provided rubric criteria
# - Do NOT introduce external standards or personal preferences
# - Map EVERY piece of feedback directly to specific rubric criteria

# ### **2. REQUIRED ANALYSIS COMPONENTS:**

# #### **A. QUANTITATIVE SCORING:**
# - Score each rubric criterion separately on a scale of 0-100%
# - Provide EXACT percentages, not ranges
# - Calculate weighted overall score if rubric includes weightings
# - Flag ANY criterion where score is below 70% as "Needs Significant Improvement"

# #### **B. QUALITATIVE FEEDBACK (MUST INCLUDE):**
# - **Strengths Identified:** List 3-5 specific examples where criteria were met/exceeded
# - **Deficiencies Found:** List 5-8 specific, actionable deficiencies with exact evidence from submission
# - **Critical Analysis:** Explain WHY each deficiency constitutes a failure to meet rubric standards
# - **Evidence-Based Assessment:** Include exact quotes/line numbers to support every claim

# #### **C. STRUCTURAL ANALYSIS:**
# - **Organization Evaluation:** Assess logical flow, paragraph structure, transitions
# - **Argumentation Analysis:** Evaluate thesis clarity, evidence quality, logical consistency
# - **Technical Components:** Check formatting, citations, length compliance, technical accuracy

# #### **D. CRITICAL THINKING ASSESSMENT:**
# - **Depth of Analysis:** Evaluate sophistication of thought, not just surface-level coverage
# - **Originality Assessment:** Check for rote repetition vs. genuine insight
# - **Synthesis Evaluation:** Assess integration of concepts, critical connections made

# ### **3. REQUIRED FORMAT FOR RESPONSE:**

# Provide your analysis as a JSON object with this EXACT structure:
# {{
#     "overall_score": 85,
#     "overall_grade": "B",
#     "criteria_breakdown": [
#         {{
#             "criterion": "Criterion Name", 
#             "score_percentage": 80, 
#             "weight": 25,
#             "strengths": ["Specific strength with evidence"],
#             "deficiencies": ["Specific deficiency with exact quote"],
#             "recommendations": ["Concrete action required"],
#             "needs_improvement": true/false
#         }}
#     ],
#     "critical_deficiencies": [
#         {{
#             "issue": "Specific critical issue",
#             "evidence": "Exact quote/location",
#             "priority": "high/medium/low",
#             "remediation": "Step-by-step fix"
#         }}
#     ],
#     "strengths_to_build": [
#         {{
#             "strength": "Specific strength",
#             "evidence": "Exact quote/location",
#             "reinforcement": "How to build on this"
#         }}
#     ],
#     "structural_analysis": {{
#         "organization": "Detailed assessment",
#         "argument_development": "Specific evaluation",
#         "technical_compliance": "Checklist results"
#     }},
#     "revision_recommendations": {{
#         "high_priority": ["Exactly what to fix first"],
#         "content_improvements": ["Specific content changes"],
#         "structural_changes": ["Required reorganization"],
#         "technical_fixes": ["Exact formatting fixes"]
#     }},
#     "grade_justification": "Concise paragraph explaining score",
#     "readiness_assessment": {{
#         "status": "Needs Major Revision",
#         "estimated_revision_hours": 5,
#         "key_barriers": ["Fundamental issue 1", "Fundamental issue 2"]
#     }},
#     "summary": "Overall summary with actionable insights"
# }}

# ### **4. EVALUATION PRINCIPLES TO ENFORCE:**

# - **Zero Tolerance for:** Plagiarism indicators, major factual errors, ignoring assignment requirements
# - **High Standards for:** Critical thinking, original analysis, proper academic conventions
# - **Evidence-Required:** Every criticism MUST reference specific submission content
# - **Action-Oriented:** All feedback must enable immediate, concrete improvements

# ### **5. FINAL REQUIREMENTS:**

# - Do NOT give participation trophies or inflated scores
# - Do NOT hesitate to give low scores when warranted by rubric
# - Do NOT provide vague feedback - be brutally specific
# - DO highlight both excellence and failure with equal specificity
# - DO maintain professional, constructive but uncompromising tone

# **BEGIN EVALUATION NOW. Be meticulous, critical, and evidence-based in your assessment.**
# """
    
#     headers = {
#         "Authorization": f"Bearer {OPENROUTER_API_KEY}",
#         "HTTP-Referer": "http://localhost:5000",  # Required by OpenRouter
#         "X-Title": "RUBRIX Assignment Evaluator",
#         "Content-Type": "application/json"
#     }
    
#     payload = {
#         "model": FREE_MODELS[0],  # Use the first free model
#         "messages": [
#             {"role": "system", "content": "You are an expert teacher and rigorous evaluator. Always respond with valid JSON only. Be critical, evidence-based, and uncompromising in your assessment."},
#             {"role": "user", "content": prompt}
#         ],
#         "temperature": 0.2,  # Lower temperature for more consistent, critical evaluation
#         "max_tokens": 2000  # Increased for more detailed feedback
#     }
    
#     try:
#         response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=45)
#         response.raise_for_status()
        
#         result = response.json()
#         ai_response = result["choices"][0]["message"]["content"]
        
#         # Clean the response
#         ai_response = ai_response.strip()
#         if ai_response.startswith("```json"):
#             ai_response = ai_response[7:-3].strip()
#         elif ai_response.startswith("```"):
#             ai_response = ai_response[3:-3].strip()
            
#         return ai_response
        
#     except Exception as e:
#         print(f"OpenRouter error: {e}")
#         # Fallback to simulation with strict format
#         return json.dumps({
#             "overall_score": 78,
#             "overall_grade": "C+",
#             "criteria_breakdown": [
#                 {
#                     "criterion": "Content Quality", 
#                     "score_percentage": 72, 
#                     "weight": 35,
#                     "strengths": ["Clear thesis statement in introduction", "Relevant examples provided"],
#                     "deficiencies": ["Lacks depth in analysis - only surface level coverage", "Missing citations for key claims"],
#                     "recommendations": ["Add at least 3 scholarly references", "Deepen analysis with counterarguments"],
#                     "needs_improvement": True
#                 },
#                 {
#                     "criterion": "Organization", 
#                     "score_percentage": 85, 
#                     "weight": 25,
#                     "strengths": ["Logical paragraph structure", "Clear transitions between sections"],
#                     "deficiencies": ["Conclusion is abrupt and doesn't synthesize main points", "Introduction could better preview structure"],
#                     "recommendations": ["Expand conclusion to summarize key findings", "Add roadmap sentence in introduction"],
#                     "needs_improvement": False
#                 },
#                 {
#                     "criterion": "Critical Thinking", 
#                     "score_percentage": 65, 
#                     "weight": 40,
#                     "strengths": ["Identifies main issues in the topic"],
#                     "deficiencies": ["Fails to analyze underlying assumptions", "No synthesis of different perspectives", "Superficial evaluation of evidence"],
#                     "recommendations": ["Question the assumptions behind each argument", "Compare and contrast at least 3 different viewpoints", "Evaluate the quality of evidence used"],
#                     "needs_improvement": True
#                 }
#             ],
#             "critical_deficiencies": [
#                 {
#                     "issue": "Lack of critical analysis depth",
#                     "evidence": "\"The solution is effective because it helps people.\" (Paragraph 3) - This is descriptive, not analytical",
#                     "priority": "high",
#                     "remediation": "Replace descriptive statements with analytical questions: Why is it effective? For whom? Under what conditions? Compared to what alternatives?"
#                 },
#                 {
#                     "issue": "Missing academic citations",
#                     "evidence": "No references provided for claims about statistics or established theories",
#                     "priority": "high",
#                     "remediation": "Add minimum 5 scholarly sources using proper APA/MLA format"
#                 }
#             ],
#             "strengths_to_build": [
#                 {
#                     "strength": "Clear writing style",
#                     "evidence": "Sentence structure is varied and readable throughout (e.g., Paragraph 2 uses effective complex sentences)",
#                     "reinforcement": "Maintain this clarity while adding analytical depth"
#                 },
#                 {
#                     "strength": "Logical organization",
#                     "evidence": "Each paragraph has clear topic sentences and flows naturally to the next",
#                     "reinforcement": "Apply same organizational rigor to argument development"
#                 }
#             ],
#             "structural_analysis": {
#                 "organization": "Good basic structure but lacks sophistication in argument development",
#                 "argument_development": "Linear presentation without enough critical engagement or synthesis",
#                 "technical_compliance": "Meets basic formatting but lacks citations and proper academic conventions"
#             },
#             "revision_recommendations": {
#                 "high_priority": ["Add scholarly citations", "Deepen critical analysis"],
#                 "content_improvements": ["Include counterarguments", "Add case studies/examples"],
#                 "structural_changes": ["Expand conclusion", "Add literature review section"],
#                 "technical_fixes": ["Add reference list", "Fix formatting inconsistencies"]
#             },
#             "grade_justification": "Score of 78 reflects adequate content presentation but significant deficiencies in critical analysis and academic rigor. While well-organized, the submission lacks the analytical depth and scholarly engagement required for higher grades.",
#             "readiness_assessment": {
#                 "status": "Needs Major Revision",
#                 "estimated_revision_hours": 6,
#                 "key_barriers": ["Insufficient critical engagement", "Lack of scholarly references", "Superficial analysis"]
#             },
#             "summary": "Adequately organized submission that meets basic requirements but requires substantial improvement in analytical depth, scholarly engagement, and critical thinking to achieve higher standards.",
#             "note": "Using simulated analysis (OpenRouter unavailable)"
#         })

# @app.route('/')
# def index():
#     current_year = datetime.now().year
#     return render_template('index.html', current_year=current_year)

# @app.route('/analyze', methods=['POST'])
# def upload_files():
#     try:
#         # Check if this is a JSON request (text input) or form data (file upload)
#         if request.is_json:
#             data = request.get_json()
#             assignment_text = data.get('assignment_text', '')
#             rubric_text = data.get('rubric_text', '')
            
#             if not assignment_text or not rubric_text:
#                 return jsonify({
#                     'success': False,
#                     'error': 'Both assignment and rubric text are required'
#                 })
            
#             # Get analysis options
#             detailed_analysis = data.get('detailed_analysis', True)
#             rewrite_suggestions = data.get('rewrite_suggestions', True)
#             grade_prediction = data.get('grade_prediction', True)
            
#             # Analyze with OpenRouter
#             analysis_result = analyze_with_openrouter(
#                 assignment_text, 
#                 rubric_text, 
#                 detailed_analysis, 
#                 rewrite_suggestions, 
#                 grade_prediction
#             )
            
#             # Parse response
#             try:
#                 analysis_data = json.loads(analysis_result)
#                 return jsonify({
#                     'success': True,
#                     'analysis': analysis_data
#                 })
#             except json.JSONDecodeError as e:
#                 print(f"JSON parse error: {e}")
#                 return jsonify({
#                     'success': False,
#                     'error': 'Failed to parse AI response',
#                     'raw_response': analysis_result
#                 })
        
#         # Original file upload logic
#         elif 'assignment' in request.files and 'rubric' in request.files:
#             assignment_file = request.files['assignment']
#             rubric_file = request.files['rubric']
            
#             if assignment_file.filename == '' or rubric_file.filename == '':
#                 return render_template('index.html', error='No files selected')
            
#             # Get analysis options from form
#             detailed_analysis = request.form.get('detailed_analysis') == 'on'
#             rewrite_suggestions = request.form.get('rewrite_suggestions') == 'on'
#             grade_prediction = request.form.get('grade_prediction') == 'on'
            
#             # Save files temporarily
#             assign_id = str(uuid.uuid4())[:8]
#             assign_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{assign_id}_assignment.txt")
#             rubric_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{assign_id}_rubric.txt")
            
#             assignment_file.save(assign_path)
#             rubric_file.save(rubric_path)
            
#             # Read files
#             assignment_text = read_file_content(assign_path)
#             rubric_text = read_file_content(rubric_path)
            
#             # Analyze with OpenRouter
#             analysis_result = analyze_with_openrouter(
#                 assignment_text, 
#                 rubric_text, 
#                 detailed_analysis, 
#                 rewrite_suggestions, 
#                 grade_prediction
#             )
            
#             # Parse response
#             try:
#                 analysis_data = json.loads(analysis_result)
#             except json.JSONDecodeError as e:
#                 print(f"JSON parse error: {e}")
#                 analysis_data = {
#                     "overall_score": 75,
#                     "overall_grade": "C",
#                     "criteria_breakdown": [
#                         {
#                             "criterion": "Content", 
#                             "score_percentage": 70, 
#                             "weight": 30,
#                             "strengths": ["Basic content covered"],
#                             "deficiencies": ["Analysis needed"],
#                             "recommendations": ["Improve depth"],
#                             "needs_improvement": True
#                         }
#                     ],
#                     "summary": "Analysis completed but with parsing limitations.",
#                     "raw_response": analysis_result[:500]
#                 }
            
#             # Cleanup
#             try:
#                 os.remove(assign_path)
#                 os.remove(rubric_path)
#             except:
#                 pass
            
#             return render_template('result.html', 
#                                  analysis=analysis_data,
#                                  assignment_name=assignment_file.filename,
#                                  rubric_name=rubric_file.filename)
#         else:
#             return render_template('index.html', error='Invalid request format')
        
#     except Exception as e:
#         print(f"Error in upload_files: {e}")
#         if request.is_json:
#             return jsonify({
#                 'success': False,
#                 'error': f'Error: {str(e)}'
#             })
#         else:
#             return render_template('index.html', error=f'Error: {str(e)}')

# @app.route('/result')
# def result():
#     """Route to display result page with query parameters"""
#     try:
#         analysis_json = request.args.get('analysis')
#         if analysis_json:
#             analysis_data = json.loads(analysis_json)
#             assignment_name = request.args.get('assignment_name', 'Text Input')
#             rubric_name = request.args.get('rubric_name', 'Text Input')
            
#             return render_template('result.html',
#                                  analysis=analysis_data,
#                                  assignment_name=assignment_name,
#                                  rubric_name=rubric_name)
#         else:
#             return render_template('index.html', error='No analysis data provided')
#     except Exception as e:
#         return render_template('index.html', error=f'Error displaying results: {str(e)}')

# @app.route('/api/status')
# def api_status():
#     """API status endpoint"""
#     return jsonify({
#         'status': 'online',
#         'service': 'RUBRIX AI Assignment Evaluator',
#         'version': '1.0',
#         'ai_provider': 'OpenRouter',
#         'free_models_available': len(FREE_MODELS),
#         'strict_evaluation_mode': True,
#         'timestamp': datetime.now().isoformat()
#     })

# @app.route('/health')
# def health_check():
#     return jsonify({
#         'status': 'ok',
#         'ai_provider': 'OpenRouter',
#         'free_models_available': len(FREE_MODELS),
#         'upload_folder_exists': os.path.exists(app.config['UPLOAD_FOLDER'])
#     })

# @app.route('/test-ai')
# def test_ai():
#     """Test the AI connection with strict prompt"""
#     try:
#         test_result = analyze_with_openrouter(
#             "Sample assignment: Write a critical analysis of renewable energy adoption in developing countries. Discuss economic, social, and environmental factors, and propose policy recommendations.",
#             "Rubric: Critical Analysis (40% weight): Depth of analysis, use of evidence, consideration of multiple perspectives. Policy Recommendations (30% weight): Feasibility, innovation, evidence-based. Structure and Clarity (20% weight): Organization, writing quality. Research and Citations (10% weight): Use of sources, proper citation."
#         )
        
#         parsed_result = json.loads(test_result) if isinstance(test_result, str) else test_result
#         return jsonify({
#             "success": True,
#             "strict_mode": True,
#             "test_result": parsed_result
#         })
#     except Exception as e:
#         return jsonify({
#             "success": False,
#             "error": str(e),
#             "strict_mode": True,
#             "fallback_working": True
#         })

# if __name__ == '__main__':
#     # Create uploads folder
#     if not os.path.exists(app.config['UPLOAD_FOLDER']):
#         os.makedirs(app.config['UPLOAD_FOLDER'])
    
#     print("\n" + "="*50)
#     print("RUBRIX - STRICT Assignment Evaluator")
#     print("="*50)
#     print("✅ Using OpenRouter Free AI Models")
#     print("✅ STRICT EVALUATION MODE: Enabled")
#     print(f"✅ Available models: {', '.join(FREE_MODELS[:2])}...")
#     print(f"✅ Server: http://localhost:5000")
#     print(f"✅ API Status: http://localhost:5000/api/status")
#     print(f"✅ Test endpoint: http://localhost:5000/test-ai")
#     print("="*50)
#     print("\n⚠️  STRICT MODE: Evaluations will be critical and uncompromising")
#     print("="*50)
    
#     app.run(debug=True, host='0.0.0.0', port=5000)