# Running SpecDetect4AI with Docker

This guide explains how to use SpecDetect4AI via Docker without installing dependencies manually. All you need is Docker installed on your machine.

---

##  Step 1 — Build the Docker Image

Clone the repository and build the Docker image from the root of the project:

```bash
git clone https://Anonymous_Repo_SpecDetect4AI
cd SpecDetect4AI
docker build -t specdetect4ai .
```

This will create a Docker image called `specdetect4ai`.

---

##  Step 2 — Prepare the Project You Want to Analyze

Make sure your target project (e.g., a Python AI/ML project) is located somewhere on your system. For example:

```bash
/Users/yourname/Documents/ai_project/
```

---

##  Step 3 — Run SpecDetect4AI on Your Project

To run the tool on your codebase, use the following command:

```bash
docker run \
  -v "path/to/AI/project":/code \
  -v $(pwd)"path/to/result/folder/output":/app/results \
  specdetect4ai \
  --input-dir /code \
  --all \
  --summary \
  --output-file /app/results/specDetect4ai_results.json
```

> Replace `"path/to/AI/project"` with the absolute path to the Python project you want to analyze.
> Replace `"path/to/result/folder/output"` with the absolute path to the folder you want the output json file.

- `--all` runs all available rules.
- `--summary` prints a per-rule detection summary.
- Results are saved in `specDetect4ai_results.json` inside the container.

---

##  Accessing the Results

To retrieve the output file from the container, use the `-v` volume binding to mount a local directory (as shown above). After the run, you will find the result in:

```bash
/path/to/your/project/specDetect4ai_results.json
```

---

##  Example

Assume your project is in:

```
/Users/Documents/mlflow-master
```

Then run:

```bash
docker run \  -v /Users/Documents/mlflow-master:/code \
  -v /Users/Documents/SpecDetect4AI:/app/results \
  specdetect4ai \
  --input-dir /code \
  --all \
  --summary \
  --output-file /app/results/specDetect4ai_results.json
```

---

##  Requirements

- Docker Desktop must be installed and running.
- Make sure Docker is available in your terminal (e.g., `docker --version` works and `docker run hello-world` too).

---

##  Tips

- The first build may take a few minutes (downloads dependencies).
- If your codebase contains a lot of files, analysis may take time (if you want to be faster, forget docker and follow (docs/usage.md)).
- You can specify selected rules using `--rules R2 R5 R11`.

---
