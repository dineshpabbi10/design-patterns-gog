# Gang of Four Design Patterns

Interactive documentation for **23 Gang of Four design patterns** tailored to microservices, React frontends, Spark data pipelines, and custom Python API clients.

## 🌐 Documentation

**[View the interactive docs →](https://dineshpabbi10.github.io/design-patterns-go4/)**

## Overview

This repository provides domain-specific implementations of all 23 Gang of Four design patterns, with real-world examples from your development experience:

- **Microservices**: Building resilient, scalable distributed systems
- **Frontend Integration**: React components communicating with backend services
- **Data Pipelines**: Spark ETL jobs and orchestration
- **API Clients**: Custom Python clients for third-party systems (like `ParagoNClient`)

## Pattern Categories

### Creational Patterns (5)
- Singleton
- Factory Method
- Abstract Factory
- Builder
- Prototype

### Structural Patterns (7)
- Adapter
- Bridge
- Composite
- Decorator
- Facade
- Flyweight
- Proxy

### Behavioral Patterns (11)
- Chain of Responsibility
- Command
- Interpreter
- Iterator
- Mediator
- Memento
- Observer
- State
- Strategy
- Template Method
- Visitor

## Getting Started

### Local Development

```bash
# Install dependencies
pip install mkdocs mkdocs-material

# View documentation locally
mkdocs serve
# Opens http://127.0.0.1:8000

# Build static site
mkdocs build
```

### Project Structure

```
design-patterns-gog/
├── creational/          # Pattern implementations
│   ├── singleton.py
│   ├── factory_method.py
│   ├── abstract_factory.py
│   ├── builder.py
│   └── prototype.py
├── structural/
│   ├── adapter.py
│   ├── bridge.py
│   ├── composite.py
│   ├── decorator.py
│   ├── facade.py
│   ├── flyweight.py
│   └── proxy.py
├── behavioral/          # To be documented
│   └── ... (11 patterns)
├── docs/               # MkDocs documentation
│   ├── index.md
│   ├── creational/
│   ├── structural/
│   └── behavioral/
└── mkdocs.yml         # Documentation configuration
```

## Usage Examples

### Builder Pattern
```python
job_spec = (SparkJobBuilder()
    .from_s3("prod-bucket", "data/customers/")
    .with_filter("status = 'active'")
    .with_windowing("tumbling", duration=3600)
    .with_resources(executors=10, memory_gb=4)
    .build())
```

### Adapter Pattern
```python
adapter = ParagoNUserAdapter(paragon_api_response)
internal_user = adapter.to_internal()
```

### Decorator Pattern
```python
client = ParagoNClient()
client = LoggingClient(client)
client = RetryingClient(client, max_retries=3)
client = MetricsClient(client, metrics_registry)
user = client.fetch_user("user_123")
```

## Learning Path

1. **Start with your problem**: Find a pattern that matches your current challenge
2. **Read the motivation**: Understand the real-world scenario
3. **Study the implementation**: See the complete working code
4. **Run the code**: Copy and adapt examples to your project
5. **Extend it**: Customize for your specific needs

## Features

- ✅ **Domain-specific examples**: All patterns tailored to your tech stack
- ✅ **Complete implementations**: Not just conceptual, but production-ready code
- ✅ **Real-world scenarios**: Examples from microservices, React, Spark, and API clients
- ✅ **Testing strategies**: Unit tests and mocking patterns included
- ✅ **Performance considerations**: Trade-offs and optimization tips
- ✅ **Interactive docs**: Fully searchable, navigable documentation site

## Contributing

Found a pattern that could use a better example for your domain? Submit a pull request!

## License

MIT License - feel free to use in your projects

---

**Last Updated**: December 2025  
**Documentation**: [https://dineshpabbi10.github.io/design-patterns-go4/](https://dineshpabbi10.github.io/design-patterns-go4/)
