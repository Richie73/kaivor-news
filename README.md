# Kaivor

Kaivor is a modular AI assistant and personal operating system designed to run locally while integrating with cloud AI providers when required.

## Features

- Multi-provider AI routing
- Automatic provider failover
- Conversation memory
- Knowledge search
- PDF document reader
- Microsoft Word (.docx) reader
- Plain text document reader
- AI analytics
- Configurable models
- Modular architecture

## Requirements

- Python 3.13+
- pip

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Running

Interactive AI shell:

```bash
python kaivor.py ai
```

Run the test suite:

```bash
python kaivor.py test
```

Search your knowledge base:

```bash
python kaivor.py search <query>
```

## Project Structure

```
Kaivor/
├── commands/
├── config/
├── core/
├── knowledge/
├── modules/
├── tests/
├── requirements.txt
└── README.md
```

## Current Status

Current build: **v0.8.5 Stable**

Core systems operational:

- AI Engine
- Provider Routing
- Conversation Memory
- Knowledge Store
- Search Engine
- PDF Reader
- DOCX Reader

## Licence

Private development project.
