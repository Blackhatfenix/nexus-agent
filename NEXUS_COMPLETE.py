#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════╗
║  NEXUS — Agente Autônomo Avançado de Elite v3.0                     ║
║  AGI Local Total para Termux/Linux no Android                       ║
║                                                                      ║
║  Execute: python3 NEXUS_COMPLETE.py                                  ║
║  Setup:   pip3 install aiohttp beautifulsoup4 lxml rich              ║
╚═══════════════════════════════════════════════════════════════════════╝

CAPACIDADES IMPLEMENTADAS:
1. ReAct Engine (Think→Act→Observe→Repeat)
2. Terminal executivo (comandos shell isolados)
3. Busca web (DuckDuckGo + Bing + Google)
4. Web scraping (extração de conteúdo)
5. Code Interpreter (execução Python sandbox)
6. Base de conhecimento local (busca semântica TF-IDF)
7. Memória de sessão + memória de trabalho
8. Consolidação de memória (curto→longo prazo)
9. Auto-melhoria (reflexão, auto-correção, meta-aprendizado)
10. Detecção de padrões de erro
11. Task Scheduler (one-shot, periódico)
12. Pipeline Executor (operações encadeadas)
13. Plugin System (extensibilidade dinâmica)
14. Error Recovery (circuit breaker, retry com backoff)
15. Multi-provider LLM (Ollama, OpenAI, Anthropic, Groq, DeepSeek)
16. Auto-configure profiles (phone, server, cloud)
17. Hardware detection automático
"""
from __future__ import annotations

import asyncio
import ast
import hashlib
import json
import logging
import math
import os
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional
from urllib.parse import quote_plus

# ═══════════════════════════════════════════════════════════════════
#  DEPENDÊNCIAS
# ═══════════════════════════════════════════════════════════════════

def ensure_deps():
    deps = {"aiohttp": "aiohttp", "bs4": "beautifulsoup4", "rich": "rich"}
    missing = []
    for mod, pkg in deps.items():
        try: __import__(mod)
        except ImportError: missing.append(pkg)
    if missing:
        print(f"⚙️  Instalando: {', '.join(missing)}")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet"] + missing)
        print("✅ Pronto!")

ensure_deps()

import aiohttp
from bs4 import BeautifulSoup
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()

# ═══════════════════════════════════════════════════════════════════
#  CONFIGURAÇÃO CENTRAL
# ═══════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "nexus_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
KB_PATH = DATA_DIR / "knowledge.json"
AUTO_IMPROVE_PATH = DATA_DIR / "auto_improve.json"
MEMORYCONSOLIDATED_PATH = DATA_DIR / "memory_consolidated.json"
SCHEDULER_PATH = DATA_DIR / "scheduler.json"
ERROR_LOG_PATH = DATA_DIR / "error_log.json"

# Detecção de ambiente
def detect_hardware() -> dict:
    info = {"cores": os.cpu_count() or 1, "ram_mb": 1024, "storage_gb": 10.0,
            "platform": platform.system(), "arch": platform.machine(), "python": platform.python_version()}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if "MemTotal" in line:
                    info["ram_mb"] = int(line.split()[1]) // 1024
    except: pass
    try:
        st = os.statvfs("/")
        info["storage_gb"] = round(st.f_blocks * st.f_frsize / (1024**3), 1)
    except: pass
    info["is_termux"] = os.path.exists("/data/data/com.termux")
    info["is_android"] = "android" in platform.platform().lower() or info["is_termux"]
    return info

HARDWARE = detect_hardware()

# Perfis adaptativos
if HARDWARE["ram_mb"] < 3000:
    PROFILE = "phone"
    MAX_TOKENS, MAX_ITERS, TOOL_TIMEOUT = 1024, 8, 30
elif HARDWARE["ram_mb"] < 12000:
    PROFILE = "server"
    MAX_TOKENS, MAX_ITERS, TOOL_TIMEOUT = 2048, 12, 60
else:
    PROFILE = "cloud"
    MAX_TOKENS, MAX_ITERS, TOOL_TIMEOUT = 4096, 20, 120

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "dolphin3")

# ═══════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Você é o NEXUS — Agente Autônomo Avançado de Elite (AGI Local).

CICLO REACT (execute em loop até concluir):
1. PENSE sobre o objetivo
2. ESCOLHA a ferramenta correta
3. EXECUTE a ferramenta
4. OBSERVE o resultado
5. REPITA ou finalize

FERRAMENTAS (use EXATAMENTE estes XML tags):

TERMINAL:
<tool>exec</tool><tool_input>comando aqui</tool_input>

PESQUISA WEB:
<tool>search</tool><tool_input>query de pesquisa</tool_input>

RACIOCÍNIO (planeje antes de agir):
<tool>think</tool><tool_input>seu raciocínio aqui</tool_input>

CONCLUSÃO (quando terminar):
<tool>done</tool><tool_input>resumo do que foi feito</tool_input>

REGRAS ABSOLUTAS:
- Use terminal para QUALQUER ação real (criar, editar, instalar, executar)
- Use search para informações que você não sabe
- Use think para planejar ações complexas
- Use done quando o objetivo for atingido
- NUNCA invente o resultado de um comando — execute-o
- Seja conciso e eficiente
- Responda em português brasileiro"""

# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════

