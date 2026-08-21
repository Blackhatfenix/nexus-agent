# 🧠 NEXUS v3.0 — AGI Local Total

**NEXUS** é um agente autônomo avançado de elite com suporte a **web interface**, desenvolvido para Termux/Linux e Android.

## 🚀 Features

✅ **ReAct Engine** — Think → Act → Observe → Repeat  
✅ **Terminal Executivo** — Comandos shell isolados e seguros  
✅ **Busca Web** — DuckDuckGo + Bing + Google  
✅ **Web Scraping** — Extração automática de conteúdo  
✅ **Code Interpreter** — Execução Python em sandbox  
✅ **Base de Conhecimento** — Busca semântica TF-IDF  
✅ **Memória Persistente** — Consolidação curto↔longo prazo  
✅ **Auto-Melhoria** — Reflexão, auto-correção, meta-aprendizado  
✅ **Task Scheduler** — One-shot e tarefas periódicas  
✅ **Pipeline Executor** — Operações encadeadas  
✅ **Plugin System** — Extensibilidade dinâmica  
✅ **Error Recovery** — Circuit breaker com retry inteligente  
✅ **Multi-Provider LLM** — Ollama, OpenAI, Groq, Anthropic  
✅ **Auto-Configure** — Detecção automática de hardware  
✅ **Web Interface** — FastAPI + WebSocket + Modern UI  

## 📋 Requisitos

- Python 3.10+
- pip
- Para Termux: `pkg install python python-pip git`

## 🔧 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/Blackhatfenix/nexus-agent.git
cd nexus-agent
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Configure um LLM (opcional mas recomendado)

#### Opção A: Ollama (Local - Recomendado)

```bash
# Linux/Mac
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull dolphin3
ollama serve &

# Termux
pkg install ollama
ollama pull dolphin3
ollama serve &
```

#### Opção B: Groq (Gratuito - Online)

```bash
export GROQ_API_KEY=gsk_seu_token_aqui
```

#### Opção C: OpenAI

```bash
export OPENAI_API_KEY=sk_seu_token_aqui
```

## 🚀 Uso

### Modo Web (Recomendado)

```bash
python3 app.py
```

Acesse: **http://localhost:8000**

### Modo CLI

```bash
python3 NEXUS_COMPLETE.py
```

## 💬 Exemplos de Comandos

### Chat Normal
```
Você › instale vim
Você › pesquisar sobre Python
Você › liste os arquivos da pasta atual
```

### Comandos Especiais
```
/help           — Mostra ajuda
/status         — Status completo
/kb             — Base de conhecimento
/learn          — Auto-melhoria
/plugins        — Lista de plugins
/exec python_code — Executar código Python
/clear          — Limpar memória
/exit           — Sair
```

### Plugins
```
/plugin system_info   — Info do hardware
/plugin file_stats    — Estatísticas de arquivos
```

## 🌐 Web Interface

### Arquitetura

```
┌─────────────────┐
│  Frontend HTML  │ ← index.html (Chat UI)
│  CSS + JS       │   style.css (Styling)
│  WebSocket      │   script.js (Lógica)
└────────┬────────┘
         │
    ┌────▼─────┐
    │  FastAPI  │ ← app.py (Backend)
    │  WebSocket│
    │  REST API │
    └────┬──────┘
         │
    ┌────▼──────────┐
    │ NEXUS Engine   │ ← NEXUS_COMPLETE.py
    │ (Todas as IA)  │
    └────────────────┘
```

### Endpoints API

| Método | Endpoint | Descrição |
|--------|----------|----------|
| GET | `/api/status` | Status do agente |
| POST | `/api/process` | Processar mensagem |
| GET | `/api/kb` | Base de conhecimento |
| GET | `/api/learning` | Auto-melhoria stats |
| POST | `/api/clear-memory` | Limpar memória |
| GET | `/api/plugins` | Lista de plugins |
| POST | `/api/plugin` | Executar plugin |
| WS | `/ws/chat` | WebSocket para chat |

