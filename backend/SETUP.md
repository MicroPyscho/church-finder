# ⛪ Church Finder — File Creation and Setup Guide

Here's all 48 files in the project, what each one does,
and why it matters. Wrote this so anyone — regardless of experience — can follow along.

---

## Create a File in VS Code

1. In the left sidebar (Explorer), right-click the correct folder
2. Click **New File**
3. Type the filename exactly as shown
4. Paste the code from the source document
5. Press **Ctrl+S** to save

---

## Round 1 — Config Files
> Config Files are the foundation. They hold settings and rules that every other file depends on. Create these first so nothing else is missing a reference.

**1. `backend/.env.example`**
Right-click the `backend` folder → New File → `.env.example`

This is a template that tells you what secret settings the app needs — things like your database password and email credentials. It is safe to share because it contains no real values. Later you will copy it to `.env` and fill in the real values. It is the starting point for anyone setting up the project for the first time.

---

**2. `backend/requirements.txt`**
Right-click `backend` → New File → `requirements.txt`

This is a shopping list of every Python library the app needs — FastAPI, the database driver, the web scraper tools, testing libraries, and code quality tools. When you run the app, Python reads this list and installs everything automatically. Without it, the backend simply cannot start.

---

**3. `backend/pyproject.toml`**
Right-click `backend` → New File → `pyproject.toml`

Sets the rules for code quality. It tells the linting tools exactly what to look for — unused variables, bad formatting, potential bugs, import order issues. Think of it as the rulebook for how the code should be written. In CI, any violation blocks the build from proceeding.

---

**4. `backend/alembic.ini`**
Right-click `backend` → New File → `alembic.ini`

Configuration file for Alembic, which is the tool that manages your database structure. Whenever you need to add or change a table in the database, Alembic handles it safely without destroying your existing data. This file tells Alembic where to find the migration scripts and how to connect to the database.

---

## Round 2 — Backend Core
> These are the engine of the project. Each file builds on the one before it — config is read by the database, the database is used by the models, the models are used by the schemas, and so on. Follow this order exactly.

**5. `backend/app/config.py`**
Right-click `backend/app` → New File → `config.py`

The brain of your settings. It reads all your environment variables from the `.env` file and makes them available to the rest of the app as a single clean object. So when any part of the code needs to know the database URL, the notification method, or whether you are in dev or production mode, it asks `config.py`. Centralising settings here means you only ever change them in one place.

---

**6. `backend/app/database.py`**
Right-click `backend/app` → New File → `database.py`

Sets up the connection to your PostgreSQL database. Every time the app needs to read or save data, it goes through this file to get a database session. It also handles cleaning up those connections properly when they are finished so the database does not get overwhelmed with open connections.

---

**7. `backend/app/models.py`**
Right-click `backend/app` → New File → `models.py`

Defines the shape of your data — what a Listing looks like (title, price, location, URL etc.), what a Deployment looks like, and what a CrawlRun looks like. Think of these as the column headers for your database tables. When you run the app for the first time, these models are used to create the actual tables in PostgreSQL.

---

**8. `backend/app/schemas.py`**
Right-click `backend/app` → New File → `schemas.py`

Similar to models but for the API layer — it defines exactly what data goes in and out of each endpoint. When the frontend asks for listings, `schemas.py` ensures the response always has the right fields in the right format. It is the contract between your frontend and backend, and FastAPI uses it to automatically validate every request and response.

---

**9. `backend/app/crawler.py`**
Right-click `backend/app` → New File → `crawler.py`

This is the heart of the whole project — the actual web scraper. It visits Rightmove, OnTheMarket, Clive Emson Auctions, and Allsop, finds church property listings across 13 counties within 2.5 hours of London, filters them by keyword (church, chapel, vestry, nave, ecclesiastical), and returns the results to be saved in the database. It runs every 3 hours automatically or whenever you trigger it manually from the dashboard.

---

**10. `backend/app/main.py`**
Right-click `backend/app` → New File → `main.py`

