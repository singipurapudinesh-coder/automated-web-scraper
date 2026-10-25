# Automated Web Scraper with Scheduler

A Python-based web scraping and automation project that collects web data, processes it, stores results in SQLite, and exports structured datasets to CSV and JSON. It supports scheduled execution and automated scraping through GitHub Actions.

## Overview

The **Automated Web Scraper with Scheduler** is designed to simplify recurring web data collection. It combines scraping tools, persistent local storage, command-line execution, scheduled jobs, and automated exports into a reusable workflow.

The project also uses Docker for containerization and GitHub Actions for daily automated runs.

## Key Features

- **Web scraping:** Collects structured information from supported websites.
- **HTML parsing:** Uses BeautifulSoup and lxml to extract relevant content.
- **Browser automation:** Uses Selenium for browser-driven scraping tasks.
- **Scheduled execution:** Supports recurring scraping workflows.
- **Data storage:** Stores scraped records in an SQLite database.
- **Multiple export formats:** Exports results to CSV and JSON.
- **Command-line interface:** Initialize the database, execute scraping jobs, and export results.
- **Workflow automation:** Runs selected scraping jobs through GitHub Actions.
- **Containerization:** Includes a Dockerfile for container-based execution.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core development |
| Selenium | Browser automation |
| BeautifulSoup | HTML parsing |
| lxml | HTML processing |
| SQLite | Local data storage |
| Celery | Task processing support |
| Docker | Containerization |
| GitHub Actions | Automated workflow execution |
| CSV and JSON | Data export formats |

## Project Structure

```text
automated-web-scraper/
├── .github/
│   └── workflows/
│       └── scraper.yml
├── core/
│   ├── engine.py
│   ├── parser.py
│   └── scrapers/
│       ├── quotes_scraper.py
│       ├── ecommerce_scraper.py
│       └── dynamic_generic.py
├── tasks/
│   └── celery_tasks.py
├── database.py
├── celery_app.py
├── scheduler.py
├── exporter.py
├── cli.py
├── requirements.txt
├── Dockerfile
└── README.md
```

*Note: This structure summarizes the known project files. Keep the tree aligned with the files actually present in your repository.*

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/singipurapudinesh-coder/automated-web-scraper.git
cd automated-web-scraper
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS or Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Selenium-based scraping may also require a compatible browser and browser driver.

### 4. Initialize the database

```bash
python cli.py init
```

### 5. Run a scraping job

For example, run the quotes scraper:

```bash
python cli.py run quotes_sample
```

Run the books scraper:

```bash
python cli.py run books_sample
```

### 6. Export scraped data

Export quotes data to CSV and JSON:

```bash
python cli.py export --job quotes_sample --format csv
python cli.py export --job quotes_sample --format json
```

Export books data:

```bash
python cli.py export --job books_sample --format csv
python cli.py export --job books_sample --format json
```

Check the CLI help for additional commands:

```bash
python cli.py --help
```

## Automated Execution with GitHub Actions

The project includes a GitHub Actions workflow that supports manual execution and scheduled runs.

**Current workflow configuration:**

- Manual triggering through the Actions tab.
- Daily scheduled execution at 03:00 UTC (08:30 IST).
- Automated execution of the `quotes_sample` and `books_sample` jobs.
- CSV and JSON export generation.
- Export files uploaded as a downloadable workflow artifact.
- Artifact retention configured for 14 days.

### Run the workflow manually

1. Open the repository's **Actions** tab.
2. Select the scraper workflow.
3. Click **Run workflow**.
4. Open the completed run to inspect logs and download `scraper-exports`.

Repository: [Automated Web Scraper on GitHub](https://github.com/singipurapudinesh-coder/automated-web-scraper)

> **Storage note:** GitHub Actions artifacts are temporary downloadable outputs. The workflow's SQLite database is not automatically preserved between fresh runner environments.

## Output Formats

The scraper generates structured data in:

- **CSV:** Suitable for spreadsheets, data analysis, and reporting.
- **JSON:** Suitable for Python applications, APIs, and downstream processing.

The generated exports can be downloaded from successful GitHub Actions runs.

## Docker Support

A Dockerfile is included to package the application and its dependencies into a container.

Build the image:

```bash
docker build -t automated-web-scraper .
```

Run the container:

```bash
docker run --rm automated-web-scraper
```

The default container command follows the configuration in the project's Dockerfile.

## Skills Demonstrated

- Python programming and modular application design
- Web scraping and HTML parsing
- Browser automation with Selenium
- Data processing and export automation
- SQLite database integration
- Task scheduling and workflow automation
- Docker-based application packaging
- Git and GitHub version control
- CI/CD fundamentals with GitHub Actions
- Debugging and dependency management

## Future Improvements

- Add configurable scraping targets and extraction rules.
- Implement retry logic, rate limiting, and more robust error handling.
- Add monitoring, logging, and failure notifications.
- Persist historical data across scheduled runs.
- Add data validation and automated tests to the CI workflow.
- Build a dashboard for exploring scraped datasets.

## Responsible Scraping

Use this project only on websites you are authorized to access. Respect each website's terms of service, robots.txt guidance, rate limits, and applicable privacy and data protection requirements. Avoid collecting sensitive personal information without an appropriate lawful basis.

## Author

**Singipurapu Dinesh**

GitHub: [@singipurapudinesh-coder](https://github.com/singipurapudinesh-coder)

---

*Built as a practical Python automation project demonstrating web data extraction, structured storage, scheduled execution, and workflow automation.*