## 🔐 Segurança

### Bloqueios de Segurança

✅ Comandos perigosos bloqueados (`rm -rf /`, `mkfs`, etc)  
✅ Code sandbox com limite de recursão  
✅ Bloqueio de imports perigosos  
✅ Acesso a `/etc/`, `/proc/`, `/sys/`, `/dev/` bloqueado  
✅ Timeout de execução em todas as operações  
✅ Circuit breaker para recuperação de erros  

## 📊 Estrutura de Pastas

```
nexus-agent/
├── NEXUS_COMPLETE.py      # Motor principal do agente
├── app.py                 # Backend FastAPI
├── requirements.txt       # Dependências Python
├── static/
│   ├── index.html        # Frontend HTML
│   ├── style.css         # Styling
│   └── script.js         # Lógica JS
├── nexus_data/           # Arquivos de dados (auto-criado)
│   ├── knowledge.json    # Base de conhecimento
│   ├── auto_improve.json # Metrics de aprendizado
│   ├── memory_consolidated.json
│   └── scheduler.json
└── README.md             # Este arquivo
```

## 🎯 Perfis Adaptativos

O NEXUS detecta automaticamente o hardware e ajusta os parâmetros:

| Perfil | RAM | Max Tokens | Max Iterações | Timeout |
|--------|-----|------------|---------------|----------|
| **phone** | <3GB | 1024 | 8 | 30s |
| **server** | <12GB | 2048 | 12 | 60s |
| **cloud** | ≥12GB | 4096 | 20 | 120s |

## 🔄 Auto-Melhoria

O NEXUS aprende continuamente:

- 📊 Rastreia sucesso/falha de ações
- 🧠 Detecta padrões de erro
- 💡 Sugere estratégias alternativas
- 📈 Calcula score de confiança
- 🚨 Detecta estagnação

## 📱 Termux Quickstart

```bash
pkg update && pkg upgrade
pkg install python python-pip git
git clone https://github.com/Blackhatfenix/nexus-agent.git
cd nexus-agent
pip install -r requirements.txt
python3 app.py
```

Acesse pelo navegador Termux: `http://localhost:8000`

## 🐛 Troubleshooting

### "Módulos não encontrados"
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### "Porta 8000 já em uso"
```bash
lsof -i :8000  # Ver qual processo
kill -9 <PID>
# Ou usar outra porta
python3 app.py --port 8001
```

### "LLM não encontrado"
```bash
# Verificar Ollama
curl http://localhost:11434/api/tags

# Ou configurar Groq
export GROQ_API_KEY=seu_token
```

## 📚 Documentação

### Módulos Principais

- **KnowledgeBase** — Busca semântica com TF-IDF
- **ToolExecutor** — Execução segura de comandos shell
- **WebSearch** — Busca multi-provider (DDG, Bing)
- **CodeInterpreter** — Sandbox Python seguro
- **Memory** — Gerenciamento de memória com consolidação
- **AutoImprove** — Reflexão e meta-aprendizado
- **CircuitBreaker** — Recovery inteligente de erros
- **TaskScheduler** — Agendamento de tarefas
- **PipelineExecutor** — Execução de workflows
- **PluginManager** — Sistema de extensões
- **LLMEngine** — Multi-provider (Ollama, OpenAI, Groq)

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

MIT License — veja LICENSE para detalhes

## 🙏 Créditos

- **NEXUS** — Seu agente IA local autônomo
- Desenvolvido com ❤️ para a comunidade

## 📞 Suporte

- 🐛 Issues: [GitHub Issues](https://github.com/Blackhatfenix/nexus-agent/issues)
- 💬 Discussões: [GitHub Discussions](https://github.com/Blackhatfenix/nexus-agent/discussions)

---

**Made with 🧠 by Blackhatfenix**
