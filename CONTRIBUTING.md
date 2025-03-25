# Contribution Guidelines

## Development Setup

1. Fork the repository
2. Create feature branch:

```bash
git checkout -b feat/your-feature-name
```

3. Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

## Coding Standards

- PEP8 compliance enforced with flake8
- Type hints required for all functions
- 90%+ test coverage for new features
- Docstrings following Google style format

## Testing

```bash
# Run all tests with coverage
pytest --cov=iacgenius --cov-report=term-missing

# Run specific module tests
pytest tests/core/test_generator.py -v
```

## Pull Request Process

1. Update the README.md with new features/changes
2. Add tests for new functionality
3. Ensure all CI checks pass
4. Open PR against main branch with:
   - Description of changes
   - Screenshots for UI changes
   - Updated documentation

## Code Review Guidelines

- Prefer composition over inheritance
- Follow SOLID principles
- Keep functions under 25 lines
- Use type hints rigorously
