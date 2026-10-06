# Contributing

Thanks for helping make Text Summarization Tool clearer and more useful.

1. Fork [AliAdilQ/Text_Summarization_Tool](https://github.com/AliAdilQ/Text_Summarization_Tool) and clone your fork.
2. Create a focused branch: `git switch -c feature/your-change`.
3. Follow the setup in [README.md](README.md). Install development dependencies with `pip install -r requirements-dev.txt`.
4. Keep route handlers small, NLP logic in services, and user-facing controls accessible. Preserve the history ownership checks and CSRF protection.
5. Add meaningful coverage for changed behavior. Run `python -m pytest` and `ruff check .` before committing. Check relevant pages in both themes and on a narrow screen.
6. Commit a clear description of the change. Do not include secrets, databases, virtual environments, or model weights.
7. Push your branch and open a pull request against the original repository. Describe the problem, resulting behavior, and validation performed; attach real screenshots for visual changes.

For bugs, include reproduction steps, Python/package versions, the affected route, and a sanitized error message. Never include passwords, private document text, or environment secrets.