The front door of the entire backend. It creates the FastAPI application, connects all the route files together, and sets up middleware including CORS (which allows the frontend to talk to the backend) and GZip compression (which makes responses faster). This is the file that starts running when you launch the server with `docker compose up`.

---

## Round 3 — Backend Routers
> Routers are the individual departments of the API. Each one handles a specific area of responsibility. They are kept separate so the code stays organised and easy to maintain.

**11. `backend/app/routers/health.py`**
Right-click `backend/app/routers` → New File → `health.py`

A simple endpoint that checks if the app and database are running properly. It runs a quick test query against the database and reports back with a status of "ok" or "degraded". The frontend's green or red API badge in the top corner calls this endpoint every 30 seconds to show you at a glance whether everything is healthy.

---

**12. `backend/app/routers/listings.py`**
Right-click `backend/app/routers` → New File → `listings.py`

Handles everything to do with church listings — fetching them with search and pagination, showing crawl run history, and letting you manually trigger a new crawl from the dashboard. When you type in the search bar on the listings page, this router handles that query. When you press Run Crawl, this router kicks off the scraper in the background.

---

**13. `backend/app/routers/deployments.py`**
Right-click `backend/app/routers` → New File → `deployments.py`

Manages deployment history and the one-click rollback feature. Every time you deploy a new version of the app, this router records it. If something breaks after a deploy, you can select any previous deployment from the history and this router handles rolling the live app back to that older version — safely and with a full audit trail.

---

## Round 4 — Database Migrations
> Migrations are version control for your database. Just as Git tracks changes to your code, Alembic tracks changes to your database structure. These two files set that system up.

**14. `backend/migrations/env.py`**
Right-click `backend/migrations` → New File → `env.py`

Tells Alembic how to connect to your database and run migrations. It bridges your app's database settings with Alembic's migration engine, and handles the async connection that PostgreSQL requires. You will not need to edit this file unless you change your database setup significantly.

---

**15. `backend/migrations/versions/0001_initial.py`**
Right-click `backend/migrations/versions` → New File → `0001_initial.py`

The first and only migration — it creates all three database tables (listings, deployments, crawl_runs) along with their indexes when you run the app for the first time. If you ever need to reset or rebuild the database from scratch, running `alembic upgrade head` will replay this file and recreate everything correctly.

---

## Round 5 — Backend Tests
> Tests are your safety net. They prove the code does what it is supposed to do before it goes anywhere near a real server. These run automatically in CI on every push.

**16. `backend/tests/conftest.py`**
Right-click `backend/tests` → New File → `conftest.py`

Sets up a fake in-memory database for testing. This means your tests run fast without needing a real PostgreSQL database running locally. It also overrides the database dependency in the app so every test automatically uses the safe test database instead of the real one. It is the shared setup that all other test files rely on.

---

**17. `backend/tests/test_crawler.py`**
Right-click `backend/tests` → New File → `test_crawler.py`

Tests the crawler logic in isolation — checking that keyword filtering correctly identifies church-related listings, that listing IDs are generated consistently, that the scraper handles website failures gracefully without crashing, and that the config has sensible values. These tests run without hitting any real websites, which makes them fast and reliable in CI.

---

**18. `backend/tests/test_api.py`**
Right-click `backend/tests` → New File → `test_api.py`

Tests the actual API endpoints end-to-end — making sure listings return a properly shaped response, that bad pagination inputs are rejected with a 422 error, that deployments save correctly and mark prior ones as not-current, and that a rollback request for a non-existent deployment returns a 404. These are your confidence check before every deploy.

---

## Round 6 — Docker and Infrastructure
> Docker packages your app so it runs identically everywhere — your laptop, a staging server, and production. These files define those packages and how they are orchestrated together.

**19. `backend/Dockerfile`**
Right-click `backend` → New File → `Dockerfile`

A recipe for building your backend into a self-contained package called a Docker image that can run anywhere. It uses a two-stage build — first installing all dependencies, then copying only what is needed into a clean production image. It also creates a non-root user to run the app, which is a standard security practice.

---

