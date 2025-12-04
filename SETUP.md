# Setup Guide - TechFlow Automation Platform

This guide provides detailed instructions for setting up the TechFlow Automation Platform in both development and production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start with Docker](#quick-start-with-docker)
3. [Manual Setup (Without Docker)](#manual-setup-without-docker)
4. [Google Sheets Setup](#google-sheets-setup)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Docker Desktop** (recommended) or Docker Engine + Docker Compose
  - Minimum version: Docker 20.10+, Docker Compose 2.0+

### Required Accounts & Credentials

- **OpenAI API Key**
  - Recommended model: `gpt-4o-mini` (cost-effective)
  - For processing 25 dummy files (5 forms + 10 emails + 10 invoices), expected cost for **gpt-4o-mini** is < $0.005

- **Google Cloud Account**
  - For Google Sheets API access
  - Free tier available

- **Redis Instance**
  - Included in Docker Compose setup

## Quick Start with Docker

This is the **recommended** setup method for both development and demo purposes.

### Step 1: Clone the Repository

```bash
git clone https://github.com/Costopoulos/client-automation-platform.git
cd client-automation-platform
```

### Step 2: Configure Backend Environment

```bash
cd backend
cp .env.example .env
```

Edit `backend/.env` with your credentials:

```bash
# Source Directories
BASE_DIR=dummy_data

# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Google Sheets Configuration
GOOGLE_SPREADSHEET_ID=your-actual-spreadsheet-id-here

# Redis Configuration (use default for Docker Compose)
REDIS_URL=redis://redis:6379/0

# Logging
LOG_LEVEL=INFO

# API Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Step 3: Configure Frontend Environment

```bash
cd ../frontend
cp .env.example .env
```

The default values work for local Docker setup:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# WebSocket URL
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Step 4: Set Up Google Sheets Credentials

See [Google Sheets Setup](#google-sheets-setup) section below for detailed instructions.

Place your service account JSON file at:
```
backend/credentials/service-account.json
```

### Step 5: Start the Application

From the project root:

```bash
docker-compose up --build
```

This will start:
- **Backend API** on http://localhost:8000
- **Frontend Dashboard** on http://localhost:3000
- **Redis** on localhost:6379

### Step 6: Verify Installation

1. **Check Backend Health**
   ```bash
   curl http://localhost:8000/api/health
   ```
   Should return JSON with system status.

2. **Check API Documentation**
   Open http://localhost:8000/docs in your browser.

3. **Check Frontend**
   Open http://localhost:3000 in your browser.

4. **Check Logs**
   ```bash
   docker-compose logs -f backend
   docker-compose logs -f frontend
   ```

## Manual Setup (Without Docker)

If you prefer to run services directly without Docker:

### Backend Setup

1. **Install Python 3.11+**
   ```bash
   python --version  # Should be 3.11 or higher
   ```

2. **Create Virtual Environment**
   ```bash
   cd backend
   python -m venv venv

   # On macOS/Linux:
   source venv/bin/activate

   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

4. **Set Up Pre-commit Hooks** (optional, for development)
   ```bash
   pre-commit install
   ```

5. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

6. **Set Up Redis**
   - Install Redis locally or use a managed service
   - Update `REDIS_URL` in `.env`

7. **Run the Backend**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Install Node.js 18+**
   ```bash
   node --version  # Should be 18 or higher
   ```

2. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit if needed (defaults work for local setup)
   ```

4. **Run the Frontend**
   ```bash
   npm run dev
   ```

   Frontend will be available at http://localhost:3000

## Google Sheets Setup

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name: "TechFlow Automation"
4. Click "Create"

### Step 2: Enable Google Sheets API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Sheets API"
3. Click on it and click "Enable"

### Step 3: Create a Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Enter details:
   - **Name**: `techflow-automation-service`
   - **Description**: "Service account for TechFlow automation platform"
4. Click "Create and Continue"
5. Skip optional steps (no roles needed for Sheets access)
6. Click "Done"

### Step 4: Create Service Account Key

1. Click on the service account you just created
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Choose "JSON" format
5. Click "Create"
6. A JSON file will download automatically

### Step 5: Save the Credentials

1. Rename the downloaded file to `service-account.json`
2. Move it to `backend/credentials/service-account.json`
3. Ensure this file is **never committed to git** (it's in `.gitignore`)

### Step 6: Create Google Spreadsheet

1. Go to [Google Sheets](https://sheets.google.com/)
2. Create a new spreadsheet
3. Name it "TechFlow Client Data"
4. **(OPTIONAL - This step is optional, since it is performed automatically upon backend initialization)** Create two sheets:
   - **Clients** - for contact form and email data
   - **Invoices** - for invoice data

5. **(OPTIONAL - This step is optional, since it is performed automatically upon backend initialization)** Add headers to **Clients** sheet:
   ```
   Type | Source | Date | Client Name | Email | Phone | Company | Service Interest | Priority | Message | Extraction Timestamp | Confidence
   ```

6. **(OPTIONAL - This step is optional, since it is performed automatically upon backend initialization)** Add headers to **Invoices** sheet:
   ```
   Type | Source | Date | Client Name | Amount | VAT | Total Amount | Invoice Number | Extraction Timestamp | Confidence
   ```

### Step 7: Share Spreadsheet with Service Account

1. Open your spreadsheet
2. Click "Share" button
3. Copy the **service account email** from your JSON file
   - It looks like: `techflow-automation-service@project-id.iam.gserviceaccount.com`
4. Paste it in the "Add people and groups" field
5. Set permission to "Editor"
6. **Uncheck** "Notify people"
7. Click "Share"

### Step 8: Get Spreadsheet ID

1. Look at your spreadsheet URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit
   ```
2. Copy the `SPREADSHEET_ID_HERE` to `backend/.env`:
   ```bash
   GOOGLE_SPREADSHEET_ID=your-spreadsheet-id-here
   ```

## Troubleshooting

### Docker Issues

**Problem**: `docker-compose` command not found
```bash
# Try using docker compose (without hyphen)
docker compose up --build
```

**Problem**: Port already in use
```bash
# Check what's using the port
lsof -i :8000  # Backend
lsof -i :3000  # Frontend

# Stop the process or change ports in docker-compose.yml
```

**Problem**: Permission denied on credentials file
```bash
chmod 600 backend/credentials/service-account.json
```

## Support

If you encounter issues not covered here:
- Check the logs in `backend/logs/`
- Review API documentation at http://localhost:8000/docs
- Check Docker logs: `docker-compose logs -f backend` and `docker-compose logs -f frontend`
