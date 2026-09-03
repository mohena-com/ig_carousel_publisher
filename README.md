# ig_carousel_app — Ollama six-slide version

This version uses the existing Ollama model instead of vLLM.

Default:
- Ollama: `http://webmaster-ai.local:11434`
- Model: `qwen3:8b`

## Run

```bash
./run.sh --input article.txt
```

or:

```bash
OLLAMA_HOST=http://localhost:11434 \
OLLAMA_MODEL=qwen3:8b \
./run.sh --input article.txt
```

Output:

```text
output_carousel/carousel.json
output_carousel/slide_1.png
...
output_carousel/slide_6.png
```

The generator normalizes common Qwen field mistakes (`headline`/`body`) into
the project's canonical schema and guarantees six slides before validation.
It does not invent source facts; missing factual content is replaced by
generic presentation-safe filler.


## Batch mode

`run.sh` processes every TXT file in `../reports/jobs/` independently.

```bash
./run.sh
```

Default output:

```text
../output_carousel/
├── <job-file-stem-1>/
│   ├── facts.json
│   ├── carousel.json
│   ├── slide_1.png
│   ├── slide_2.png
│   ├── slide_3.png
│   ├── slide_4.png
│   ├── slide_5.png
│   └── slide_6.png
├── <job-file-stem-2>/
│   └── ...
└── ...
```

You can parameterize both locations:

```bash
./run.sh   --reports-dir "/path/to/reports/jobs"   --output-dir "/path/to/output_carousel"
```

You may also pass the parent reports directory; if it contains a `jobs/`
subdirectory, the script uses that automatically.

Each TXT is processed independently. One failed TXT does not prevent the
remaining files from being attempted; the batch exits non-zero if any file
fails.
"# ig_carousel_publisher" 
