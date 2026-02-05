# Cakto Mini Split Engine 🌵

API de pagamentos focada em split de recebíveis, cálculo de taxas e garantia de consistência financeira (Idempotência e Ledger).

## 🚀 Como Rodar?

### Pré-requisitos:

- Python 3.8+ 🐍
- Docker e Docker Compose 🐳

### Passo a Passo:

1. **Clone o repositório:**

   ```
   git clone https://github.com/estelamdrs/cakto-mini-split-engine.git
   cd cakto-mini-split-engine
   ```

2. **Configure o ambiente:**

Copie o arquivo de exemplo para criar o seu .env.

As configurações padrão já funcionam com o Docker.

    cp .env.example .env

3. **Execute o container:**

Este comando irá construir a imagem, aguardar o banco de dados, rodar as migrações automaticamente e subir o servidor.

    docker-compose up --build

A API estará disponível para o teste em [POST] http://localhost:8000/api/v1/payments

## **🧪 Rodando os Testes**

Para garantir um ambiente isolado e evitar conflitos de dependências, recomenda-se rodar os testes dentro do container Docker:

1. Certifique-se que o projeto está rodando (passo anterior).
2. Em um novo terminal, acesse o diretório do repositório e execute:

   ```
   docker-compose exec web python manage.py test
   ```

## **🧠 Decisões de Arquitetura e Design**

1. Precisão Financeira (Decimal)

Para evitar erros de ponto flutuante comuns em tipos float, utilizei estritamente o tipo Decimal do Python e do MySQL.

Estratégia de Arredondamento: O sistema calcula os splits com precisão de 2 casas decimais. Qualquer centavo residual decorrente de dízimas é alocado ao último recebedor da lista (ou ao recebedor principal), garantindo que a equação Soma das Partes == Valor Líquido seja sempre verdadeira (Zero-Sum Game).

2. Consistência e Atomicidade

Adotei o padrão de Transação Atômica (transaction.atomic). A criação do Payment, os lançamentos no Ledger e o evento de Outbox ocorrem tudo-ou-nada. Isso impede estados inconsistentes (ex: pagamento criado sem ledger) em caso de falha no meio do processo.

3. Idempotência

Implementada via header Idempotency-Key.

Cenário de Sucesso: Se a chave já existe e o payload é idêntico, retornamos 200 OK com os dados originais, sem reprocessar.

Cenário de Conflito: Se a chave existe mas o payload (valor) difere, retornamos 409 Conflict, protegendo o sistema de duplicidades acidentais.

4. Outbox Pattern

Para permitir arquitetura orientada a eventos, o sistema persiste um OutboxEvent na mesma transação do pagamento. Isso garante que o evento payment_captured exista no banco para ser processado posteriormente por um worker (fora do escopo deste MVP) e enviado a um message broker (RabbitMQ/Kafka).

## **🤖 Uso de IA**

Conforme permitido nas regras, utilizei IA (Gemini) como "Pair Programmer" para:

- Setup inicial da infraestrutura Docker e configurações do Django.
- Refinamento de cenários de teste (Edge cases matemáticos) e documentação.
- Discussão sobre estratégias de tratamento de erro e serialização.

Toda a lógica de negócios, decisões de arredondamento e implementação final foram validadas manualmente.

## **🔗 Pull Request**

O desenvolvimento deste desafio pode ser visualizado no PR a seguir: [PR #1](https://github.com/estelamdrs/cakto-mini-split-engine/pull/1)

---

## 🏗️ Decisões Técnicas e Arquiteturais

### 1. Precisão Financeira e Arredondamento

Para garantir a integridade dos cálculos, aboli o uso de `float` e adotei estritamente **Decimal** (Python) e **DECIMAL(19,2)** (Banco de Dados).

- **A Regra do Centavo:** Em divisões de split onde o resultado gera dízimas (ex: 100 / 3), a estratégia adotada foi o "Zero-Sum Game". O sistema calcula os valores arredondando para baixo (floor) e **aloca a diferença de centavos ao recebedor principal (ou último da lista)**.

- **Por quê?** Isso garante que a soma das partes (`receivables`) seja **sempre** matematicamente igual ao todo (`net_amount`), evitando furos contábeis.

### 2. Estratégia de Idempotência

A idempotência é garantida através do header `Idempotency-Key` e validada antes de qualquer processamento:

1.  **Chave Existente + Mesmo Payload:** O sistema entende como uma retransmissão de rede, ignora o processamento e retorna o sucesso original (`200 OK`).

2.  **Chave Existente + Payload Diferente:** O sistema identifica inconsistência e bloqueia a operação com `409 Conflict`, protegendo contra dados corrompidos.

### 3. Métricas de Produção (Observabilidade)

Se estivesse rodando este serviço em produção hoje, monitoraria os seguintes sinais vitais (Golden Signals):

- **Latência p95 e p99:** Para garantir que o cálculo de taxas não está gargalando o checkout.
- **Taxa de Erros 4xx vs 5xx:** Monitorar picos de `409 Conflict` (problemas de integração do cliente) vs `500` (falhas internas).

- **Lag da Tabela Outbox:** Monitorar se os eventos `payment_captured` estão acumulando sem serem processados.

- **Discrepância Financeira:** Um alerta crítico caso `gross_amount - fees != sum(splits)`.

### 4. O que faria com mais tempo (Next Steps)

Dado o escopo de 1 hora, priorizei a lógica core. Em uma v2, focaria em:

- **Processamento Assimétrico Real:** Implementar um worker (Celery + Redis/RabbitMQ) para ler a tabela Outbox e publicar mensagens reais.

- **Autenticação:** Adicionar camada de segurança (JWT ou API Key) para proteger os endpoints.

- **CI/CD:** Pipeline no GitHub Actions para rodar testes e lint (flake8/black) automaticamente a cada PR.

- **Docker Otimizado:** Configurar um container específico de produção (gunicorn) em vez do `runserver` de desenvolvimento.