**20. `docker-compose.yml`**
Right-click the root `church-finder` folder → New File → `docker-compose.yml`

The main orchestrator for local development. With one command — `docker compose up` — it starts three services together: the PostgreSQL database, the FastAPI backend with hot-reload, and the React frontend. They are all wired up to talk to each other correctly with no manual configuration needed from you.

---

**21. `docker-compose.staging.yml`**
Right-click the root folder → New File → `docker-compose.staging.yml`

The staging version of the orchestrator, configured for your pre-production server. It uses a real built Docker image instead of live source code, requires database passwords to be set as environment variables, and includes Nginx for SSL termination. This is what CI deploys to when you push to the staging branch.

---

**22. `docker-compose.prod.yml`**
Right-click the root folder → New File → `docker-compose.prod.yml`

The production version — stricter settings, no source code mounts, more conservative health checks, and every secret must be explicitly provided or the container refuses to start. This is what runs on your live server and is only deployed after manual approval in GitHub.

---

**23. `nginx/prod.conf`**
Right-click `nginx` → New File → `prod.conf`

Configures Nginx as a reverse proxy sitting in front of your app. It handles HTTPS and SSL certificate termination, adds security headers to every response, compresses responses with gzip for faster page loads, serves the React frontend as static files, and proxies API calls through to the FastAPI backend. It is the public-facing layer of the entire system.

---

**24. `scripts/rollback.sh`**
Right-click `scripts` → New File → `rollback.sh`

A shell script that runs on your server when you click the Rollback button in the dashboard. It pulls the specified older Docker image, restarts the backend container with it, then checks the health endpoint up to 10 times to confirm the rollback succeeded. If health checks keep failing it exits with an error so you know something went wrong.

---

**25. `scripts/setup_github.sh`**
Right-click `scripts` → New File → `setup_github.sh`

A one-time setup script that automates creating your GitHub repository. It initialises Git, creates the main, staging, and develop branches, pushes everything to GitHub, sets branch protection rules so CI must pass before anything can merge, creates the three deployment environments, and prints out every secret you need to add manually. Run it once at the very start of the project.

---

## Round 7 — Frontend Config
> These files set up the React app's build system, TypeScript rules, test runner, linting, and environment variables. Without them, the frontend will not build or run at all.

**26. `frontend/index.html`**
Right-click `frontend` → New File → `index.html`

The single HTML page that the entire React app lives inside. It is mostly empty — just a `<div id="root">` that React fills in dynamically. Think of it as the empty picture frame that React paints onto. It also sets the page title, viewport settings, and links to the favicon.

---

**27. `frontend/package.json`**
Right-click `frontend` → New File → `package.json`

The equivalent of `requirements.txt` but for JavaScript. It lists every frontend library the app needs — React, the router, the data-fetching library, date formatting, icons, and all the dev tools. It also defines the scripts you run during development such as `npm run dev` to start the app and `npm test` to run tests. When you run `npm install`, this file is what gets read to know what to download.

---

**28. `frontend/tsconfig.json`**
Right-click `frontend` → New File → `tsconfig.json`

The rulebook for TypeScript. TypeScript is a stricter version of JavaScript that catches mistakes before you even run the code. This file tells TypeScript how strict to be — in this project strict mode is fully on, which means type errors, unused variables, and missing return types are all caught at the coding stage rather than showing up as bugs in the browser later.

---

**29. `frontend/tsconfig.node.json`**
Right-click `frontend` → New File → `tsconfig.node.json`

A separate TypeScript config specifically for the build tool (Vite). It is needed because Vite runs in a different environment — Node.js on your machine — rather than in the browser, so it needs slightly different TypeScript settings. Without this file, the build tool itself would have type errors.

---

**30. `frontend/vite.config.ts`**
Right-click `frontend` → New File → `vite.config.ts`

Configures Vite, which is the tool that bundles and serves your React app. It sets up the dev server on port 3000, configures a proxy so API calls automatically go to your FastAPI backend without you needing to change anything, and sets up how the production build is packaged — splitting vendor code, React, and utilities into separate chunks for faster loading.

