# Contributing to ChatGPT-Style Voice Assistant

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## 🎯 Ways to Contribute

- **Bug Reports** - Found a bug? Open an issue with detailed reproduction steps
- **Feature Requests** - Have an idea? Describe it in a new issue
- **Code Contributions** - Submit pull requests for bug fixes or new features
- **Documentation** - Improve README, comments, or add examples
- **Testing** - Add new test cases or improve existing ones
- **Performance** - Optimize code for better speed or memory usage

## 🚀 Getting Started

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/ChatPythonAgentDemo.git
cd ChatPythonAgentDemo
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest black flake8 mypy
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

## 📝 Development Guidelines

### Code Style

- **Follow PEP 8** - Python style guide
- **Use type hints** - Add type annotations where possible
- **Write docstrings** - Document all functions and classes
- **Keep it simple** - Prefer clarity over cleverness

```python
def example_function(param: str, count: int = 5) -> bool:
    """
    Brief description of what the function does.
    
    Args:
        param: Description of param
        count: Description of count (default: 5)
    
    Returns:
        Description of return value
    """
    # Implementation
    return True
```

### Code Formatting

```bash
# Format code with Black
black voice_assistant_VAD.py

# Check linting
flake8 voice_assistant_VAD.py

# Type checking
mypy voice_assistant_VAD.py
```

### Testing

**All contributions must include tests!**

```bash
# Run all tests
python3 run_all_chatgpt_parity_tests.py

# Run specific test suite
python3 test_performance.py

# Add new tests to appropriate file
# - test_voice_assistant_VAD_comprehensive.py for component tests
# - test_error_recovery.py for error handling
# - test_performance.py for performance benchmarks
```

### Writing Tests

```python
def test_your_new_feature():
    """Test description."""
    print("\n=== Test: Your New Feature ===")
    
    try:
        # Setup
        # ...
        
        # Execute
        result = your_function()
        
        # Assert
        if result:
            print("✓ Test passed")
            return True
        else:
            print("✗ Test failed")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
```

## 🔍 Pull Request Process

### 1. Make Your Changes

- Write clean, documented code
- Add tests for new functionality
- Update documentation if needed

### 2. Test Your Changes

```bash
# Run test suite
python3 run_all_chatgpt_parity_tests.py

# Verify all automated tests pass
# Manual tests should be noted in PR description
```

### 3. Commit Your Changes

```bash
# Use clear, descriptive commit messages
git add .
git commit -m "feat: Add custom wake word detection"
# or
git commit -m "fix: Resolve VAD false positive issue"
# or
git commit -m "docs: Update installation instructions"
```

**Commit Message Format:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding/updating tests
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `style:` - Code style changes (formatting, etc.)

### 4. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 5. Open a Pull Request

1. Go to the original repository on GitHub
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill out the PR template:
   - **Description** - What does this PR do?
   - **Motivation** - Why is this change needed?
   - **Testing** - How was it tested?
   - **Screenshots** - If applicable

### 6. Code Review

- Address reviewer feedback promptly
- Make requested changes in new commits
- Keep discussion professional and constructive

## 🐛 Bug Reports

**Good bug reports include:**

- **Clear title** - Summarize the issue
- **Environment** - OS, Python version, package versions
- **Steps to reproduce** - Exact steps to trigger the bug
- **Expected behavior** - What should happen
- **Actual behavior** - What actually happens
- **Error messages** - Full error output
- **Screenshots** - If helpful

**Example:**

```markdown
## Bug: VAD not detecting whisper speech

**Environment:**
- OS: macOS 14.0
- Python: 3.11.5
- webrtcvad: 2.0.10

**Steps to Reproduce:**
1. Start voice assistant
2. Whisper quietly into microphone
3. No speech detected

**Expected:** Whisper should be detected
**Actual:** Recording times out

**Error:** None, just timeout

**Workaround:** Use VAD aggressiveness level 1 instead of 3
```

## ✨ Feature Requests

**Good feature requests include:**

- **Use case** - Why is this feature needed?
- **Description** - What should it do?
- **Examples** - Show example usage
- **Alternatives** - What are other solutions?
- **Priority** - How important is this?

## 📋 Areas Needing Contribution

### High Priority
- [ ] Multi-language support
- [ ] Custom wake word detection
- [ ] Streaming audio responses
- [ ] Better echo cancellation

### Medium Priority
- [ ] Web interface
- [ ] Voice cloning
- [ ] Emotion detection
- [ ] Performance optimizations

### Documentation
- [ ] Video tutorials
- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Troubleshooting guide

## 🧪 Test Coverage Goals

- **Unit tests** - Cover all functions
- **Integration tests** - Test component interactions
- **Performance tests** - Benchmark critical paths
- **Error handling** - Test all failure modes
- **Edge cases** - Test boundary conditions

## 💬 Communication

- **Issues** - For bugs, features, and questions
- **Discussions** - For general questions and ideas
- **Pull Requests** - For code contributions

## 📚 Resources

- [Python Style Guide (PEP 8)](https://pep8.org/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [WebRTC VAD](https://github.com/wiseman/py-webrtcvad)
- [Project Test Documentation](CHATGPT_PARITY_TESTS.md)

## ⚖️ License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You!

Every contribution, no matter how small, helps make this project better. We appreciate your time and effort!

---

**Questions?** Open an issue or reach out to the maintainers.
