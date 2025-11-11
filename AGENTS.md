# AGENTS.md for Gnome

## Project Overview

Gnome is an AI-powered file management platform designed for professionals in law, auditing, and accounting firms. It automates file organization with near-100% accuracy, enables seamless multi-ecosystem syncing (e.g., Google Drive, OneDrive), and supports semantic querying and data labeling to reduce compliance risks and boost efficiency.

### Technical Stack

- **Frontend**: HTML/CSS/JavaScript with semantic UI framework
- **Backend**: Flask (Python 3.x)
- **Database**: In-memory storage (prototype), MongoDB planned for production
- **AI/ML**: Semantic search using embeddings (Hugging Face models planned)
- **Authentication**: Flask sessions (Auth0 SSO planned for production)
- **File Processing**: PyMuPDF, Pillow, python-docx, pytesseract for multi-format support

### Architecture

The application follows a simple client-server architecture:
- Flask serves HTML templates and provides RESTful API endpoints
- User authentication via session management
- File uploads stored locally in `uploads/` directory
- Mock semantic search implemented with keyword matching (AI embeddings planned)

### Project Scope

**MVP Features**:
- User authentication (login/register)
- File upload and management
- Basic keyword-based search
- File listing with metadata
- User file isolation

**Planned Features**:
- Semantic search with AI embeddings
- Cloud storage integration (Google Drive, OneDrive)
- Advanced file organization and tagging
- Compliance and audit trail features

### Team Structure

- **Tres Frisard**: Project Lead
- **Ondrej**: Engineering Lead
- **Organization**: CS @ Harvard (CS1060 Fall 2025)

### Project Management

- **Ticketing System**: Linear (tickets scored 0-7 points with due dates)
- **Version Control**: GitHub (cs1060f25/gnome-project)
- **Deployment**: Vercel (gnome-project.vercel.app)

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/cs1060f25/gnome-project.git
cd gnome-project

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The application will be available at `http://localhost:5001`

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run with auto-reload
FLASK_ENV=development python app.py
```

## Code Style Guidelines

### Python Code Style

- Follow PEP 8 style guidelines
- Use 4-space indentation
- Use descriptive variable and function names
- Add docstrings to all functions and classes
- Use type hints where appropriate

### Example

```python
def process_file(filename: str, user_email: str) -> dict:
    """
    Process uploaded file and extract metadata.
    
    Args:
        filename: Name of the file to process
        user_email: Email of the user uploading the file
        
    Returns:
        Dictionary containing file metadata
    """
    # Implementation here
    pass
```

### Commit Message Format

All commits should follow this format:

```
HW9 TASK-<ticket-number>: <brief description>

<optional detailed description>
```

Example:
```
HW9 TASK-5: Implement AI embeddings pipeline

Added sentence-transformers integration for semantic search.
Includes vector generation and similarity scoring.
```

## Testing Instructions

### Continuous Integration Plan

The project uses GitHub Actions for continuous integration:

- **Triggers**: All pushes to main branch and pull requests
- **Test Execution**: Automated test suite runs on every commit
- **Deployment**: Successful tests on main branch trigger automatic deployment to Vercel production
- **Failed Tests**: Block production deployment; preview deployments may still be created for debugging

### How to Run Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_file_upload_search.py

# Run tests with verbose output
python -m pytest -v tests/

# Run tests with coverage report
python -m pytest --cov=. --cov-report=html tests/
```

### Test Requirements

- **Coverage Target**: Minimum 80% code coverage for search functionality
- **Test Types**:
  - Unit tests: Test individual functions and methods
  - Integration tests: Test API endpoints and workflows
  - E2E tests: Test complete user workflows (planned)

### How to Run Linters

```bash
# Run flake8 for code style checking
flake8 app.py semantic/ --max-line-length=120

# Run pylint for code quality
pylint app.py

# Run black for code formatting (check only)
black --check app.py semantic/

# Run black to auto-format code
black app.py semantic/
```

### When to Update Tests

**ALWAYS update tests when**:
- Adding new features or functionality
- Modifying existing features
- Fixing bugs (add regression tests)
- Changing API endpoints or function signatures
- Refactoring code that affects behavior

**Test-Driven Development (TDD) is encouraged**:
1. Write failing test first
2. Implement minimal code to pass the test
3. Refactor while keeping tests passing

### Instructions NOT to Change Existing Tests

**CRITICAL**: Do not modify or delete existing tests unless **explicitly requested** by the user.

Existing tests represent the expected behavior of the system. If a test is failing:

1. **First**, verify the test is correct and represents the intended behavior
2. **Then**, fix the code to make the test pass
3. **Only modify tests** if:
   - The user explicitly requests it
   - The requirements have changed and the user has approved the change
   - There is a clear bug in the test itself (discuss with team first)

### Other Testing Instructions

#### Privacy and Security Testing