---

**31. `frontend/vitest.config.ts`**
Right-click `frontend` → New File → `vitest.config.ts`

Configures Vitest, the frontend test runner. It tells tests to run in a simulated browser environment called jsdom so React components and browser APIs can be tested without a real browser. It also sets up code coverage reporting so you can see exactly what percentage of your code is being tested and which lines are not covered.

---

**32. `frontend/.eslintrc.cjs`**
Right-click `frontend` → New File → `.eslintrc.cjs`

Sets the linting rules for all frontend TypeScript and React code. It enforces no use of lazy `any` types, no unused variables, proper React hook usage, no `console.log` left in the code, and consistent import style. In CI, the linter runs with zero warnings allowed — any violation blocks the build entirely, keeping the codebase clean.

---

**33. `frontend/.env.development`**
Right-click `frontend` → New File → `.env.development`

Environment variables used when you are running the app locally on your own machine with `npm run dev`. It points the frontend at `http://localhost:8000` for the API and sets the environment to dev, which causes a blue banner to appear at the top of the screen reminding you that the data is not real.

---

**34. `frontend/.env.staging`**
Right-click `frontend` → New File → `.env.staging`

The same idea but for the staging server. When CI builds the frontend for staging it uses this file instead, pointing the API URL at your staging server address and showing a yellow banner at the top of the screen so anyone using the staging environment knows it is pre-production.

---

**35. `frontend/.env.production`**
Right-click `frontend` → New File → `.env.production`

The production version of environment variables. It points to your live API URL and shows no banner at all, since this is the real version that end users see. These three `.env` files together mean the exact same codebase automatically behaves differently depending on where it is deployed, with no manual code changes needed.

---

## Round 8 — Frontend Source Code
> This is the visual layer of the app — everything the user actually sees and interacts with. Build it after all the config is in place so the tools that compile and check it are ready to go.

**36. `frontend/src/index.css`**
Right-click `frontend/src` → New File → `index.css`

All the visual styling for the entire app — colours, fonts, spacing, card layouts, tables, buttons, the rollback confirmation modal, responsive mobile layout, and animations like the spinning crawl button and pulsing health dot. The whole editorial brutalism look — dark header, parchment background, serif display font, monospace numbers — is defined entirely in this file. Without it the app works but looks completely unstyled.

---

**37. `frontend/src/api/client.ts`**
Right-click `frontend/src/api` → New File → `client.ts`

The single place where the frontend talks to the backend. Every API call in the app — fetching listings, triggering a crawl, loading deployment history, performing a rollback, checking health — goes through this file. Keeping all API calls in one place means if the backend URL or a response shape ever changes, you only need to update it here rather than hunting through every component in the app.

---

**38. `frontend/src/main.tsx`**
Right-click `frontend/src` → New File → `main.tsx`

The entry point of the entire React application. It is very short — it just finds the `<div id="root">` in `index.html` and mounts the whole React app inside it. Think of it as the ignition key that starts everything. React takes over from this point and handles all the rendering.

---

**39. `frontend/src/App.tsx`**
Right-click `frontend/src` → New File → `App.tsx`

Sets up the overall structure of the app — the sticky top navigation bar with the ChurchFinder logo, the three navigation links (Listings, Deployments, Crawl Runs), the health badge, the mobile hamburger menu, and the routing so clicking each link loads the right page. It also wraps everything in the React Query provider which manages all data fetching and caching across the entire app.

---

**40. `frontend/src/components/HealthBadge.tsx`**
Right-click `frontend/src/components` → New File → `HealthBadge.tsx`

The small green or red indicator in the top right corner of the app. It pings the `/health` endpoint every 30 seconds and shows "API OK" in green if everything is running correctly, or "API ⚠" in red if something is wrong. Hovering over it shows you the exact API status, database status, and app version. It is your always-visible early warning system.

---

**41. `frontend/src/components/ListingsPage.tsx`**
Right-click `frontend/src/components` → New File → `ListingsPage.tsx`

