# Contributing to RoboOps

Thanks for your interest in this project. RoboOps is primarily a solo portfolio project, but it follows real engineering practices so it can be contributed to like any other open-source repository.

## Getting Started
1. Fork the repository and clone your fork locally.
2. 2. Create a feature branch from main, e.g. git checkout -b feat/short-description.
   3. 3. Backend setup: cd backend, create a virtual environment, pip install -r requirements.txt.
      4. 4. Frontend setup: cd frontend, npm install.
         5. 5. Full stack: cp .env.example .env then docker compose up --build from the repo root.
           
            6. ## Commit Messages
            7. This project uses Conventional Commits: feat:, fix:, docs:, test:, chore:, refactor:. Example: fix: correct pagination limit validation. Squash incremental WIP commits before opening a pull request so main keeps a clean, readable history.
           
            8. ## Running Tests
            9. - Backend unit/ORM tests: cd backend && pytest -v
               - - Backend tests require DATABASE_URL, TEST_DATABASE_URL, and MIGRATION_TEST_DATABASE_URL to be set (see .env.example); the suite fails fast with a clear error if any is missing.
                 - - Frontend: cd frontend && npm test
                  
                   - CI runs backend-tests, backend-db-tests, and frontend-tests automatically on every push and pull request (see .github/workflows/ci.yml). All three must pass before a pull request will be considered for merge.
                  
                   - ## Pull Requests
                   - - Keep PRs focused on a single change.
                     - - Add or update tests for any behavior change.
                       - - Fill out the pull request template completely.
                         - - Do not introduce authentication bypasses or hard-coded credentials.
                          
                           - ## Database Changes
                           - Any change to backend/app/models must include a corresponding Alembic migration under backend/alembic/versions/. See docs/database-schema.md for the current schema reference before adding new tables or columns.
                          
                           - ## Code of Conduct
                           - Participation in this project is governed by standard open-source etiquette: be respectful, keep feedback constructive, and assume good faith.
