# 🚀 Guia de Deployment — NEXUS

## Opções de Hospedagem

### 1️⃣ **Render** (Recomendado - Gratuito)

**Prós:**
- ✅ Gratuito com limite generoso
- ✅ Deploy automático via GitHub
- ✅ Suporte a Python/Node/Go
- ✅ WebSocket nativo
- ✅ Sem cartão de crédito para free tier

**Passo a passo:**

1. Vá para [render.com](https://render.com)
2. Clique "New +" → "Web Service"
3. Conecte seu repositório GitHub
4. Preencha:
   - **Name:** `nexus-agent`
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python3 app.py`
   - **Plan:** Free
5. Clique "Deploy Service"

**URL:** `https://seu-nome-da-app.onrender.com`

---

### 2️⃣ **Railway** (Fácil - Gratuito)

**Prós:**
- ✅ Super fácil (detecta automaticamente)
- ✅ Free $5/mês
- ✅ Sem configuração necessária
- ✅ GitHub Actions nativo

**Passo a passo:**

1. Vá para [railway.app](https://railway.app)
2. Login com GitHub
3. Clique "New Project"
4. "Deploy from GitHub repo"
5. Selecione `nexus-agent`
6. Railway faz tudo automaticamente

**URL:** Gerada automaticamente no dashboard

---

### 3️⃣ **Vercel** (Super Rápido)

**Prós:**
- ✅ Suporte a Python
- ✅ Deploy em segundos
- ✅ Gratuito
- ✅ Incredibly fast

**Passo a passo:**

1. Vá para [vercel.com](https://vercel.com)
2. Clique "Add New" → "Project"
3. "Import Git Repository"
4. Selecione seu fork de `nexus-agent`
5. Vercel detecta automaticamente
6. Clique "Deploy"

**URL:** `https://seu-projeto.vercel.app`

---

### 4️⃣ **Heroku** (Antigo mas funciona)

**Passo a passo:**

```bash
# Instale Heroku CLI
which heroku || curl https://cli-assets.heroku.com/install.sh | sh

# Login
heroku login

# Crie app
heroku create seu-app-name

# Deploy
git push heroku master

# Ver logs
heroku logs --tail
```

**URL:** `https://seu-app-name.herokuapp.com`

---

### 5️⃣ **Docker + Any Cloud**

**Build Docker:**
```bash
docker build -t nexus-agent .
docker run -p 8000:8000 nexus-agent
```

**Deploy em:**
- AWS ECS
- Google Cloud Run
- DigitalOcean App Platform
- Azure Container Instances

---

## 🌐 GitHub Pages (Estático)

Para hospedar apenas o frontend estático:

1. Vá para Settings → Pages
2. Source: `Deploy from a branch`
3. Branch: `master`, folder: `/static`
4. Salve
5. URL: `https://seu-usuario.github.io/nexus-agent`

**Limitação:** Sem backend (sem busca web, sem código Python)

---

## 🔑 Variáveis de Ambiente

Configure na plataforma escolhida:

```bash
# Ollama (local)
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=dolphin3

# Groq (gratuito online)
GROQ_API_KEY=gsk_seu_token_aqui
GROQ_MODEL=llama-3.3-70b-versatile

# OpenAI
OPENAI_API_KEY=sk_seu_token_aqui
OPENAI_MODEL=gpt-4o-mini
```

---

## 📊 Comparação de Plataformas

| Plataforma | Free Tier | Setup | WebSocket | Python | Recomendação |
|-----------|-----------|-------|-----------|--------|---------------|
| **Render** | Sim | ⭐⭐⭐ | ✅ | ✅ | 🏆 Melhor |
| **Railway** | $5/mês | ⭐⭐⭐⭐⭐ | ✅ | ✅ | 2º Lugar |
| **Vercel** | Sim | ⭐⭐⭐⭐ | ❌ | ✅ | 3º Lugar |
| **Heroku** | Não | ⭐⭐⭐ | ✅ | ✅ | Pago |
| **GitHub Pages** | Sim | ⭐⭐⭐⭐⭐ | ❌ | ❌ | Frontend só |

---

## 🐛 Troubleshooting

### "Port already in use"
```bash
lsof -i :8000
kill -9 <PID>
```

### "Module not found"
```bash
pip install -r requirements.txt --upgrade
```

### "WebSocket connection failed"
- Verifique firewall
- WebSocket pode não funcionar em alguns proxies
- Teste com API REST primeiro

### "LLM not available"
```bash
# Configurar via env var
export GROQ_API_KEY=seu_token
# ou
export OPENAI_API_KEY=seu_token
```

---

## ✅ Checklist de Deploy

- [ ] Repositório sincronizado
- [ ] `requirements.txt` atualizado
- [ ] Variáveis de ambiente configuradas
- [ ] Testou localmente com `python3 app.py`
- [ ] Conectou GitHub a plataforma
- [ ] Deploy iniciado
- [ ] Testou URL do app
- [ ] Testou endpoint `/api/status`
- [ ] Testou WebSocket `/ws/chat`
- [ ] Configurou LLM (Groq/OpenAI/Ollama)

---

## 🚀 Deploy Rápido (Render)

O jeito mais fácil:

```bash
# 1. Make sure your repo is public
# 2. Go to https://render.com
# 3. Connect GitHub
# 4. Select nexus-agent repo
# 5. Render auto-detects and deploys
# 6. Your app is live!
```

---

**Pronto! Seu NEXUS está no ar! 🚀**