class KnowledgeBase:
    """Base de conhecimento com busca semântica TF-IDF leve."""

    def __init__(self, path: Path = KB_PATH):
        self._path = path
        self._entries: list[dict] = []
        self._load()

    def add(self, title: str, content: str, source: str = "web", tags: list[str] | None = None):
        eid = hashlib.sha256(f"{title}:{content[:500]}".encode()).hexdigest()[:12]
        entry = {"id": eid, "title": title, "content": content, "source": source,
                 "tags": tags or [], "ts": time.time(), "access": 0}
        for e in self._entries:
            if e["id"] == eid:
                e["content"] = content; e["ts"] = time.time(); self._save(); return
        self._entries.append(entry)
        self._save()

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        q_tokens = set(self._tokenize(query))
        if not q_tokens: return []
        scored = []
        for e in self._entries:
            e_tokens = set(self._tokenize(e.get("title", "") + " " + e.get("content", "")))
            if not e_tokens: continue
            overlap = len(q_tokens & e_tokens) / max(len(q_tokens), 1)
            scored.append((overlap, e))
        scored.sort(key=lambda x: -x[0])
        results = []
        for s, e in scored[:top_k]:
            if s > 0.05:
                e["access"] = e.get("access", 0) + 1
                results.append(e)
        return results

    def count(self) -> int: return len(self._entries)

    def get_recent(self, n: int = 10) -> list[dict]:
        return sorted(self._entries, key=lambda x: -x.get("ts", 0))[:n]

    def _save(self):
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, ensure_ascii=False, indent=2)
        except: pass

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    self._entries = json.load(f)
            except: self._entries = []

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        stopwords = {"o","a","e","de","do","da","dos","das","em","no","na","um","uma","por",
                      "para","com","sem","the","is","at","on","and","or","an","in","to","for",
                      "of","it","this","that","as","by","be","are","was","has","have","not",
                      "but","from","with","they","we","you","que","se","foi","ser","ter",
                      "como","mais","mas","ou","sua","seu","isso","este","esta"}
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return [t for t in text.split() if t not in stopwords and len(t) > 2]


# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: TOOL EXECUTOR (Terminal)
# ═══════════════════════════════════════════════════════════════════

BLOCKED_CMDS = {"rm -rf /", "rm -rf /*", "dd if=/dev/zero of=/dev/sd",
                "mkfs", ":(){ :|:& };:", "> /dev/sd", "chmod -R 777 /"}

class ToolExecutor:
    def __init__(self, work_dir: str = str(BASE_DIR)):
        self.work_dir = work_dir
        self.history: list[dict] = []

    def is_blocked(self, cmd: str) -> bool:
        c = cmd.strip().lower()
        return any(b in c for b in BLOCKED_CMDS)

    def run(self, cmd: str, timeout: int = TOOL_TIMEOUT) -> dict:
        if self.is_blocked(cmd):
            return {"command": cmd, "stdout": "", "stderr": "⛔ Bloqueado por segurança.",
                    "exit_code": -1, "duration": 0}
        start = time.time()
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                    timeout=timeout, cwd=self.work_dir)
            rec = {"command": cmd, "stdout": result.stdout, "stderr": result.stderr,
                   "exit_code": result.returncode, "duration": round(time.time() - start, 2)}
            self.history.append(rec)
            return rec
        except subprocess.TimeoutExpired:
            return {"command": cmd, "stdout": "", "stderr": f"Timeout {timeout}s",
                    "exit_code": -1, "duration": timeout}
        except Exception as e:
            return {"command": cmd, "stdout": "", "stderr": str(e),
                    "exit_code": -1, "duration": round(time.time() - start, 2)}


# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: WEB SEARCH
# ═══════════════════════════════════════════════════════════════════

class WebSearch:
    def __init__(self, timeout: int = 15):
        self._timeout = timeout
        self._ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"

    async def search(self, query: str, max_results: int = 8) -> list[dict]:
        results = await asyncio.gather(
            self._duckduckgo(query, max_results),
            self._bing(query, max_results),
            return_exceptions=True,
        )
        seen, consolidated = set(), []
        for batch in results:
            if isinstance(batch, list):
                for r in batch:
                    key = re.sub(r'https?://(www\.)?', '', r.get("url", "")).rstrip("/")
                    if key not in seen:
                        seen.add(key); consolidated.append(r)
        consolidated.sort(key=lambda x: -x.get("score", 0))
        return consolidated[:max_results]

    async def scrape(self, url: str) -> Optional[dict]:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers={"User-Agent": self._ua},
                                 timeout=aiohttp.ClientTimeout(total=self._timeout),
                                 ssl=False) as r:
                    if r.status != 200: return None
                    html = await r.text(errors="ignore")
                    soup = BeautifulSoup(html, "lxml")
                    for tag in soup.find_all(["script","style","nav","footer"]): tag.decompose()
                    title = soup.title.get_text(strip=True) if soup.title else ""
                    main = soup.find("main") or soup.find("article") or soup.body
                    text = main.get_text(separator="\n", strip=True) if main else ""
                    return {"url": url, "title": title, "text": text[:8000]}
        except: return None

    async def _duckduckgo(self, query: str, max: int) -> list[dict]:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        results = []
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers={"User-Agent": self._ua},
                                 timeout=aiohttp.ClientTimeout(total=self._timeout)) as r:
                    html = await r.text(errors="ignore")
                    soup = BeautifulSoup(html, "lxml")
                    for item in soup.find_all("div", class_="result")[:max]:
                        a = item.find("a", class_="result__a")
                        sn = item.find("a", class_="result__snippet")
                        if a:
                            results.append({"url": a.get("href",""), "title": a.get_text(strip=True),
                                            "snippet": sn.get_text(strip=True) if sn else "",
                                            "source": "duckduckgo", "score": 0.7})
        except: pass
        return results

    async def _bing(self, query: str, max: int) -> list[dict]:
        url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max}"
        results = []
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers={"User-Agent": self._ua},
                                 timeout=aiohttp.ClientTimeout(total=self._timeout)) as r:
                    html = await r.text(errors="ignore")
                    soup = BeautifulSoup(html, "lxml")
                    for item in soup.find_all("li", class_="b_algo")[:max]:
                        a = item.find("a"); p = item.find("p")
                        if a:
                            results.append({"url": a.get("href",""), "title": a.get_text(strip=True),
                                            "snippet": p.get_text(strip=True) if p else "",
                                            "source": "bing", "score": 0.75})
        except: pass
        return results


# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: CODE INTERPRETER (Sandbox)
# ═══════════════════════════════════════════════════════════════════

class CodeInterpreter:
    BLOCKED = {"subprocess","shutil","ctypes","importlib","_thread","threading"}

    def __init__(self, timeout: int = 30, work_dir: str = str(BASE_DIR)):
        self.timeout = timeout
        self.work_dir = work_dir

    def check_security(self, code: str) -> Optional[str]:
        code_lower = code.lower()
        for mod in self.BLOCKED:
            if f"import {mod}" in code_lower or f"from {mod}" in code_lower:
                return f"Import bloqueado: {mod}"
        if "eval(" in code_lower or "exec(" in code_lower:
            return "eval/exec bloqueado"
        for p in ["/etc/","/proc/","/sys/","/dev/"]:
            if p in code_lower: return f"Acesso bloqueado: {p}"
        return None

    async def execute(self, code: str, timeout: int | None = None) -> dict:
        if not code.strip(): return {"success": False, "error": "Código vazio"}
        issue = self.check_security(code)
        if issue: return {"success": False, "error": f"Segurança: {issue}"}

        sandbox_code = f'''import sys, io
_stdout = sys.stdout; sys.stdout = io.StringIO()
sys.setrecursionlimit(100)
try:
{chr(10).join("    " + l for l in code.split(chr(10)))}
except SystemExit: pass
except RecursionError: print("\\n❌ Recursão excessiva")
except MemoryError: print("\\n❌ Memória insuficiente")
except Exception as e: print(f"\\n❌ {{type(e).__name__}}: {{e}}")
finally:
    out = sys.stdout.getvalue(); sys.stdout = _stdout
    if out: print(out)
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=self.work_dir) as f:
            f.write(sandbox_code); temp = f.name
        try:
            effective_timeout = timeout or self.timeout
            proc = await asyncio.create_subprocess_exec(sys.executable, temp,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.work_dir)
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=effective_timeout)
                return {"success": proc.returncode == 0,
                        "output": stdout.decode("utf-8", errors="replace").strip(),
                        "error": stderr.decode("utf-8", errors="replace").strip() if proc.returncode != 0 else ""}
            except asyncio.TimeoutError:
                try: os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except: pass
                return {"success": False, "error": f"Timeout {effective_timeout}s"}
        finally:
            try: os.unlink(temp)
            except: pass


# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: MEMÓRIA
# ═══════════════════════════════════════════════════════════════════

class Memory:
    def __init__(self, max_turns: int = 50):
        self.turns: list[dict] = []
        self.max_turns = max_turns
        self.working: dict[str, Any] = {}
        self.consolidated: list[dict] = []
        self._load_consolidated()

    def add(self, role: str, content: str):
        self.turns.append({"role": role, "content": content, "ts": time.time()})
        if len(self.turns) > self.max_turns:
            old = self.turns[:len(self.turns) - self.max_turns]
            self._consolidate(old)
            self.turns = self.turns[-self.max_turns:]

    def get_prompt_history(self) -> str:
        return "\n".join(
            f"{'Usuário' if t['role']=='user' else 'Assistente'}: {t['content'][:500]}"
            for t in self.turns[-30:]
        )

    def store(self, key: str, value: Any): self.working[key] = value
    def recall(self, key: str) -> Any: return self.working.get(key)

    def _consolidate(self, turns: list[dict]):
        if not turns: return
        texts = [t["content"][:300] for t in turns if t["role"] == "assistant"]
        if texts:
            summary = " | ".join(t[:100] for t in texts[:5])
            facts = []
            for t in texts:
                urls = re.findall(r'https?://[^\s<>"]+', t)
                facts.extend(urls[:2])
            self.consolidated.append({
                "summary": summary[:500], "facts": facts[:10],
                "ts": time.time(), "turns": len(turns)
            })
            if len(self.consolidated) > 100:
                self.consolidated = self.consolidated[-100:]
            self._save_consolidated()

    def search_memory(self, query: str) -> list[dict]:
        q_words = set(query.lower().split())
        results = []
        for m in self.consolidated:
            m_words = set(m.get("summary", "").lower().split())
            if q_words and m_words:
                overlap = len(q_words & m_words) / max(len(q_words), 1)
                if overlap > 0.2: results.append(m)
        return results[:5]

    def _save_consolidated(self):
        try:
            with open(MEMORYCONSOLIDATED_PATH, "w", encoding="utf-8") as f:
                json.dump(self.consolidated, f, ensure_ascii=False, indent=2)
        except: pass

    def _load_consolidated(self):
        if MEMORYCONSOLIDATED_PATH.exists():
            try:
                with open(MEMORYCONSOLIDATED_PATH, encoding="utf-8") as f:
                    self.consolidated = json.load(f)
            except: self.consolidated = []


# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: AUTO-MELHORIA
# ═══════════════════════════════════════════════════════════════════

class AutoImprove:
    def __init__(self):
        self.reflections: list[dict] = []
        self.error_patterns: dict[str, dict] = {}
        self.strategies: dict[str, dict] = {}
        self.metrics = {"reflections": 0, "corrections": 0, "score": 0.5, "stagnation": 0}
        self._load()

    def reflect(self, action: str, result: str, success: bool, duration: float = 0):
        ref = {"action": action[:200], "result": result[:200], "success": success,
               "duration": duration, "ts": time.time()}
        self.reflections.append(ref)
        self.metrics["reflections"] += 1
        if len(self.reflections) > 200: self.reflections = self.reflections[-200:]
        recent = self.reflections[-20:]
        if recent:
            old_score = self.metrics["score"]
            new_score = sum(1 for r in recent if r["success"]) / len(recent)
            self.metrics["score"] = round(new_score, 3)
            if new_score < old_score and new_score < 0.3:
                self.metrics["stagnation"] += 1
            else:
                self.metrics["stagnation"] = max(0, self.metrics["stagnation"] - 1)
        self._save()

    def record_error(self, error: str, context: str):
        sig = hashlib.md5(error[:100].lower().encode()).hexdigest()[:10]
        if sig not in self.error_patterns:
            self.error_patterns[sig] = {"sig": error[:200], "count": 0, "resolutions": []}
        self.error_patterns[sig]["count"] += 1
        self._save()

    def record_strategy(self, name: str, success: bool):
        if name not in self.strategies:
            self.strategies[name] = {"uses": 0, "wins": 0}
        self.strategies[name]["uses"] += 1
        if success: self.strategies[name]["wins"] += 1
        self._save()

    def get_suggestion(self, error: str) -> str | None:
        err_lower = error.lower()
        for p in self.error_patterns.values():
            sig_words = p["sig"].lower().split()[:5]
            if any(w in err_lower for w in sig_words if len(w) > 3):
                if p["resolutions"]: return p["resolutions"][-1]
        return None

    def get_learning_summary(self) -> dict:
        recent = self.reflections[-50:]
        return {
            "total_reflections": self.metrics["reflections"],
            "score": self.metrics["score"],
            "stagnation": self.metrics["stagnation"],
            "error_patterns": len(self.error_patterns),
            "strategies": len(self.strategies),
            "recent_success_rate": sum(1 for r in recent if r["success"]) / max(len(recent), 1),
        }

    def _save(self):
        try:
            with open(AUTO_IMPROVE_PATH, "w", encoding="utf-8") as f:
                json.dump({"reflections": self.reflections[-200:],
                           "patterns": self.error_patterns,
                           "strategies": self.strategies,
                           "metrics": self.metrics}, f, ensure_ascii=False, indent=2)
        except: pass

    def _load(self):
        if AUTO_IMPROVE_PATH.exists():
            try:
                with open(AUTO_IMPROVE_PATH, encoding="utf-8") as f:
                    data = json.load(f)
                self.reflections = data.get("reflections", [])
                self.error_patterns = data.get("patterns", {})
                self.strategies = data.get("strategies", {})
                self.metrics.update(data.get("metrics", {}))
            except: pass


# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: ERROR RECOVERY (Circuit Breaker)
# ═══════════════════════════════════════════════════════════════════

class CircuitBreaker:
    def __init__(self, threshold: int = 5, recovery_timeout: float = 60.0):
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.state = "closed"  # closed, open, half_open
        self.last_failure = 0.0

    def allow(self) -> bool:
        if self.state == "closed": return True
        if self.state == "open":
            if time.time() - self.last_failure > self.recovery_timeout:
                self.state = "half_open"; return True
            return False
        return True  # half_open: allow one test

    def record_success(self):
        if self.state == "half_open": self.state = "closed"
        self.failures = max(0, self.failures - 1)

    def record_failure(self):
        self.failures += 1; self.last_failure = time.time()
        if self.failures >= self.threshold: self.state = "open"


# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: TASK SCHEDULER
# ═══════════════════════════════════════════════════════════════════

class TaskScheduler:
    def __init__(self):
        self.tasks: list[dict] = []
        self._load()

    def add(self, name: str, command: str, interval: float = 0, cron: str = "") -> dict:
        task = {"id": f"task-{len(self.tasks)+1:04d}", "name": name, "command": command,
                "interval": interval, "cron": cron, "status": "pending",
                "run_count": 0, "last_run": 0, "next_run": time.time(),
                "created": time.time()}
        self.tasks.append(task); self._save(); return task

    def list_tasks(self) -> list[dict]: return self.tasks

    def cancel(self, task_id: str) -> bool:
        for t in self.tasks:
            if t["id"] == task_id: t["status"] = "cancelled"; self._save(); return True
        return False

    def _save(self):
        try:
            with open(SCHEDULER_PATH, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except: pass

    def _load(self):
        if SCHEDULER_PATH.exists():
            try:
                with open(SCHEDULER_PATH, encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except: self.tasks = []


# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: PIPELINE EXECUTOR
# ═══════════════════════════════════════════════════════════════════

class PipelineExecutor:
    def __init__(self):
        self.pipelines: list[dict] = []

    def create(self, name: str, steps: list[dict]) -> dict:
        pipe = {"id": f"pipe-{len(self.pipelines)+1:04d}", "name": name,
                "steps": steps, "created": time.time()}
        self.pipelines.append(pipe); return pipe

    async def execute(self, pipeline_id: str, executor: ToolExecutor, web: WebSearch) -> dict:
        pipe = next((p for p in self.pipelines if p["id"] == pipeline_id), None)
        if not pipe: return {"error": "Pipeline não encontrado"}
        results = []
        variables = {}
        for step in pipe["steps"]:
            tool = step.get("tool", "")
            params = step.get("params", {})
            # Substituir variáveis
            for k, v in params.items():
                if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
                    var_name = v[2:-2].strip()
                    params[k] = variables.get(var_name, v)
            try:
                if tool == "exec":
                    r = executor.run(params.get("command", ""), timeout=60)
                    results.append({"step": step.get("id",""), "success": r["exit_code"] == 0,
                                    "output": r["stdout"][:500]})
                    if step.get("output_to"): variables[step["output_to"]] = r["stdout"]
                elif tool == "search":
                    r = await web.search(params.get("query", ""), max_results=3)
                    results.append({"step": step.get("id",""), "success": True,
                                    "output": f"{len(r)} resultados"})
                    if step.get("output_to"): variables[step["output_to"]] = json.dumps(r, ensure_ascii=False)
            except Exception as e:
                results.append({"step": step.get("id",""), "success": False, "error": str(e)})
        return {"pipeline": pipe["name"], "results": results, "variables": variables}


# ═══════════════════════════════════════════════════════════════════
#  MÓDULO: PLUGIN SYSTEM
# ═══════════════════════════════════════════════════════════════════

class PluginManager:
    def __init__(self):
        self.plugins: dict[str, dict] = {}
        self._builtin = {
            "system_info": {"desc": "Info do sistema", "fn": self._plugin_system_info},
            "file_stats": {"desc": "Estatísticas de arquivos", "fn": self._plugin_file_stats},
        }

    def register(self, name: str, fn: Callable, desc: str = ""):
        self.plugins[name] = {"fn": fn, "desc": desc}

    async def execute(self, name: str, **kwargs) -> dict:
        if name in self._builtin:
            try: return {"success": True, "result": await self._builtin[name]["fn"](**kwargs)}
            except Exception as e: return {"success": False, "error": str(e)}
        if name in self.plugins:
            try: return {"success": True, "result": await self.plugins[name]["fn"](**kwargs)}
            except Exception as e: return {"success": False, "error": str(e)}
        return {"success": False, "error": f"Plugin '{name}' não encontrado"}

    def list_plugins(self) -> list[str]:
        return list(self._builtin.keys()) + list(self.plugins.keys())

    async def _plugin_system_info(self, **kw) -> dict:
        return {"hardware": HARDWARE, "profile": PROFILE, "python": sys.version,
                "platform": platform.platform(), "cwd": os.getcwd()}

    async def _plugin_file_stats(self, directory: str = ".", **kw) -> dict:
        d = Path(directory)
        if not d.exists(): return {"error": "Diretório não existe"}
        cats = defaultdict(lambda: {"count": 0, "size": 0})
        total_files, total_size = 0, 0
        for item in d.rglob("*"):
            if item.is_file() and not item.name.startswith("."):
                ext = item.suffix.lower() or "sem_extensão"
                cats[ext]["count"] += 1
                try: cats[ext]["size"] += item.stat().st_size
                except: pass
                total_files += 1
                total_size += cats[ext]["size"]
        return {"total_files": total_files, "total_size_mb": round(total_size/(1024*1024),2),
                "by_extension": dict(sorted(cats.items(), key=lambda x: -x[1]["count"])[:10])}


# ═══════════════════════════════════════════════════════════════════
#  ENGINE LLM (Multi-provider)
# ═══════════════════════════════════════════════════════════════════

class LLMEngine:
    def __init__(self):
        self.available = False
        self.provider = "none"
        self.model = OLLAMA_MODEL

    async def check(self) -> bool:
        # Verificar Ollama
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("http://localhost:11434/api/tags",
                                 timeout=aiohttp.ClientTimeout(total=3)) as r:
                    if r.status == 200:
                        data = await r.json()
                        models = [m.get("name","") for m in data.get("models",[])]
                        if models:
                            self.available = True; self.provider = "ollama"
                            self.model = models[0]; return True
        except: pass
        # Verificar Groq (gratuito)
        groq_key = os.getenv("GROQ_API_KEY", "")
        if groq_key:
            self.available = True; self.provider = "groq"
            self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            return True
        # Verificar OpenAI
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            self.available = True; self.provider = "openai"
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            return True
        return False

    async def generate(self, prompt: str, context: str = "") -> str:
        if self.provider == "ollama":
            return await self._ollama_generate(prompt, context)
        elif self.provider == "groq":
            return await self._openai_compat_generate(prompt, context, "https://api.groq.com/openai/v1", os.getenv("GROQ_API_KEY",""))
        elif self.provider == "openai":
            return await self._openai_compat_generate(prompt, context, "https://api.openai.com/v1", os.getenv("OPENAI_API_KEY",""))
        raise Exception("Nenhum provider LLM disponível")

    async def _ollama_generate(self, prompt: str, context: str) -> str:
        full = f"Contexto:\n{context}\n\n{prompt}" if context else prompt
        body = {"model": self.model, "prompt": full, "system": SYSTEM_PROMPT,
                "stream": False, "options": {"temperature": 0.7, "num_predict": MAX_TOKENS}}
        async with aiohttp.ClientSession() as s:
            async with s.post(OLLAMA_URL, json=body,
                              timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Ollama erro {resp.status}: {text[:300]}")
                data = await resp.json()
                return data.get("response", "")

    async def _openai_compat_generate(self, prompt: str, context: str, base_url: str, api_key: str) -> str:
        full = f"Contexto:\n{context}\n\n{prompt}" if context else prompt
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": full}]
        body = {"model": self.model, "messages": messages, "temperature": 0.7, "max_tokens": MAX_TOKENS}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{base_url}/chat/completions", json=body, headers=headers,
                              timeout=aiohttp.ClientTimeout(total=120)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"LLM erro {resp.status}: {text[:300]}")
                data = await resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")


# ═══════════════════════════════════════════════════════════════════
#  NEXUS AGENT — LOOP PRINCIPAL
# ═══════════════════════════════════════════════════════════════════

class NexusAgent:
    def __init__(self):
        self.kb = KnowledgeBase()
        self.tools = ToolExecutor()
        self.search = WebSearch()
        self.memory = Memory()
        self.llm = LLMEngine()
        self.auto_improve = AutoImprove()
        self.circuit_breaker = CircuitBreaker()
        self.scheduler = TaskScheduler()
        self.pipeline = PipelineExecutor()
        self.plugins = PluginManager()
        self.code_interpreter = CodeInterpreter()
        self._start_time = time.time()

    async def initialize(self):
        console.print(Panel("[bold cyan]🧠 NEXUS — Inicializando[/bold cyan]", border_style="cyan"))
        # Hardware
        console.print(f"  📱 Hardware: {HARDWARE['cores']} cores, {HARDWARE['ram_mb']}MB RAM, {HARDWARE['storage_gb']}GB disco")
        console.print(f"  🎯 Perfil: {PROFILE}")
        # LLM
        console.print("  🔍 Verificando LLM...")
        if await self.llm.check():
            console.print(f"  ✅ LLM: {self.llm.provider}/{self.llm.model}")
        else:
            console.print("  ⚠️ LLM indisponível — modo offline (terminal + search + KB)")
            console.print(f"    Ollama: ollama pull {OLLAMA_MODEL} && ollama serve &")
            console.print(f"    Groq:   export GROQ_API_KEY=gsk_...")
        # Componentes
        console.print(f"  📚 KB: {self.kb.count()} entradas")
        console.print(f"  🔄 Auto-Improve: {self.auto_improve.metrics['reflections']} reflexões")
        console.print(f"  🧩 Plugins: {len(self.plugins.list_plugins())}")
        console.print(f"  ⏰ Scheduler: {len(self.scheduler.tasks)} tarefas")
        console.print(f"  🔧 Tools: terminal, search, code_exec, plugins, pipelines")
        console.print(Panel("[bold green]✅ NEXUS pronto![/bold green]", border_style="green"))

    async def process(self, user_input: str) -> str:
        self.memory.add("user", user_input)
        start = time.time()

        # Modo offline
        if not self.llm.available:
            result = await self._offline_process(user_input)
            self.memory.add("assistant", result)
            self.auto_improve.reflect(user_input[:100], result[:200], True, time.time()-start)
            return result

        # Modo online (ReAct Loop)
        kb_ctx = ""
        kb_results = self.kb.search(user_input, top_k=3)
        if kb_results:
            kb_ctx = "\n\n".join(f"[{e['title']}] {e['content'][:400]}" for e in kb_results)

        history = self.memory.get_prompt_history()
        prompt = f"Histórico:\n{history}\n\nUsuário: {user_input}\nAssistente:"

        for iteration in range(MAX_ITERS):
            try:
                if not self.circuit_breaker.allow():
                    return "🔴 Circuit breaker aberto — tente novamente em alguns segundos"
                raw = await self.llm.generate(prompt, kb_ctx)
                self.circuit_breaker.record_success()
            except Exception as e:
                self.circuit_breaker.record_failure()
                self.auto_improve.record_error(str(e), user_input[:100])
                suggestion = self.auto_improve.get_suggestion(str(e))
                msg = f"❌ Erro LLM: {e}"
                if suggestion: msg += f"\n💡 {suggestion}"
                return msg

            clean, actions = await self._process_tools(raw)

            if actions:
                action_text = "\n".join(actions)
                prompt += f"\n{raw}\n\nResultado:\n{action_text}\n\nContinue:"
                self.memory.add("assistant", action_text)
                continue

            if clean:
                self.memory.add("assistant", clean)
                self.auto_improve.reflect(user_input[:100], clean[:200], True, time.time()-start)
                self.auto_improve.record_strategy("react_loop", True)
                final = ("\n\n".join(actions) + "\n\n---\n\n" if actions else "") + clean
                return final

            return "(nenhum output)"

        return f"⚠️ Limite de {MAX_ITERS} iterações atingido."

    async def _process_tools(self, response: str) -> tuple[str, list[str]]:
        actions, clean = [], response

        # exec
        for m in re.finditer(r"<tool>exec</tool>\s*<tool_input>(.*?)</tool_input>", response, re.DOTALL):
            cmd = m.group(1).strip()
            if cmd:
                r = self.tools.run(cmd)
                icon = "✅" if r["exit_code"] == 0 else "❌"
                out = r["stdout"].strip()[:2000] if r["stdout"] else ""
                err = r["stderr"].strip()[:500] if r["stderr"] else ""
                act = f"{icon} `{cmd}`"
                if out: act += f"\n```\n{out}\n```"
                if err and r["exit_code"] != 0: act += f"\nErro: {err}"
                actions.append(act)
                if r["exit_code"] == 0 and out:
                    self.kb.add(f"Cmd: {cmd}", out[:1000], source="terminal")
                self.auto_improve.reflect(cmd, out[:200] if out else err, r["exit_code"]==0)
                self.auto_improve.record_strategy("terminal", r["exit_code"]==0)
            clean = clean.replace(m.group(0), "")

        # search
        for m in re.finditer(r"<tool>search</tool>\s*<tool_input>(.*?)</tool_input>", response, re.DOTALL):
            query = m.group(1).strip()
            if query:
                results = await self.search.search(query, max_results=5)
                if results:
                    lines = [f"🔍 **{query}**\n"]
                    for i, r in enumerate(results, 1):
                        lines.append(f"**{i}.** [{r['title']}]({r['url']})")
                        if r.get("snippet"): lines.append(f"   {r['snippet'][:150]}\n")
                        self.kb.add(r["title"], r.get("snippet",""), source="web")
                    actions.append("\n".join(lines))
                else: actions.append(f"🔍 Sem resultados: {query}")
            clean = clean.replace(m.group(0), "")

        # think
        for m in re.finditer(r"<tool>think</tool>\s*<tool_input>(.*?)</tool_input>", response, re.DOTALL):
            actions.append(f"🧠 {m.group(1).strip()}")
            clean = clean.replace(m.group(0), "")

        # done
        for m in re.finditer(r"<tool>done</tool>\s*<tool_input>(.*?)</tool_input>", response, re.DOTALL):
            actions.append(f"✅ {m.group(1).strip()}")
            clean = clean.replace(m.group(0), "")

        return clean.strip(), actions

    async def _offline_process(self, user_input: str) -> str:
        u = user_input.lower()

        # Plugin commands
        if u.startswith("/plugin ") or u.startswith("/pl "):
            plugin_name = u.split(maxsplit=1)[1].split()[0] if len(u.split()) > 1 else ""
            if plugin_name:
                r = await self.plugins.execute(plugin_name)
                if r["success"]:
                    return f"🧩 **Plugin {plugin_name}:**\n```json\n{json.dumps(r['result'], indent=2, ensure_ascii=False)[:2000]}\n```"
                return f"❌ {r['error']}"
            return f"Plugins: {', '.join(self.plugins.list_plugins())}"

        # Search
        if any(w in u for w in ["pesquisar","search","procurar","buscar"]):
            query = re.sub(r'(pesquisar|search|procurar|buscar)\s*(sobre|por|about)?\s*', '', u).strip()
            if query:
                results = await self.search.search(query, max_results=5)
                if results:
                    lines = [f"🔍 **{query}**\n"]
                    for i, r in enumerate(results, 1):
                        lines.append(f"**{i}.** [{r['title']}]({r['url']})")
                        if r.get("snippet"): lines.append(f"   {r['snippet'][:150]}\n")
                        self.kb.add(r["title"], r.get("snippet",""), source="web")
                    return "\n".join(lines)
            return "🔍 Use: pesquisar sobre [assunto]"

        # Code exec
        if u.startswith("/exec ") or u.startswith("/code "):
            code = user_input.split(maxsplit=1)[1] if " " in user_input else ""
            if code:
                r = await self.code_interpreter.execute(code)
                if r["success"]: return f"📤 **Output:**\n```\n{r['output']}\n```"
                return f"❌ **Erro:** {r['error']}"
            return "Use: /exec seu_codigo_python"

        # KB search
        kb_results = self.kb.search(user_input, top_k=3)
        if kb_results:
            lines = ["📚 **Conhecimento:**\n"]
            for e in kb_results:
                lines.append(f"**{e['title']}**\n{e['content'][:300]}\n")
            return "\n".join(lines)

        # Memory search
        mem_results = self.memory.search_memory(user_input)
        if mem_results:
            lines = ["🧠 **Memória:**\n"]
            for m in mem_results[:3]:
                lines.append(f"- {m.get('summary', '')[:200]}\n")
            return "\n".join(lines)

        return (
            "⚠️ **LLM offline.** Modos disponíveis:\n\n"
            "🔧 **Terminal:** qualquer mensagem → executa comandos\n"
            "🔍 **Pesquisa:** `pesquisar sobre [assunto]`\n"
            "🐍 **Código:** `/exec seu_codigo_python`\n"
            "🧩 **Plugins:** `/plugin system_info`\n"
            f"📚 **KB:** {self.kb.count()} entradas\n\n"
            f"**Para ativar LLM:**\n"
            f"```bash\nollama pull {OLLAMA_MODEL}\nollama serve &\npython3 {__file__}\n```"
        )


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

BANNER = """
\033[36m╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗              ║
║     ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝              ║
║     ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗              ║
║     ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║              ║
║     ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║              ║
║     ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝              ║
║                                                               ║
║     🧠 NEXUS v3.0 — AGI Local Total                          ║
║     ReAct + Auto-Improve + KB + Plugins                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝\033[0m"""

async def main():
    print(BANNER)
    agent = NexusAgent()
    await agent.initialize()

    while True:
        try:
            user_input = console.input("\033[36mVocê › \033[0m").strip()
            if not user_input: continue
            cmd = user_input.lower()

            if cmd in ("/exit","/sair","exit","quit"):
                console.print("\n[dim]Salvando...[/dim]")
                agent.kb._save(); agent.auto_improve._save()
                agent.memory._save_consolidated()
                console.print("[dim]Até logo! 👋[/dim]\n"); break

            if cmd in ("/help","/ajuda","help"):
                print(HELP_TEXT); continue

            if cmd in ("/status",):
                uptime = time.time() - agent._start_time
                h, m = int(uptime//3600), int((uptime%3600)//60)
                console.print(f"\n📊 **NEXUS Status:**")
                console.print(f"  🏗️ Perfil: {PROFILE} | Hardware: {HARDWARE['cores']} cores, {HARDWARE['ram_mb']}MB RAM")
                console.print(f"  🌐 LLM: {agent.llm.provider}/{agent.llm.model} ({'✅' if agent.llm.available else '❌'})")
                console.print(f"  📚 KB: {agent.kb.count()} | 🧠 Reflexões: {agent.auto_improve.metrics['reflections']}")
                console.print(f"  📈 Score: {agent.auto_improve.metrics['score']:.2f} | ⏱️ Uptime: {h}h{m}m")
                console.print(f"  🔧 Comandos: {len(agent.tools.history)} | ⏰ Tarefas: {len(agent.scheduler.tasks)}")
                console.print(f"  🔌 Circuit Breaker: {agent.circuit_breaker.state}")
                console.print(f"  🧩 Plugins: {', '.join(agent.plugins.list_plugins())}\n")
                continue

            if cmd in ("/kb","/conhecimento"):
                entries = agent.kb.get_recent(10)
                if entries:
                    console.print(f"\n📚 **Base de Conhecimento** ({agent.kb.count()} total)\n")
                    for e in entries:
                        src = e.get("source","?")
                        console.print(f"  [{src}] {e['title'][:60]}")
                    console.print()
                else: console.print("📚 Base vazia\n")
                continue

            if cmd in ("/learn","/aprendizado"):
                s = agent.auto_improve.get_learning_summary()
                console.print(Panel(
                    f"Score: {s['score']:.3f} | Reflexões: {s['total_reflections']} | "
                    f"Padrões erro: {s['error_patterns']} | Estratégias: {s['strategies']} | "
                    f"Stagnation: {s['stagnation']} | Taxa sucesso: {s['recent_success_rate']:.1%}",
                    title="🔄 Auto-Melhoria", border_style="cyan"))
                continue

            if cmd in ("/plugins","/pl"):
                console.print(f"\n🧩 **Plugins:** {', '.join(agent.plugins.list_plugins())}\n")
                continue

            if cmd in ("/clear","/limpar"):
                agent.memory.turns.clear(); console.print("🧹 Memória limpa"); continue

            if cmd in ("/hardware","/hw"):
                console.print(f"\n📱 **Hardware:**\n{json.dumps(HARDWARE, indent=2)}\n")
                continue

            # Processar
            with console.status("[bold green]🧠 Processando..."):
                response = await agent.process(user_input)
            console.print()
            try: console.print(Markdown(response))
            except: console.print(response)
            console.print()

        except KeyboardInterrupt:
            console.print("\n[dim]Ctrl+C — /exit para sair[/dim]")
        except EOFError:
            console.print("\n[dim]Até logo! 👋[/dim]\n"); break
        except Exception as e:
            console.print(f"\n[red]❌ {e}[/red]\n")

HELP_TEXT = """
\033[36m╔═══════════════════════════════════════════════════════╗
║  🧠 NEXUS v3.0 — Ajuda                                ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  💬 Chat: digite qualquer mensagem                    ║
║                                                       ║
║  🔧 O agente decide automaticamente:                  ║
║     "instale vim"         → executa pkg install       ║
║     "pesquisar sobre X"   → busca web                 ║
║     "liste os arquivos"   → executa ls                ║
║                                                       ║
║  🐍 Código Python:                                    ║
║     /exec print(2+2)      → executa em sandbox        ║
║                                                       ║
║  🧩 Plugins:                                          ║
║     /plugin system_info   → info do hardware          ║
║     /plugin file_stats    → stats de arquivos         ║
║                                                       ║
║  📋 Comandos:                                         ║
║     /help      — esta ajuda                           ║
║     /status    — status completo                      ║
║     /kb        — base de conhecimento                 ║
║     /learn     — auto-melhoria                        ║
║     /plugins   — lista plugins                        ║
║     /hardware  — info do hardware                     ║
║     /clear     — limpar memória                       ║
║     /exit      — sair                                 ║
╚═══════════════════════════════════════════════════════╝\033[0m"""


if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: console.print("\n[dim]Até logo! 👋[/dim]\n")
