# Contributing to MARSAR

Thanks for your interest in improving MARSAR.

## Maintainers

| Name | Role | GitHub |
|---|---|---|
| Adarsh Satyajit Adhikary (Kai) | Project Lead & Lead Backend Developer | [@kaidhikary](https://github.com/kaidhikary) |
| Raj Panigrahy | Backend Developer | [@rajpanigrahy20-gif](https://github.com/rajpanigrahy20-gif) |
| Ayush Shashibhushan Tripathi | Frontend Developer | [@4yushtripathi](https://github.com/4yushtripathi) |

For anything backend-related, tag Kai or Raj. For frontend, tag Ayush.

## Getting set up

Follow the [Getting Started](README.md#getting-started) section of the README to get the backend and frontend running locally.

## Workflow

1. Open an issue describing the bug or feature before starting work on anything non-trivial.
2. Create a branch off `main`: `git checkout -b feature/short-description`.
3. Keep changes scoped — one logical change per PR.
4. Run the test suite before pushing backend changes:
   ```bash
   cd backend
   python -m pytest tests/ -v
   ```
5. Open a pull request describing what changed and why.

## Ground rules for this project

- **No real Bitcoin data or real PII** in commits, issues, or test fixtures — only synthetic/demo data.
- **No network calls from runtime code.** MARSAR is designed to run fully offline; anything that needs the network (dataset downloads, model training against external data) belongs in `backend/ml_training/` or `backend/tools/`, run in a separate connected environment, never in `app/`.
- **Don't commit secrets.** `.env` files are gitignored — copy `.env.example` and keep real keys local.
- **Don't overstate model accuracy.** The shipped model is trained on synthetic data; keep language in code/docs/comments honest about what is demonstrated vs. production-ready (see `IMPLEMENTATION_NOTES.md`).

## Code style

- Backend: standard PEP 8, type hints where practical.
- Frontend: TypeScript, existing component patterns under `frontend/src/components/`.

## License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
