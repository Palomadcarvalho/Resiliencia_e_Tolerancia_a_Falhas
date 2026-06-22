import httpx
import asyncio
import logging
import pybreaker
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Principal - Matrícula Acadêmica")

SERVICO_EXTERNO = "http://servico-externo:8001"
TIMEOUT_SEGUNDOS = 5

# Cliente HTTP global para otimizar pool de conexões (Connection Pooling).
# Configura Timeout total e Timeout específico de conexão.
http_client = httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT_SEGUNDOS, connect=2.0))

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

# ─── Métricas Prometheus
requisicoes_total = Counter(
    "matricula_requisicoes_total",
    "Total de requisições de matrícula",
    ["status"]
)
tentativas_retry = Counter(
    "matricula_retry_total",
    "Total de tentativas de retry realizadas"
)
circuit_breaker_aberto = Counter(
    "matricula_circuit_breaker_aberto_total",
    "Vezes que o circuit breaker abriu"
)
duracao_requisicao = Histogram(
    "matricula_duracao_segundos",
    "Duração das requisições de matrícula"
)

# ─── Circuit Breaker (pybreaker)
# CLOSED → OPEN após 5 falhas consecutivas
# OPEN   → HALF-OPEN após 30 segundos
# HALF-OPEN → CLOSED se sucesso; → OPEN se falha

class CBListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning(f"⚡ Circuit Breaker: {old_state.name} → {new_state.name}")
        if new_state.name == "open":
            circuit_breaker_aberto.inc()

cb = pybreaker.CircuitBreaker(
    fail_max=5,          # abre após 5 falhas consecutivas
    reset_timeout=30,    # tenta fechar após 30s (HALF-OPEN)
    listeners=[CBListener()],
    name="validador-cpf",
)

# Limita a 10 requisições concorrentes ao serviço externo
bulkhead = asyncio.Semaphore(10)

# ─── Retry + Timeout (tenacity + httpx)
def antes_de_retry(retry_state):
    if retry_state.attempt_number > 1:
        tentativas_retry.inc()
        logger.info(f"🔄 Retry {retry_state.attempt_number - 1}/2 — aguardando backoff...")

def deve_fazer_retry(exception: BaseException) -> bool:
    """Determina se o erro ocorrido permite uma nova tentativa (Retry)."""
    if isinstance(exception, httpx.TimeoutException):
        return True  # Retentar sempre em caso de Timeout
    if isinstance(exception, httpx.HTTPStatusError):
        # Retentar apenas se for um erro do servidor (5xx)
        # Erros do cliente (4xx) não são corrigidos com retries
        return exception.response.status_code >= 500
    return False

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),  # 1s → 2s → 4s
    retry=retry_if_exception(deve_fazer_retry),
    before=antes_de_retry,
)
async def chamar_servico(cpf: str, modo: str) -> dict:
    logger.info(f"Chamando serviço externo — CPF: {cpf} | modo: {modo}")

    # Usa o http_client global (com connection pool ativo)
    response = await http_client.get(
        f"{SERVICO_EXTERNO}/validar-cpf/{modo}/{cpf}"
    )
    response.raise_for_status()
    logger.info("Serviço externo respondeu com sucesso.")
    return response.json()

async def chamar_com_circuit_breaker(cpf: str, modo: str) -> dict:
    try:
        loop = asyncio.get_event_loop()
        resultado = await loop.run_in_executor(
            None,
            lambda: cb.call(asyncio.run, chamar_servico(cpf, modo))
        )
        return resultado
    except pybreaker.CircuitBreakerError:
        logger.warning("🚫 Circuit Breaker OPEN — requisição bloqueada.")
        raise

def resposta_fallback(cpf: str, motivo: str) -> dict:
    logger.warning(f"Fallback ativado — motivo: {motivo}")
    return {
        "cpf": cpf,
        "valido": None,
        "fonte": "fallback",
        "mensagem": (
            "Não foi possível validar o CPF no momento. "
            "A matrícula foi registrada como pendente e será confirmada em breve."
        ),
    }

@app.post("/matricula/{cpf}")
async def realizar_matricula(cpf: str, modo: str = "sucesso"):
    """
    Realiza matrícula acadêmica validando o CPF via serviço externo.

    Parâmetros:
    - modo=sucesso  → serviço responde normalmente
    - modo=lento    → serviço demora 10s (timeout + retry atuam)
    - modo=falha    → serviço retorna HTTP 500 (retry + fallback + circuit breaker atuam)
    """
    with duracao_requisicao.time():

        # ── Bulkhead: limita concorrência
        if bulkhead.locked() and bulkhead._value == 0:
            logger.warning("Bulkhead: limite de concorrência atingido.")
            requisicoes_total.labels(status="bulkhead_rejeitado").inc()
            return JSONResponse(status_code=429, content={
                "erro": "Muitas requisições simultâneas. Tente novamente em instantes."
            })

        async with bulkhead:
            try:
                resultado = await chamar_com_circuit_breaker(cpf, modo)
                requisicoes_total.labels(status="sucesso").inc()
                return {
                    "status": "matricula_processada",
                    "validacao_cpf": resultado,
                }

            except pybreaker.CircuitBreakerError:
                # Circuit Breaker OPEN → fallback imediato
                # HTTP 200 (não 503): fallback é tratamento controlado de erro.
                # O usuário recebe uma resposta válida (matrícula pendente),
                # nunca um erro técnico bruto. Mesmo padrão do fallback por
                # retries esgotados — coerente com o documento de trade-offs.
                dados = resposta_fallback(cpf, "circuit_breaker_aberto")
                requisicoes_total.labels(status="circuit_breaker").inc()
                return JSONResponse(status_code=200, content={
                    "status": "matricula_pendente",
                    "validacao_cpf": dados,
                })

            except Exception as e:
                # Retries esgotados → fallback
                dados = resposta_fallback(cpf, str(type(e).__name__))
                requisicoes_total.labels(status="fallback").inc()
                return JSONResponse(status_code=200, content={
                    "status": "matricula_pendente",
                    "validacao_cpf": dados,
                })


@app.get("/circuit-breaker/status")
async def status_circuit_breaker():
    """Retorna o estado atual do circuit breaker."""
    return {
        "estado": cb.current_state,
        "falhas_consecutivas": cb.fail_counter,
        "limite_falhas": cb.fail_max,
        "timeout_reset_segundos": cb.reset_timeout,
    }


@app.post("/circuit-breaker/resetar")
async def resetar_circuit_breaker():
    """Reseta manualmente o circuit breaker (útil para demonstração)."""
    cb._state_storage._state = pybreaker.STATE_CLOSED
    cb._state_storage._failure_count = 0
    logger.info("🔁 Circuit breaker resetado manualmente.")
    return {"mensagem": "Circuit breaker resetado para CLOSED."}


@app.get("/health")
async def health():
    """Health check com status do circuit breaker e do serviço externo."""
    cb_status = cb.current_state
    servico_ok = False
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{SERVICO_EXTERNO}/health")
            servico_ok = r.status_code == 200
    except Exception:
        pass

    return {
        "api_principal": "ok",
        "circuit_breaker": cb_status,
        "servico_externo": "ok" if servico_ok else "indisponivel",
    }


@app.get("/metrics")
async def metrics():
    """Endpoint de métricas para coleta pelo Prometheus."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
