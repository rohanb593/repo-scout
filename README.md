# 🔍 Repository Scout

A **Python + Streamlit** application that searches, clones, and analyses GitHub repositories to extract meaningful insights about codebases.  
Designed to help developers quickly understand unfamiliar repositories through automated analysis and structured visualisation.

---

## 🚀 Overview

**Repository Scout** allows users to:
- Search GitHub repositories programmatically
- Clone repositories locally for analysis
- Process repository metadata and structure
- Store favourites for later inspection
- Visualise repository statistics through an interactive Streamlit UI

This tool is especially useful for:
- Exploring large or unfamiliar codebases  
- Comparing repositories before contributing  
- Analysing project structure and content at scale  

---

## ✨ Features

### 🔎 Repository Search
- Search GitHub repositories using defined criteria
- Fetch repository metadata automatically

### 📂 Repository Cloning
- Clones selected repositories locally using **GitPython**
- Temporary and persistent clone directories supported

### ⭐ Favourites System
- Save repositories to:
  - `favorites.csv`
  - `advanced_favorites.csv`
- Reload and re-analyse saved repositories

### 📊 Data Analysis & Visualisation
- Repository statistics displayed using:
  - Tables
  - Charts
- Fast processing using Pandas & NumPy

### 🖥 Interactive UI
- Built with **Streamlit**
- Responsive layout
- User-friendly controls for exploration and filtering

---

## 🗂 Project Structure

project-root/
│── app.py # Main Streamlit application
│── requirements.txt # Python dependencies
│── README.md # Documentation
│
├── favorites.csv # Saved favourite repositories
├── advanced_favorites.csv # Extended favourites
│
├── favorites_repos/ # Persistently cloned repositories
└── temp_cloned_repos/ # Temporary clones for analysis


---

## 🛠 Tech Stack

| Layer | Technology |
|------|-----------|
| Language | Python 3.11.5 |
| Frontend | Streamlit |
| Data Processing | Pandas, NumPy |
| Git Operations | GitPython |
| Visualisation | Altair / Streamlit charts |
| HTTP Requests | Requests |

---

## 📦 Requirements

- **Python 3.11.5**
- Git installed and available in PATH

All required Python packages are listed in `requirements.txt`.

---

## 📥 Installation

### 1️⃣ Clone the repository
```bash
git clone <repository-url>
cd repository-scout


python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows


pip install -r requirements.txt

favorites.csv
advanced_favorites.csv

mkdir favorites_repos
mkdir temp_cloned_repos

streamlit run app.py

http://localhost:8501