The main page of the whole app and the one you will look at most. It shows all the church property listings as cards, each with a colour-coded source tag (Rightmove, OnTheMarket, auction houses), the property title, price, location, and how long ago it was first seen. It also has the search bar to filter results by title or location, pagination to move through large result sets, and the Run Crawl button to manually kick off a new scrape immediately.

---

**42. `frontend/src/components/DeploymentsPage.tsx`**
Right-click `frontend/src/components` → New File → `DeploymentsPage.tsx`

Shows the full history of every time the app has been deployed — which version, which environment, who deployed it, and when. The key feature is the Rollback button next to each historical deployment. Clicking it opens a confirmation modal where you can optionally enter a reason, and then the app rolls the live server back to that exact older version. This is your safety net if a new deploy breaks something in production.

---

**43. `frontend/src/components/CrawlRunsPage.tsx`**
Right-click `frontend/src/components` → New File → `CrawlRunsPage.tsx`

An audit log of every time the scraper has run — when it started, how long it took, how many new listings it found, how many total it scraped across all sources, and whether there were any errors. The three stat cards at the top give a running total across all runs. Clicking View Errors on any run with issues shows you the exact error message so you can diagnose what went wrong with which scraper.

---

**44. `frontend/src/__tests__/api.test.ts`**
Right-click `frontend/src/__tests__` → New File → `api.test.ts`

Frontend unit tests that run automatically in CI. They verify that the API client functions all exist and are callable, and that the data shapes for Listing and Deployment objects have all the required fields with the correct types. They are quick sanity checks that catch any accidental breaking changes to the API client before they reach a real environment.

---

## Round 9 — CI/CD Pipeline
> CI/CD stands for Continuous Integration and Continuous Deployment. These files automate quality checks and deployment so you can ship code with confidence. They go last because they reference everything else in the project.

**45. `.gitignore`**
Right-click the root `church-finder` folder → New File → `.gitignore`

Tells Git which files to completely ignore and never track in version control. This includes your `.env` files which contain real passwords, `node_modules` which contains thousands of auto-generated files that can be reinstalled at any time, build output folders, cache directories, and log files. Without this file you would accidentally upload sensitive credentials to GitHub every time you pushed.

---

**46. `README.md`**
Right-click the root folder → New File → `README.md`

The documentation for the entire project — explains the architecture, how to run it locally in three commands, how to run tests, how to do database migrations, how rollback works, the branch strategy, and how the CI pipeline operates. Anyone new to the project reads this first to understand how everything fits together. It is also the file displayed on the GitHub repository homepage.

---

**47. `.github/workflows/ci.yml`**
Right-click `.github/workflows` → New File → `ci.yml`

The automated quality gate that runs every single time you push code to GitHub. It runs the Python linter and type checker, runs all backend unit tests, then runs the frontend type checker, linter, and build check. Then it spins up a real PostgreSQL database and runs the full integration test suite. Then it builds the Docker image and does a smoke test to confirm the container starts and the health endpoint responds. Only if every single one of those steps passes can the code be merged or deployed to any environment. This is what makes the project truly production-grade.

---

**48. `.github/workflows/preview.yml`**
Right-click `.github/workflows` → New File → `preview.yml`

Every time you open a pull request on GitHub, this workflow automatically builds the frontend for that specific branch and deploys it to a temporary live URL via Netlify. It then posts that URL as a comment directly on the pull request so anyone reviewing can click through and see exactly what the change looks like in a real browser before approving the merge. When the pull request is closed or merged the preview environment is automatically torn down and the comment is updated to show it is no longer active.

---

## What Comes Next

Once all 48 files are in place, the next steps are:

1. Copy `.env.example` to `.env` — run `cp backend/.env.example backend/.env` in your terminal
2. Fill in any values in `.env` you want to customise (notification email etc.)
3. Make sure Docker Desktop is installed and running
4. In your terminal from the root `church-finder` folder, run `docker compose up`
5. Open your browser and go to `http://localhost:3000`

The app will be live, the database will be created automatically, and you can hit Run Crawl to fetch your first batch of church listings.