- Verify user file isolation (users should only access their own files)
- Test authentication and session management
- Validate file upload size limits and allowed extensions
- Test for path traversal vulnerabilities

#### Performance Testing

- Search queries should complete within 2 seconds for typical datasets
- File uploads should handle files up to 50MB
- Application should support at least 10 concurrent users

#### Logging and Debugging

- Log all search queries with user email and results count
- Log file upload events with metadata
- Use `app.logger.info()` for informational logs
- Use `app.logger.error()` for error conditions
- Never log sensitive information (passwords, tokens)

#### Test Data

- Test files are stored in `tests/fixtures/` directory
- Use sample files representing different formats (PDF, DOCX, images)
- Clean up uploaded test files after test completion

## Pull Request Instructions

### PR Title Format

```
[TASK-<ID>] <Brief description>
```

Example: `[TASK-5] Implement AI embeddings for semantic search`

### PR Process

1. **Create feature branch**: Use format `username-hw9` or `username1-username2-hw9` for pairs
2. **Rebase on main**: Before creating PR, rebase your branch on latest main
3. **Run tests**: Ensure all tests pass locally before pushing
4. **Run linters**: Fix all linting errors before pushing
5. **Push branch**: Push to GitHub
6. **Create PR**: Include description of changes, linked tickets, and test results
7. **Code review**: Wait for review from team member
8. **Address feedback**: Make requested changes
9. **Merge**: After approval, merge to main (rebase preferred over merge commits)

### PR Description Template

```markdown
## Summary
Brief description of changes

## Related Tickets
- TASK-5: AI Embeddings
- TASK-3: Database Schema

## Changes Made
- Implemented X
- Updated Y
- Fixed Z

## Testing
- [ ] All tests passing
- [ ] Linters passing
- [ ] Tested manually
- [ ] Added new tests for new functionality

## Screenshots (if applicable)
[Add screenshots for UI changes]
```

## Feature Development Guidelines

### Ticket Requirements

Each ticket in Linear must include:

1. **Clear description** of the feature or bug
2. **Acceptance criteria** (what defines "done")
3. **Comprehensive test plan**
4. **Point estimate** (0-7 points)
5. **Due date**
6. **Assignee(s)**

### Bug Reporting

When creating bug tickets, include:

1. **Correct (desired) behavior**: What should happen
2. **Steps to reproduce**: Detailed steps to trigger the bug
3. **Actual behavior**: What actually happens (wrong behavior)
4. **Environment**: Browser, OS, Python version, etc.
5. **Link to affected feature(s)**: Reference the original feature ticket(s)

### Shipping with Known Bugs

It is acceptable to merge features with **non-blocker bugs** provided:

- The bug is properly ticketed in Linear
- The bug is linked to the feature ticket
- The bug is marked with appropriate priority
- The team is aware and has approved

**Blocker bugs** must be fixed before merging:
- Security vulnerabilities
- Data corruption issues
- Complete feature breakage
- Critical user-facing errors

## AI Development Guidelines

### When Working with AI Coding Assistants

This AGENTS.md file provides context for AI coding assistants (like GitHub Copilot, Cursor, Claude, etc.) to understand the project structure and requirements.

**AI assistants should**:
- Follow the code style guidelines above
- Always run tests after making changes
- Never modify existing tests without explicit user permission
- Add comprehensive tests for new code
- Maintain user file isolation in all features
- Log significant operations for debugging
- Handle errors gracefully with appropriate error messages

**AI assistants should NOT**:
- Commit changes without running tests first
- Skip linting or code quality checks
- Introduce security vulnerabilities (SQL injection, XSS, etc.)
- Hard-code secrets or credentials
- Remove existing functionality without confirmation
- Change API contracts without updating all callers

### Privacy Considerations

Gnome prioritizes user privacy:
- All file processing should happen locally when possible
- User files must be isolated (users cannot access other users' files)
- No sensitive information should be logged
- Cloud integration should be optional

## Current Status

### Completed Features (HW8)

- [x] User authentication (login/register)
- [x] File upload with validation
- [x] File listing and management
- [x] Basic keyword search
- [x] User file isolation
- [x] Session management

### In Progress (HW9)

- [ ] TASK-5: AI embeddings for semantic search (Tres)
- [ ] TASK-3: Database schema design (Ondrej)

### Planned Features

- [ ] Cloud storage integration (Google Drive, OneDrive)
- [ ] Advanced file tagging and organization
- [ ] Collaborative features
- [ ] Audit trail and compliance features
- [ ] Advanced semantic search with filters

## Contact and Resources

- **GitHub Repository**: https://github.com/cs1060f25/gnome-project
- **Production URL**: https://gnome-project.vercel.app
- **Google Drive**: https://drive.google.com/drive/folders/1KTE88UOWZq0-xKMG2FgmqsswxNBQ8qxP

## License

This project is part of CS1060 coursework at Harvard University.

