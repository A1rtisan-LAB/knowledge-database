# Contributing to Knowledge Database

First off, thank you for considering contributing to Knowledge Database! It's people like you that make Knowledge Database such a great tool.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed and expected**
- **Include screenshots if possible**
- **Include your environment details** (OS, Python version, Docker version)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a detailed description of the proposed enhancement**
- **Explain why this enhancement would be useful**
- **List any alternative solutions you've considered**

### Your First Code Contribution

Unsure where to begin? You can start by looking through these issues:
- `good first issue` - issues which should only require a few lines of code
- `help wanted` - issues which need extra attention

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the existing code style
6. Issue that pull request!

## Development Process

### Setting Up Your Development Environment

```bash
# Clone your fork
git clone https://github.com/your-username/knowledge-database.git
cd knowledge-database

# Add upstream remote
git remote add upstream https://github.com/original/knowledge-database.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run the application locally
./scripts/start-local.sh
```

### Code Style

We use several tools to maintain code quality:

- **Black** for Python code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking

Run all checks:
```bash
# Format code
black app/ tests/
isort app/ tests/

# Run linting
flake8 app/ tests/
mypy app/

# Or run all at once
make lint
```

### Testing

Write tests for any new functionality:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_auth.py

# Run tests in parallel
pytest -n auto
```

### Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

Examples:
```
feat: add Korean language support for search
fix: resolve JWT token expiration issue
docs: update API documentation for v2 endpoints
```

### Documentation

- Update README.md if needed
- Add docstrings to all public functions and classes
- Update API documentation for any endpoint changes
- Keep both English and Korean documentation in sync

### Branch Naming Convention

- `feature/` - New features (e.g., `feature/add-export-api`)
- `fix/` - Bug fixes (e.g., `fix/search-pagination`)
- `docs/` - Documentation updates (e.g., `docs/update-api-guide`)
- `refactor/` - Code refactoring (e.g., `refactor/optimize-queries`)

## Review Process

1. **Automated Checks**: All PRs must pass:
   - Unit tests
   - Integration tests
   - Code style checks
   - Security scanning

2. **Code Review**: At least one maintainer review required
   - Code quality
   - Performance implications
   - Security considerations
   - Documentation completeness

3. **Testing**: Manual testing for UI changes

## Release Process

1. Update version in `VERSION` file
2. Update CHANGELOG.md
3. Create release PR
4. After merge, tag release
5. Deploy to staging
6. Deploy to production

## Community

- **Discord**: [Join our Discord](https://discord.gg/knowledge-db)
- **Forum**: [Community Forum](https://forum.knowledge-db.com)
- **Twitter**: [@KnowledgeDB](https://twitter.com/knowledgedb)

## Recognition

Contributors are recognized in:
- CHANGELOG.md
- GitHub contributors page
- Project documentation

## Questions?

Feel free to:
- Open an issue for questions
- Reach out on Discord
- Email the maintainers at contribute@knowledge-db.com

Thank you for contributing! 🎉