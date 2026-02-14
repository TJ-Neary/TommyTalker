# Contributing to TommyTalker

Thank you for your interest in contributing to TommyTalker!

## Core Philosophy

1.  **Privacy First**: No audio or text data ever leaves the user's machine. All processing runs locally.
2.  **Native Performance**: Optimized for Apple Silicon via mlx-whisper (Metal-accelerated).
3.  **Code Quality**: High standards for code readability, typing, and testing.

## Development Setup

1.  **Clone the repository**
    ```bash
    git clone https://github.com/TJ-Neary/TommyTalker.git
    cd TommyTalker
    ```

2.  **Set up the environment**
    ```bash
    # Create virtual env
    python3 -m venv .venv
    source .venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

3.  **Install pre-commit hooks** (Recommended)
    ```bash
    pre-commit install
    ```

## Development Workflow

- **Branching**: Use feature branches (`feature/my-new-feature`) or fix branches (`fix/bug-description`).
- **Code Style**: We use [Ruff](https://docs.astral.sh/ruff/) and [Black](https://github.com/psf/black).
    ```bash
    # Run linter
    ruff check .
    # Format code
    black .
    ```
- **Testing**: Run the test suite before submitting PRs.
    ```bash
    pytest tests/
    ```

## Pull Request Process

1.  Ensure your code builds and passes all tests.
2.  Update documentation (`README.md`, `CLAUDE.md`) if appropriate.
3.  Submit your PR with a clear description of the problem and solution.

## Reporting Issues

Please use the GitHub Issues tab to report bugs or suggest enhancements. Provide as much context as possible, including your macOS version and hardware (e.g., M1, M3 Max).

---
**License**: By contributing, you agree that your contributions will be licensed under its MIT License.
