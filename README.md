# 🛡️ Resiliência e Tolerância a Falhas

> Trabalho Prático — Arquitetura de Software (5º Período)
> PUC Minas · Instituto de Ciências Exatas e Informática (ICEI)
> Departamento de Sistemas de Informação e Engenharia de Software

---

## 👥 Equipe

Arthur Luiz Alves Soares

Athos Marques Ribeiro Fonseca

Brenda Evers

Mateus Araujo Santos

Paloma Dias de Carvalho

**Professor:** Filipe Tório Lopes Ruas Nhimi

**Disciplina:** Arquitetura de Software — 5º Período

---

## 📋 Sobre o Projeto

Este projeto tem como objetivo projetar, implementar e demonstrar uma aplicação capaz de lidar com **falhas**, **indisponibilidades temporárias** e **lentidão** em serviços externos ou componentes dependentes.

O foco principal não é apenas capturar erros, mas aplicar **estratégias arquiteturais** que permitam ao sistema continuar operando de forma controlada mesmo diante de falhas.

---

## 🎯 Cenário

A aplicação simula uma **API acadêmica de matrícula** que depende de um serviço externo de **validação de CPF**. Esse serviço pode falhar, demorar a responder ou ficar temporariamente indisponível. Os mecanismos implementados visam reduzir o impacto dessas falhas sobre a aplicação principal, garantindo que o usuário sempre receba uma resposta controlada.

---

## ⚙️ Mecanismos de Resiliência Implementados

### 🔒 Bulkhead
Limita a **10 o número máximo de requisições simultâneas** ao serviço externo usando `asyncio.Semaphore`. Requisições além do limite recebem HTTP 429 imediatamente, evitando que um pico de tráfego consuma todos os recursos do servidor.

**Trade-offs:** Limite muito baixo pode rejeitar requisições legítimas; requer ajuste baseado em teste de carga.

### 🔁 Retry
Reenvio automático com **backoff exponencial** (1s → 2s → 4s) usando a biblioteca `tenacity`. Realiza até 3 tentativas antes de desistir, e apenas para exceções elegíveis (timeout e erros HTTP 5xx).

**Trade-offs:** Aumenta a latência total em caso de falhas consecutivas; deve ser usado apenas em operações idempotentes (leitura/consulta).

### ⏱️ Timeout
Limite de **5 segundos por tentativa** configurado via `httpx`. Se o serviço externo não responder nesse tempo, a operação é cancelada e o retry é acionado.

**Trade-offs:** Timeout muito curto descarta respostas válidas em serviços naturalmente lentos; muito longo torna o circuit breaker ineficaz.

### 🔀 Fallback
Quando todas as tentativas de retry falham, a API retorna **HTTP 200 com status `matricula_pendente`**, informando que a validação do CPF será realizada posteriormente. O usuário nunca recebe um erro 500 bruto.

**Trade-offs:** Exige um mecanismo complementar (fila, job agendado) para processar as pendências; a resposta deve ser honesta sobre o estado real.

### 🔌 Circuit Breaker
Implementado com `pybreaker`, opera em **três estados**:
- **CLOSED:** operação normal — chamadas passam normalmente.
- **OPEN:** após 5 falhas consecutivas — chamadas bloqueadas, fallback imediato.
- **HALF-OPEN:** após 30 segundos — uma chamada de teste é permitida para verificar recuperação.

**Trade-offs:** Estado em memória não é compartilhado entre múltiplas instâncias (para produção, usar Redis); requer ajuste fino dos limiares de abertura.

### ❤️ Health Check
O endpoint `/health` consulta ativamente o serviço externo e retorna o estado atual do circuit breaker, permitindo visibilidade proativa do sistema.

---

## 🚀 Como Executar

### Pré-requisitos

