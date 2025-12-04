# User Guide - TechFlow Automation Platform

This guide explains how to use the TechFlow Automation Platform to process client data from various sources with human-in-the-loop oversight.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Scanning for New Files](#scanning-for-new-files)
4. [Reviewing Extractions](#reviewing-extractions)
5. [Understanding Confidence Scores](#understanding-confidence-scores)
6. [Editing Extraction Data](#editing-extraction-data)
7. [Approving Extractions](#approving-extractions)
8. [Rejecting Extractions](#rejecting-extractions)
9. [Filtering and Sorting](#filtering-and-sorting)
10. [Real-Time Notifications](#real-time-notifications)
11. [Viewing Source Documents](#viewing-source-documents)
12. [Understanding Warnings](#understanding-warnings)
13. [Working with Google Sheets](#working-with-google-sheets)
14. [Best Practices](#best-practices)
15. [Troubleshooting](#troubleshooting)

## Getting Started

### Accessing the Dashboard

1. Ensure the application is running (see [SETUP.md](SETUP.md))
2. Open your web browser
3. Navigate to http://localhost:3000
4. You should see the TechFlow Automation Dashboard

### First Time Setup

Before processing files, ensure:
- ✅ Backend is running (http://localhost:8000)
- ✅ Google Sheets is configured and shared with service account
- ✅ OpenAI API key is configured
- ✅ Source files are in the correct directories

## Dashboard Overview

The dashboard consists of several key areas:

### Header Section
- **System Statistics**: Shows counts of pending, approved, rejected items
- **Scan Button**: Triggers file scanning and extraction
- **New Items Indicator**: Shows when new items are ready for review

### Filter Bar
- **All**: Show all extraction records
- **Forms**: Show only contact form extractions
- **Emails**: Show only email extractions
- **Invoices**: Show only invoice extractions

### Extraction Cards Grid
- Displays all pending extraction records
- Each card shows extracted data, confidence score, and actions
- Cards with warnings are highlighted and sorted to the top

## Scanning for New Files

### How to Scan

1. Click the **"Scan for New Files"** button in the header
2. The system will:
   - Check `dummy_data/forms/` for HTML contact forms
   - Check `dummy_data/emails/` for EML email files
   - Check `dummy_data/invoices/` for HTML invoice files
   - Process only files that haven't been processed before
3. A loading indicator appears during scanning
4. When complete, you'll see a notification with the count of new items

### What Happens During Scanning

1. **File Discovery**: System identifies new, unprocessed files
2. **Extraction**: Each file is parsed using hybrid approach:
   - AI-powered extraction attempted first (intelligent, adaptive)
   - Rule-based parsing as fallback if AI fails or has low confidence
3. **Validation**: Extracted data is validated:
   - Email format validation
   - Phone number format validation
   - Invoice calculation verification
4. **Queue Addition**: Valid extractions are added to pending queue
5. **Notification**: You receive a real-time notification

### Scan Results

After scanning, you'll see:
- **Success message**: "Processed X files, Y new items added"
- **New extraction cards**: Appear in the dashboard
- **Statistics update**: Header shows updated pending count

## Reviewing Extractions

### Extraction Card Layout

Each extraction card displays:

**Header**:
- **Type Badge**: FORM, EMAIL, or INVOICE
- **Confidence Badge**: Color-coded confidence score
  - 🟢 Green (>80%): High confidence
  - 🟡 Yellow (60-80%): Medium confidence
  - 🔴 Red (<60%): Low confidence, needs review

**Body**:
- **Extracted Fields**: All data extracted from the document
- **Warnings** (if any): Validation issues or concerns
- **Source Information**: Original filename and date

**Footer**:
- **Approve Button**: Save to Google Sheets
- **Edit Button**: Modify extracted data
- **Reject Button**: Discard extraction
- **View Source**: See original document

### Types of Extractions

#### Contact Forms (FORM)
Displays:
- Client Name
- Email Address
- Phone Number
- Company Name
- Service Interest
- Message/Inquiry

#### Client Emails (EMAIL)
Emails can contain either client inquiry information OR invoice data. The system automatically detects the type and extracts appropriate fields.

**Client Inquiry Emails** display:
- Client Name
- Email Address
- Phone Number
- Company Name
- Service Interest
- Priority (if detected)
- Message Content

**Invoice Emails** display:
- Client Name
- Invoice Number
- Invoice Date
- Base Amount
- VAT Amount (24%)
- Total Amount
- Email context/message

#### Invoices (INVOICE)
Displays:
- Invoice Number
- Invoice Date
- Client Name
- Base Amount
- VAT Amount (24%)
- Total Amount

## Understanding Confidence Scores

### What is a Confidence Score?

The confidence score (0-100%) indicates how certain the AI is about the extracted data:

- **90-100%**: Very high confidence - data is clear and unambiguous
- **80-89%**: High confidence - data is very likely correct
- **70-79%**: Good confidence - minor uncertainties
- **60-69%**: Medium confidence - review recommended
- **Below 60%**: Low confidence - manual review required

### Factors Affecting Confidence

- **Document Structure**: Well-formatted documents score higher
- **Data Clarity**: Clear, unambiguous text scores higher
- **Field Completeness**: All required fields present scores higher
- **Validation Results**: Passing validation increases confidence

### How to Use Confidence Scores

- **High confidence (>80%)**: Quick review, likely accurate
- **Medium confidence (60-80%)**: Careful review recommended
- **Low confidence (<60%)**: Detailed review required, likely needs editing

## Editing Extraction Data

### When to Edit

Edit extractions when:
- Confidence score is low
- You notice incorrect data
- Fields are missing or incomplete
- Validation warnings appear
- Data needs formatting corrections

### How to Edit

1. Click the **"Edit"** button on an extraction card
2. An edit modal appears with all fields
3. Modify any field values as needed
4. Click **"Save Changes"** to update
5. Or click **"Cancel"** to discard changes

### Edit Modal Features

- **All fields editable**: Modify any extracted value
- **Field validation**: Real-time validation as you type
- **Original values shown**: See what was originally extracted
- **Source preview**: View original document while editing

### After Editing

- Updated values are saved to the extraction record
- Confidence score may be recalculated
- You can still approve or reject after editing
- Changes are not saved to Google Sheets until approved

## Approving Extractions

### How to Approve

1. Review the extraction data carefully
2. Verify all fields are correct
3. Click the **"Approve"** button
4. The system will:
   - Write data to appropriate Google Sheets tab
   - Remove the record from pending queue
   - Show success notification
   - Update statistics

### What Happens on Approval

1. **Data Validation**: Final validation check
2. **Sheets Write**: Data is appended to Google Sheets:
   - Contact forms and emails → "Clients" sheet
   - Invoices → "Invoices" sheet
3. **Metadata Added**: Includes extraction timestamp and confidence
4. **Queue Removal**: Record is removed from pending queue
5. **Notification**: Success message displayed

### Approval Best Practices

- ✅ Always review data before approving
- ✅ Check warnings and resolve if possible
- ✅ Verify critical fields (email, amounts, dates)
- ✅ Edit incorrect data before approving
- ✅ Approve high-confidence items quickly
- ✅ Take time with low-confidence items

## Rejecting Extractions

### When to Reject

Reject extractions when:
- Data is completely incorrect or unusable
- Document is not relevant (spam, test data)
- Extraction failed completely
- Duplicate of existing data
- Data quality is too poor to salvage

### How to Reject

1. Click the **"Reject"** button on an extraction card
2. Confirm rejection (if prompted)
3. The system will:
   - Remove the record from pending queue
   - Log the rejection
   - Update statistics
   - Show confirmation notification

### What Happens on Rejection

- Record is permanently removed from queue
- No data is written to Google Sheets
- Source file remains marked as processed (won't be re-scanned)
- Rejection is logged for audit purposes

### Rejection vs. Editing

- **Edit**: When data is mostly correct but needs fixes
- **Reject**: When data is unusable or irrelevant

## Filtering and Sorting

### Filter by Type

Use the filter bar to focus on specific document types:

1. **All**: Shows all pending extractions (default)
2. **Forms**: Shows only contact form extractions
3. **Emails**: Shows only email extractions
4. **Invoices**: Shows only invoice extractions

### Automatic Sorting

Extractions are automatically sorted:
1. **Items with warnings**: Appear first (need attention)
2. **Low confidence items**: Appear next
3. **High confidence items**: Appear last

This ensures you review problematic items first.

### Search (Future Feature)

Search functionality for finding specific clients or invoice numbers is planned for future releases.

## Real-Time Notifications

### WebSocket Connection

The dashboard maintains a real-time connection to the backend:
- **Connected**: Green indicator in header
- **Disconnected**: Red indicator, automatic reconnection attempts
- **Reconnecting**: Yellow indicator

### Notification Types

**New Items Available**:
- Toast notification appears
- Shows count of new items
- Header badge updates
- Extraction cards automatically refresh

**Approval Success**:
- Green toast notification
- Confirms data saved to Sheets
- Shows sheet row number

**Rejection Confirmed**:
- Gray toast notification
- Confirms record removed

**Errors**:
- Red toast notification
- Shows error message
- Suggests corrective action

### Notification Settings

Notifications appear in the top-right corner and:
- Auto-dismiss after 5 seconds
- Can be manually dismissed
- Stack if multiple occur
- Include action buttons when relevant

## Viewing Source Documents

### How to View Source

1. Click on an extraction card (anywhere except buttons)
2. Or click the **"View Source"** button
3. A side panel or modal opens showing:
   - Original document content
   - Extracted data side-by-side
   - Highlighting of extracted fields (if applicable)

### Source Document Types

**HTML Forms**:
- Rendered HTML with form fields
- Extracted values highlighted

**Email Files**:
- Email headers (From, To, Subject, Date)
- Email body content
- Attachments list (if any)

**HTML Invoices**:
- Rendered invoice layout
- Line items and calculations
- Extracted values highlighted

### Using Source View

- **Verify Accuracy**: Compare extracted data with original
- **Find Missing Data**: Identify fields that weren't extracted
- **Understand Context**: See full document for better decisions
- **Edit Guidance**: Know what to correct when editing

## Understanding Warnings

### Types of Warnings

**Validation Warnings** (Yellow):
- Email format invalid
- Phone number format incorrect
- Missing optional fields
- Unusual data patterns

**Calculation Errors** (Orange):
- Invoice VAT doesn't match 24% of base amount
- Total doesn't equal base + VAT
- Negative amounts
- Unrealistic values

**Extraction Errors** (Red):
- Missing required fields
- AI extraction failed
- Parsing errors
- Malformed document

### How to Handle Warnings

1. **Read the warning message** carefully
2. **View the source document** to understand the issue
3. **Edit the extraction** to correct the problem
4. **Approve** if correction is successful
5. **Reject** if data is unusable

### Warning Indicators

- **Badge on card**: Shows warning count
- **Alert box**: Displays warning details
- **Color coding**: Severity indicated by color
- **Sorting**: Warning items appear first

## Working with Google Sheets

### Sheet Structure

Your Google Spreadsheet has two sheets:

**Clients Sheet**:
- Contains data from contact forms and client emails
- Columns: Type, Source, Date, Client Name, Email, Phone, Company, Service Interest, Priority, Message, Extraction Timestamp, Confidence

**Invoices Sheet**:
- Contains data from invoice documents
- Columns: Type, Source, Date, Client Name, Amount, VAT, Total Amount, Invoice Number, Extraction Timestamp, Confidence

### Data Flow

1. **Approval**: You approve an extraction in the dashboard
2. **Routing**: System determines correct sheet based on type
3. **Appending**: Data is added as a new row at the end
4. **Metadata**: Includes extraction timestamp and confidence score
5. **Confirmation**: You receive success notification

### Viewing Approved Data

1. Open your Google Spreadsheet
2. Navigate to appropriate sheet (Clients or Invoices)
3. Scroll to bottom to see most recent entries
4. Data includes all extracted fields plus metadata

### Sheet Permissions

- Service account has **Editor** access
- You have **Owner** access
- Share with team members as needed
- Consider view-only access for most users

### Data Management

**In Google Sheets, you can**:
- Sort and filter data
- Create pivot tables
- Generate reports
- Export to other formats
- Share with stakeholders
- Create charts and visualizations

**The platform does NOT**:
- Update existing rows
- Delete data from Sheets
- Modify sheet structure
- Handle sheet formulas

## Best Practices

### Quality Assurance

- ✅ Always review before approving
- ✅ Verify critical fields (email, amounts)
- ✅ Check calculations on invoices
- ✅ Resolve warnings when possible
- ✅ Use source view for uncertain items
- ✅ Edit rather than reject when possible

### Efficiency Tips

- **Keyboard shortcuts** (future feature): Speed up workflow
- **Filter by type**: Focus on one document type at a time
- **Trust high confidence**: Quick review for >80% confidence
- **Batch similar items**: Process all forms, then emails, then invoices
- **Regular scanning**: Scan multiple times per day for timely processing

### Error Prevention

- ❌ Don't approve without reviewing
- ❌ Don't ignore warnings
- ❌ Don't rush through low-confidence items
- ❌ Don't reject without checking if editing could fix
- ❌ Don't approve duplicate data

## Troubleshooting

### Common Issues

**Problem**: No items appearing after scan
- **Solution**: Check that files exist in source directories
- **Solution**: Verify files haven't been processed before
- **Solution**: Check backend logs for errors

**Problem**: Low confidence scores on all items
- **Solution**: This is normal for some document types
- **Solution**: Review and edit as needed
- **Solution**: Consider using more powerful AI model

**Problem**: Approval fails
- **Solution**: Check Google Sheets is accessible
- **Solution**: Verify service account has Editor access
- **Solution**: Check backend logs for specific error

**Problem**: WebSocket disconnected
- **Solution**: Check backend is running
- **Solution**: Refresh the page
- **Solution**: Check network connection

**Problem**: Edit modal not saving
- **Solution**: Check all required fields are filled
- **Solution**: Verify field validation passes
- **Solution**: Check browser console for errors

**Problem**: Source document not displaying
- **Solution**: Verify source file still exists
- **Solution**: Check file permissions
- **Solution**: Try refreshing the page

### Getting Help

If you encounter issues:
1. Check the [SETUP.md](SETUP.md) troubleshooting section
2. Review backend logs in `backend/logs/`
3. Check browser console for frontend errors
4. Review API documentation at http://localhost:8000/docs
5. Contact system administrator [here](mailto:costopoulos.constantinos@gmail.com)

### Reporting Issues

When reporting issues, include:
- What you were trying to do
- What happened instead
- Error messages (if any)
- Screenshot of the issue
- Browser and version
- Timestamp of the issue

## Advanced Features

### API Access

For advanced users, the backend API is available at http://localhost:8000:
- **API Documentation**: http://localhost:8000/docs
- **OpenAPI Spec**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/api/health

## Future Features

### Bulk Operations

Planned features:
- Bulk approve high-confidence items
- Bulk reject spam/test items
- Export pending queue to CSV
- Import corrections from CSV

### Custom Integrations

Planned integrations:
- Slack notifications
- Email alerts
- Webhook support
- Custom export formats

### Keyboard Shortcuts

Planned shortcuts:
- `Space`: Approve selected item
- `E`: Edit selected item
- `R`: Reject selected item
- `S`: Scan for new files
- `F`: Toggle filters
- `Arrow keys`: Navigate between items

## Other Pages

For technical setup and configuration, see [SETUP.md](SETUP.md).

For system architecture and development, see [README.md](README.md).
