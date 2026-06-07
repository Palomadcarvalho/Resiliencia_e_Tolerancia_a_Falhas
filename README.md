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

A aplicação simula uma **API acadêmica** que depende de serviços externos, como:

- Consulta de endereço por CEP
- Envio de e-mail
- Processamento de pagamento
- Autenticação de usuários
- Validação de CPF
- Integração com sistemas externos

Esses serviços podem **falhar**, **demorar a responder** ou ficar **temporariamente indisponíveis**. Os mecanismos implementados visam reduzir o impacto dessas falhas sobre a aplicação principal.

---

## ⚙️ Mecanismos de Resiliência Implementados

Os mecanismos abaixo foram implementados conforme os requisitos do trabalho:

### 🔁 Retry
Reenvio automático de requisições em caso de falha temporária, com controle de número de tentativas e intervalo entre elas.

**Trade-offs:** Aumenta a latência total em caso de falhas consecutivas; pode sobrecarregar um serviço já instável.

### ⏱️ Timeout
Limite de tempo para aguardar a resposta de um serviço externo. Se o tempo for excedido, a operação é cancelada e tratada como falha.

**Trade-offs:** Um timeout muito curto pode descartar respostas válidas; muito longo impacta a experiência do usuário.

### 🔀 Fallback
Resposta alternativa (padrão ou cache) fornecida ao usuário quando o serviço principal não está disponível, garantindo degradação controlada.

**Trade-offs:** O dado de fallback pode estar desatualizado; o usuário pode não perceber que está recebendo uma resposta alternativa.

### 🔌 Circuit Breaker
Interrompe automaticamente as chamadas ao serviço externo após um número de falhas consecutivas, evitando sobrecarga. Após um período de espera, tenta restabelecer a conexão.

**Trade-offs:** Pode rejeitar requisições mesmo quando o serviço já se recuperou; requer ajuste fino dos limiares.

---

## 🚀 Como Executar

### Pré-requisitos

- [PREENCHER]

### Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio

# Instale as dependências
[comando de instalação]
```

### Execução

```bash
# Suba os serviços
[comando para iniciar a aplicação]

# Exemplo: com Docker Compose
docker-compose up --build
```

---

## 🧪 Demonstrações

As seguintes situações podem ser simuladas para demonstrar o comportamento resiliente da aplicação:

| Cenário | Como simular | Comportamento esperado |
|--------|--------------|------------------------|
| ✅ Chamada bem-sucedida | Requisição normal | Resposta 200 com dados do serviço |
| 🐢 Lentidão | [descrever forma de simular] | Timeout acionado após X segundos |
| ❌ Falha total | [descrever forma de simular] | Retry + Fallback ou Circuit Breaker |
| 🔁 Retry | Falha intermitente | N tentativas antes de desistir |
| 🔌 Circuit Breaker aberto | Falhas consecutivas | Requisições rejeitadas sem chamar o serviço |

---

## 📊 Métricas e Logs

Os logs e métricas da aplicação evidenciam o comportamento resiliente em cada cenário. Para visualizá-los:

```bash
# Exemplo: visualizar logs em tempo real
[comando para acessar logs]

# Exemplo: acessar dashboard de métricas
[URL do Grafana, Prometheus, etc.]
```

---

## 🏗️ Arquitetura

```
[Adicionar diagrama de arquitetura da solução]
```

**Tecnologias utilizadas:**
- **Back-end:** [ex: Node.js / Java / Python / Go]
- **Resiliência:** [ex: Resilience4J / Polly / Hystrix / Spring Retry]
- **Monitoramento:** [ex: Prometheus / Grafana / OpenTelemetry]
- **Infraestrutura:** [ex: Docker / Docker Compose]
- **Banco de dados:** [ex: PostgreSQL / MongoDB / Redis]

---

## 📐 Decisões Arquiteturais

### Por que escolhemos essas estratégias?

[Descrever aqui as justificativas para as escolhas feitas, os trade-offs considerados e como cada mecanismo contribui para a resiliência geral do sistema.]

### Impactos arquiteturais

- **Retry + Timeout:** Trabalham em conjunto para equilibrar persistência e responsividade.
- **Fallback + Circuit Breaker:** Garantem degradação controlada e proteção contra cascata de falhas.
- **Health Check:** Permite visibilidade proativa do estado dos serviços.

---

## 📁 Estrutura do Projeto

```
📦 projeto
 ┣ 📂 src/
 ┃ ┣ 📂 api/
 ┃ ┣ 📂 services/
 ┃ ┣ 📂 resilience/
 ┃ ┗ 📂 config/
 ┣ 📂 tests/
 ┣ 📂 docs/
 ┣ 📄 docker-compose.yml
 ┗ 📄 README.md
```

---

## 📝 Licença

Projeto acadêmico desenvolvido para a disciplina de Arquitetura de Software — PUC Minas.
