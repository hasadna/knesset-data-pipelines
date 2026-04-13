# Knesset Data Pipelines

Data processing pipelines for loading, processing and visualizing data about the Israeli Knesset (Parliament).

The project uses [Apache Airflow](https://airflow.apache.org/) for orchestration and [DataFlows](https://github.com/datahq/dataflows) for data processing.

## Quickstart

Prerequisites:
* Python 3.8+ with [uv](https://pypi.org/project/uv/)
* Docker Compose

```bash
cd airflow
uv sync                              # Install dependencies
docker compose up -d db              # Start PostgreSQL
uv run knesset-data-pipelines --help  # Run the CLI
```

See [airflow/README.md](airflow/README.md) for full development setup including local Airflow and Docker Compose options.

## Project Structure

```
airflow/                          # Main project code (Airflow-based)
├── dags/                         # Airflow DAG definitions
├── knesset_data_pipelines/       # Core Python module
│   ├── cli.py                    # CLI entry point
│   ├── run_pipeline.py           # Pipeline execution engine
│   ├── kns_odata.py              # Knesset OData API client
│   └── committees/               # Committee-specific processing
├── pipelines/                    # Pipeline configurations (YAML)
├── compose.yaml                  # Docker Compose for local dev
└── pyproject.toml                # Dependencies

datapackage_pipelines_knesset/    # Legacy DPP framework (deprecated)
```

## Data Sources

The pipelines ingest data from the [Knesset OData APIs](http://main.knesset.gov.il/Activity/Info/Pages/Databases.aspx):
* **Bills & Laws** — Legislation data
* **Members** — Knesset member details and positions
* **Committees** — Meeting schedules, protocols and documents
* **Votes** — Parliamentary voting records
* **Lobbyists** — Registered lobbyist data

## Contributing

Looking to contribute? Check out the [open issues](https://github.com/hasadna/knesset-data-pipelines/issues) or the [Help Wanted](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) and [Noob Friendly](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22noob+friendly%22) labels.

Useful resources:
* [Airflow documentation](https://airflow.apache.org/docs/)
* [DataFlows documentation](https://github.com/datahq/dataflows)
* [Knesset databases info](http://main.knesset.gov.il/Activity/Info/Pages/Databases.aspx)
* [Project activities document](https://docs.google.com/document/d/1eeQRrpGYuEJKAAtShPbjFn6i2f_UmQgg1caMTEs93ic/edit)

<details>
<summary>Legacy setup (deprecated datapackage-pipelines)</summary>

The project was previously built on [datapackage-pipelines](https://github.com/frictionlessdata/datapackage-pipelines). The legacy code remains in `datapackage_pipelines_knesset/` but is no longer actively maintained. Most pipelines have been migrated to Airflow.

To run the legacy Docker image:

```bash
docker pull ghcr.io/hasadna/knesset-data-pipelines/knesset-data-pipelines-legacy
docker run -it -p 8888:8888 --entrypoint jupyter \
           -v $(pwd):/pipelines \
           ghcr.io/hasadna/knesset-data-pipelines/knesset-data-pipelines-legacy \
           lab --allow-root --ip 0.0.0.0 --no-browser \
           --NotebookApp.token= --NotebookApp.custom_display_url=http://localhost:8888/
```

</details>