- [Docker Desktop](https://docs.docker.com/get-docker/) instalado (inclui Docker Compose)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/Palomadcarvalho/Resiliencia_e_Tolerancia_a_Falhas/
cd seu-repositorio
```

### Execução

```bash
# Suba todos os serviços (API, serviço externo, Prometheus e Grafana)
docker-compose up --build

# Para encerrar
docker-compose down
```

---

## 🧪 Demonstrações

As seguintes situações podem ser simuladas para demonstrar o comportamento resiliente da aplicação:

| Cenário | Como simular | Comportamento esperado |
|--------|--------------|------------------------|
| ✅ Chamada bem-sucedida | `POST /matricula/{cpf}?modo=sucesso` | HTTP 200 com resultado da validação |
| 🐢 Lentidão | `POST /matricula/{cpf}?modo=lento` | Timeout (5s) → Retry 3x com backoff → Fallback |
| ❌ Falha total | `POST /matricula/{cpf}?modo=falha` | Retry 3x → Fallback com matrícula pendente |
| 🔁 Retry | Qualquer `modo=falha` ou `modo=lento` | Logs evidenciam 3 tentativas com intervalos crescentes |
| 🔌 Circuit Breaker aberto | 5+ chamadas com `modo=falha` | Requisições bloqueadas sem chamar o serviço (HTTP 503) |
| 🔒 Bulkhead | 10+ requisições simultâneas | Excedente recebe HTTP 429 imediatamente |

### Comandos de teste prontos

```bash
# 1. Chamada bem-sucedida
curl -X POST "http://localhost:8000/matricula/529.982.247-25?modo=sucesso"

# 2. Simular lentidão
curl -X POST "http://localhost:8000/matricula/529.982.247-25?modo=lento"

# 3. Simular falha (execute 5+ vezes para abrir o circuit breaker)
curl -X POST "http://localhost:8000/matricula/529.982.247-25?modo=falha"

# 4. Ver estado do circuit breaker
curl http://localhost:8000/circuit-breaker/status

# 5. Resetar o circuit breaker
curl -X POST http://localhost:8000/circuit-breaker/resetar

# 6. Health check detalhado
curl http://localhost:8000/health
```

---

## 📊 Métricas e Logs

Os logs estruturados e as métricas evidenciam o comportamento resiliente em cada cenário.

```bash
# Visualizar logs em tempo real de todos os serviços
docker-compose logs -f

# Visualizar logs apenas da API principal
docker-compose logs -f api-principal
```

**Dashboards de monitoramento:**
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (usuário: `admin` | senha: `admin`)

| Métrica | Descrição |
|--------|-----------|
| `matricula_requisicoes_total{status}` | Total por status: `sucesso`, `fallback`, `circuit_breaker`, `bulkhead_rejeitado` |
| `matricula_retry_total` | Total de retries realizados |
| `matricula_circuit_breaker_aberto_total` | Vezes que o circuit breaker abriu |
| `matricula_duracao_segundos` | Histograma de latência das requisições |

---

## 🏗️ Arquitetura

```
Cliente (curl / Postman)
         │
         ▼ HTTP POST /matricula/{cpf}?modo=sucesso|lento|falha
         │
┌────────────────────────────────────────────┐
│          API Principal (porta 8000)         │
│                                            │
│  1. Bulkhead    → máx. 10 simultâneas      │
│  2. Circuit Breaker → CLOSED/OPEN/HALF-OPEN│
│  3. Timeout     → 5s por tentativa         │
│  4. Retry       → 3x, backoff 1s→2s→4s    │
│  5. Fallback    → matrícula pendente       │
└───────────────────┬────────────────────────┘
                    │ HTTP GET
                    ▼
┌────────────────────────────────────────────┐
│     Serviço Externo Simulado (porta 8001)   │
│                                            │
│  /validar-cpf/sucesso  → resposta normal   │
│  /validar-cpf/lento    → delay 10s         │
│  /validar-cpf/falha    → HTTP 500          │
└────────────────────────────────────────────┘
         │
         ▼ scrape /metrics
┌─────────────────┐      ┌─────────────────┐
│   Prometheus    │ ───► │     Grafana      │
│  (porta 9090)   │      │  (porta 3000)   │
└─────────────────┘      └─────────────────┘
```

**Tecnologias utilizadas:**
- **Back-end:** Python 3.11 + FastAPI + Uvicorn
- **Resiliência:** pybreaker (Circuit Breaker) · tenacity (Retry) · httpx (Timeout) · asyncio.Semaphore (Bulkhead)
- **Monitoramento:** Prometheus + Grafana + prometheus-client
- **Infraestrutura:** Docker + Docker Compose

---

## 📐 Decisões Arquiteturais

### Por que escolhemos essas estratégias?

A combinação dos mecanismos forma uma **defesa em profundidade**: cada camada cobre a limitação da anterior. Nenhum mecanismo isolado é suficiente — um retry sem fallback ainda expõe erro ao usuário; um fallback sem circuit breaker ainda desperdiça recursos tentando um serviço sabidamente indisponível.

A escolha do Python com FastAPI se justifica pela simplicidade de demonstração e pela disponibilidade de bibliotecas maduras (`pybreaker`, `tenacity`) que implementam os padrões corretamente, sem reinventar a roda.

### Impactos arquiteturais

- **Retry + Timeout:** Trabalham em conjunto — o timeout define quando uma tentativa falha; o retry decide se vale tentar novamente. O backoff exponencial evita sobrecarregar um serviço já degradado.
- **Fallback + Circuit Breaker:** Garantem degradação controlada. O circuit breaker elimina a latência de timeout × retries quando o serviço está claramente indisponível, tornando o fallback imediato.
- **Bulkhead:** Isola o impacto de picos de tráfego, garantindo que um volume anormal de requisições não degrade toda a aplicação.
- **Health Check:** Permite visibilidade proativa — a equipe de operações sabe o estado do sistema antes que os usuários percebam a degradação.

---

## 📁 Estrutura do Projeto

```
📦 projeto-resiliencia
 ┣ 📂 api-principal/
 ┃ ┣ 📄 main.py            ← Bulkhead + CB + Retry + Timeout + Fallback
 ┃ ┣ 📄 requirements.txt
 ┃ ┗ 📄 Dockerfile
 ┣ 📂 servico-externo/
 ┃ ┣ 📄 main.py            ← Simula sucesso, lentidão e falha
 ┃ ┣ 📄 requirements.txt
 ┃ ┗ 📄 Dockerfile
 ┣ 📂 monitoramento/
 ┃ ┣ 📄 prometheus.yml
 ┃ ┗ 📂 grafana/provisioning/
 ┃   ┣ 📂 datasources/datasource.yml
 ┃   ┗ 📂 dashboards/dashboard.yml
 ┣ 📄 docker-compose.yml
 ┗ 📄 README.md
```

---

## 📝 Licença

Projeto acadêmico desenvolvido para a disciplina de Arquitetura de Software — PUC Minas.
