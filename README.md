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

O desenvolvimento deste desafio pode ser visualizado no PR abaixo: <VOU_COLOCAR_O_LINK_AQUI>
