# TechFlow Solutions - Client Data Automation Platform

An intelligent automation system that extracts, validates, and manages client data from multiple sources (HTML forms, email files, and invoice documents) with human-in-the-loop oversight. The platform eliminates manual data entry while maintaining accuracy through supervised approval workflows, centralizing all client and financial data in Google Sheets.

## 🎯 Overview

The TechFlow Automation Platform addresses the challenge of processing diverse client data sources by combining AI-powered extraction with human oversight. The system automatically scans for new documents, extracts structured data using LLMs, and presents results in an intuitive dashboard where users can review, edit, approve, or reject extractions before they're saved to Google Sheets.

### Key Features

- **Multi-Format Data Extraction**: Processes HTML contact forms, EML email files, and HTML invoices
- **AI-Powered Intelligence**: Uses OpenAI GPT models for adaptive extraction across varying document structures
- **Human-in-the-Loop Workflow**: No data is persisted without explicit human approval
- **Real-Time Dashboard**: WebSocket-powered live updates when new items are ready for review
- **Confidence Scoring**: AI-generated confidence scores help prioritize manual review
- **Validation & Warnings**: Automatic validation of email formats, phone numbers, and invoice calculations
- **Google Sheets Integration**: Approved data automatically syncs to organized spreadsheets
- **Error Resilience**: Graceful handling of malformed files and API failures

## 🏗️ Architecture
There are 2 diagrams.
1. The [High-level Architectural Diagram](deliverables/diagrams/img/architecture.png)
2. The [Flow Diagram](deliverables/diagrams/img/flow.png)

Both are explained in the [Report](deliverables/report.pdf).

## 🚀 Quick Start

For setup instructions, see [SETUP.md](docs/SETUP.md).

### Access the application
   - Frontend Dashboard: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 📖 Usage

See [USER_GUIDE.md](docs/USER_GUIDE.md) for detailed usage instructions.

### Quick Workflow

1. **Scan for Files**: Click "Scan for New Files" to discover unprocessed documents
2. **Review Extractions**: View extracted data with confidence scores and warnings
3. **Edit if Needed**: Click "Edit" to modify any field values
4. **Approve or Reject**: Approve to save to Google Sheets, or reject to discard
5. **Monitor Progress**: Real-time notifications when new items are ready for review

## 🛠️ Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **Pydantic** - Data validation and settings
- **BeautifulSoup4** - HTML parsing
- **OpenAI SDK** - AI-powered extraction
- **gspread** - Google Sheets integration
- **Redis** - PubSub for real-time events
- **WebSocket** - Real-time updates
- **structlog** - Structured logging

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type safety
- **TanStack Query** - Server state management
- **shadcn/ui** - Component library
- **Tailwind CSS** - Styling
- **WebSocket** - Real-time updates

## 🧪 Testing & Code Quality

### Pre-commit Hooks

The project uses automated code quality checks:

**Backend (Python):**
- **pre-commit** hooks run on every commit
- Checks: Black formatting, Ruff linting, trailing whitespace
- Runs unit tests (integration tests excluded for speed)
- Setup: `cd backend && pre-commit install`

**Frontend (TypeScript):**
- **Husky** hooks run on every commit
- Checks: ESLint, TypeScript compilation
- Runs tests on pre-push
- Automatically configured via npm install

### Backend Tests
```bash
docker compose run --rm backend pytest # Run all tests
docker compose run --rm backend pytest --cov=app               # Run with coverage
docker compose run --rm backend pytest tests/integration/      # Run integration tests only
```

### Frontend Tests
```bash
cd frontend
npm test                       # Run all tests
npm run test:coverage          # Run with coverage
```

## 📊 Data Flow

1. **File Discovery**: System scans configured directories for new files
2. **Extraction**: Files are parsed using hybrid approach:
   - AI-powered extraction attempted first (intelligent, handles variations)
   - Rule-based parsing as fallback if AI fails or confidence is low
3. **Validation**: Extracted data is validated (email format, calculations, etc.)
4. **Queue**: Valid extractions are added to pending queue
5. **Notification**: WebSocket notifies frontend of new items
6. **Review**: User reviews extraction in dashboard
7. **Approval**: User approves, edits, or rejects extraction
8. **Persistence**: Approved data is written to Google Sheets
9. **Completion**: Item is removed from queue

## 🆘 FAQ

For issues or questions:
- Check [SETUP.md](docs/SETUP.md) for setup troubleshooting
- Review [USER_GUIDE.md](docs/USER_GUIDE.md) for usage help
- Check API documentation at http://localhost:8000/docs
- Review logs in `backend/logs/` directory
