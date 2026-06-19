# Trade-offs: Retry com Backoff e Timeout

Este documento descreve os mecanismos de **Retry com Backoff** e **Timeout** aplicados no projeto, detalhando a implementação técnica e os trade-offs de cada escolha arquitetural.

---

## 1. Retry com Backoff Exponencial

**Implementação Técnica**
O mecanismo de retry, construído com a biblioteca `tenacity`, realiza até 3 tentativas de comunicação quando ocorrem falhas transitórias. A lógica é configurada para atuar apenas em situações de instabilidade de rede (Timeout) ou erros no servidor de destino (erros na faixa 5xx). Requisições que falham devido a erros do cliente (erros na faixa 4xx, como `400 Bad Request`) não disparam novas tentativas, visto que repetir um pedido incorreto não altera o resultado.

A estratégia utiliza um **Backoff Exponencial**, o que significa que o intervalo entre as tentativas aumenta de forma progressiva (1s, depois 2s, e finalmente 4s). O objetivo principal dessa abordagem é evitar a sobrecarga da rede e do serviço dependente.

### Trade-offs do Retry

**Vantagens:**
- **Recuperação Transparente:** O sistema consegue superar pequenas instabilidades de rede sem repassar o erro diretamente para o usuário.
- **Prevenção de Sobrecarga:** O tempo de espera crescente entre as tentativas reduz a pressão sobre um serviço que já está enfrentando problemas, evitando ataques de negação de serviço (DDoS) acidentais.

**Desvantagens e Riscos:**
- **Aumento da Latência Total:** Quando o serviço externo fica completamente indisponível, o cliente acaba esperando pela soma do tempo de todas as tentativas e dos intervalos de backoff antes de receber a resposta de falha definitiva.
- **Risco em Operações Não-Idempotentes:** O retry é extremamente seguro para consultas (GET). Porém, ao utilizá-lo em operações de criação ou edição de dados (POST, PUT), existe o risco de gerar registros duplicados caso o erro ocorra apenas no retorno da resposta e a ação já tenha sido processada no destino.

---

## 2. Timeout (Tempo Limite)

**Implementação Técnica**
A aplicação estabelece um limite máximo de 5 segundos de espera por uma resposta do serviço externo. A comunicação utiliza um pool de conexões globais por meio da biblioteca `httpx`, reaproveitando conexões abertas para otimizar a performance. 

Além do limite total de 5 segundos, há um limite específico de 2 segundos para o estabelecimento inicial da conexão (connect timeout). Essa separação permite interromper rapidamente requisições que ficam travadas logo no momento de se conectar ao serviço.

### Trade-offs do Timeout

**Vantagens:**
- **Falha Rápida (Fail-Fast):** Fluxos que demoram demais são interrompidos de maneira ágil, permitindo que a aplicação adote uma resposta alternativa (Fallback) sem deixar o usuário esperando por tempo indeterminado.
- **Proteção contra Esgotamento de Recursos:** A interrupção por timeout garante que as conexões não fiquem presas para sempre, o que poderia esgotar a capacidade de processamento do servidor principal.

**Desvantagens e Riscos:**
- **Complexidade de Ajuste Fino:** Um tempo limite muito apertado corre o risco de cancelar requisições legítimas que apenas exigiam um processamento maior. Por outro lado, um tempo longo demais atrasa a resposta ao usuário e diminui a capacidade de vazão do sistema durante falhas.
- **Processamento Órfão no Destino:** Quando a aplicação encerra a espera após 5 segundos, o serviço externo pode continuar processando a requisição do lado dele de forma invisível. Em cenários que envolvem dados críticos, isso demanda cuidado extra para manter a consistência entre os sistemas.

---

### Resumo Arquitetural
Na prática, o Timeout e o Retry operam em conjunto como uma defesa em camadas. O Timeout garante um teto de espera para proteger o sistema principal (falhando rápido). Imediatamente depois, o Retry com Backoff confere resiliência lidando com as falhas rápidas por meio de novas tentativas espaçadas, garantindo que os componentes da arquitetura não sejam sobrecarregados.

---

## 3. Fallback

**Implementação Técnica**
Quando o Retry esgota as tentativas e a integração com o serviço externo ainda falha, a aplicação não devolve um erro bruto para o usuário. Em vez disso, ela retorna uma resposta alternativa com o status `matricula_pendente`, indicando que a operação principal foi registrada, mas a validação do CPF não pôde ser concluída no momento.

No código, o fallback é acionado em dois cenários: quando as tentativas falham completamente e quando o circuit breaker já está aberto e bloqueia novas chamadas para o serviço externo.

### Trade-offs do Fallback

**Vantagens:**
- **Experiência Controlada:** O usuário recebe uma resposta compreensível e estável, mesmo quando a dependência externa falha.
- **Continuidade do Negócio:** A operação principal segue adiante com estado pendente, evitando que uma falha externa pare completamente o fluxo da API.

**Desvantagens e Riscos:**
- **Consistência Diferida:** A validação real não acontece imediatamente, então é necessário um mecanismo posterior para concluir a operação pendente.
- **Risco de Mascarar Problemas:** Se o fallback for usado com muita frequência, ele pode esconder uma degradação sistêmica que deveria ser investigada com prioridade.

---

## 4. Circuit Breaker

**Implementação Técnica**
O circuit breaker evita que a aplicação continue insistindo em uma dependência que já demonstrou instabilidade. Depois de um número definido de falhas consecutivas, o circuito abre e passa a rejeitar novas chamadas por um período de tempo. Nesse intervalo, a aplicação responde rapidamente sem gastar tempo tentando acessar o serviço externo repetidamente.

No retorno à metade do tempo de abertura, o circuito entra em estado half-open para testar se a dependência se recuperou. Se a chamada de teste funcionar, ele volta para closed; se falhar, abre novamente.

### Trade-offs do Circuit Breaker

**Vantagens:**
- **Redução de Latência em Cascata:** Evita que várias requisições fiquem presas aguardando timeout quando a dependência já está claramente indisponível.
- **Proteção da Aplicação Principal:** Impede que uma falha externa consuma recursos do sistema e degrade os demais fluxos.

**Desvantagens e Riscos:**
- **Falsos Positivos:** Se o limite de abertura for agressivo demais, o circuito pode abrir mesmo para falhas transitórias curtas.
- **Estado Local:** Nesta implementação, o estado fica em memória, então ele vale apenas para uma instância do serviço. Em produção, isso deveria ser compartilhado em um armazenamento externo, como Redis.

### Resumo Arquitetural
O Fallback e o Circuit Breaker trabalham juntos. O circuit breaker impede novas tentativas quando a dependência já está degradada; o fallback garante que, mesmo assim, o usuário receba uma resposta controlada. A combinação reduz latência, melhora a experiência do usuário e evita desperdício de recursos durante falhas persistentes.
