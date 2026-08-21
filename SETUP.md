# 🚀 Guia de Setup NEXUS Web

## Passo 1: Preparação

### Linux/Mac
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip git
```

### Termux (Android)
```bash
pkg update && pkg upgrade
pkg install python python-pip git curl
```

### Windows
Baixe Python de https://python.org e instale pip

## Passo 2: Clone e Configure

```bash
git clone https://github.com/Blackhatfenix/nexus-agent.git
cd nexus-agent
pip install -r requirements.txt
```

## Passo 3: Configure um LLM

### Opção 1: Ollama (Melhor para offline)

**Linux/Mac:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull dolphin3
ollama serve &
```

**Termux:**
```bash
pkg install ollama
ollama pull dolphin3
ollama serve &
```

### Opção 2: Groq (Gratuito online)

```bash
export GROQ_API_KEY=gsk_seu_token_aqui
export GROQ_MODEL=llama-3.3-70b-versatile
```

Obtenha a chave em: https://console.groq.com

### Opção 3: OpenAI

```bash
export OPENAI_API_KEY=sk_seu_token_aqui
export OPENAI_MODEL=gpt-4o-mini
```

## Passo 4: Execute

```bash
python3 app.py
```

Acesse: **http://localhost:8000**

## 🌐 Acesso Remoto

Para acessar de outro computador:

```bash
python3 app.py --host 0.0.0.0 --port 8000
```

Daí acesse: `http://seu_ip:8000`

## 📱 Termux com Nginx (Production)

### 1. Instale Nginx
```bash
pkg install nginx
```

### 2. Configure `/data/data/com.termux/files/usr/etc/nginx/nginx.conf`

```nginx
worker_processes auto;
error_log /data/data/com.termux/files/usr/var/log/nginx/error.log;
pid /data/data/com.termux/files/usr/var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    access_log /data/data/com.termux/files/usr/var/log/nginx/access.log;
    
    upstream nexus_backend {
        server localhost:8000;
    }
    
    server {
        listen 80;
        server_name localhost;
        
        location / {
            proxy_pass http://nexus_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        
        location /ws/chat {
            proxy_pass http://nexus_backend/ws/chat;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

### 3. Inicie o Nginx
```bash
nginx
```

Acesse: `http://localhost`

## ⚙️ Variáveis de Ambiente

```bash
# LLM
export OLLAMA_URL="http://localhost:11434/api/generate"
export OLLAMA_MODEL="dolphin3"
export GROQ_API_KEY="gsk_..."
export OPENAI_API_KEY="sk_..."

# Server
export HOST="0.0.0.0"
export PORT="8000"
```

## 🔍 Verificar Status

```bash
# API Status
curl http://localhost:8000/api/status | jq

# Ollama (se usar Ollama)
curl http://localhost:11434/api/tags
```

## 🧪 Teste a Primeira Vez

1. Abra http://localhost:8000
2. Clique em "Status" para verificar
3. Digite: "oi" e envie
4. Veja a resposta do NEXUS
5. Teste: "/plugin system_info"

## 🚨 Troubleshooting

### Erro: Port already in use
```bash
lsof -i :8000
kill -9 <PID>
```

### Erro: ModuleNotFoundError
```bash
pip install -r requirements.txt --force-reinstall --upgrade
```

### Erro: LLM not available
```bash
# Verifique Ollama
curl http://localhost:11434/api/tags

# Ou use Groq
export GROQ_API_KEY=seu_token
```

### Erro: WebSocket connection refused
- Certifique-se que o FastAPI está rodando
- Verifique firewall/proxy
- Tente acessar /api/status primeiro

## 📊 Monitoramento

### Ver logs em tempo real
```bash
tail -f nexus_data/error_log.json
```

### Verificar uso de recursos
```bash
top
free -h
df -h
```

## 🔐 Produção (Avançado)

### Com Gunicorn + Nginx

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app &
```

### Com Docker (se disponível)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python3", "app.py"]
```

```bash
docker build -t nexus .
docker run -p 8000:8000 nexus
```

---

✅ Pronto! NEXUS está rodando.
