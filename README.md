# 📚 RUBRIX - AI-Powered Assignment Evaluator

<div align="center">
  <img src="static/rubrix-logo-2.png" alt="RUBRIX Logo" width="120" height="120">
  <h3>Transform Your Grading with AI</h3>
  <p>Upload assignments and rubrics for instant, detailed AI-powered feedback</p>
</div>

---

## ✨ Features

- **📁 File Upload** - Support for PDF, DOCX, TXT, code files, and more
- **📝 Text Input** - Paste content directly if you don't have files
- **🤖 AI Analysis** - Free AI models evaluate against your rubric
- **📊 Detailed Feedback** - Criteria breakdown with scores and evidence
- **📄 PDF Reports** - Download professional analysis reports
- **📦 Batch Upload** - Grade multiple assignments at once
- **🌍 Language Support** - English & Afrikaans auto-detection

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

```bash
# Clone the repository
git clone  https://github.com/TrynaGITEducated/rubrix
cd rubrix

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create uploads folder
mkdir -p uploads

# Run the app
python app.py