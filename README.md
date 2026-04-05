# MedWork Clinic API

API REST da plataforma financeira e operacional da clinica de medicina do trabalho.

## Objetivo

O backend centraliza:

- autenticacao por usuario e senha com cadastro em banco
- cadastro de empresas
- cadastro de exames
- lancamento de atendimentos
- controle de faturamento, pendencias e baixas
- fechamento mensal por competencia de cobranca
- detalhamento por empresa
- geracao de extrato em PDF

## Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic

## Estrutura do projeto

```text
app/
  core/
    config.py
    security.py
  models/
    attendance.py
    company.py
    exam.py
    user.py
  routes/
    auth.py
    attendances.py
    companies.py
    exams.py
    reports.py
  schemas/
    attendance.py
    auth.py
    company.py
    exam.py
    report.py
  services/
    attendance_service.py
    company_service.py
    exam_service.py
    pdf_service.py
    report_service.py
    serializers.py
    user_service.py
  database.py
  main.py
alembic/
  env.py
  versions/
    0001_create_initial_tables.py
    0002_add_financial_identity_fields.py
    0003_add_attendance_billing_competence.py
    0004_create_users_table.py
```

## Modelo de dados

### `empresas`

- `id`
- `nome`
- `tipo`
- `documento`
- `contato`

### `exames`

- `id`
- `nome`
- `valor`

### `atendimentos`

- `id`
- `data`
- `competencia_cobranca`
- `data_pagamento`
- `nome_paciente`
- `cpf_paciente`
- `empresa_id`
- `exame_id`
- `valor`
- `forma_pagamento`
- `status`

### `usuarios`

- `id`
- `nome`
- `username`
- `password_hash`
- `created_at`

## Regras de negocio

### Autenticacao

- usuarios sao cadastrados no banco pela rota `POST /auth/register`
- login usa `username` e `password`
- senha e armazenada com hash PBKDF2 SHA-256
- rotas de negocio exigem token bearer
- `GET /health` e `GET /` permanecem publicas

### Atendimentos

- `valor` do atendimento usa o valor do exame quando o payload nao envia valor
- `forma_pagamento = faturado` gera `status = pendente`
- `forma_pagamento = dinheiro` ou `pix` gera `status = pago`
- `data_pagamento` e gravada quando o atendimento nasce pago ou quando uma baixa e executada depois

### Competencia de cobranca

- atendimentos pagos no ato entram na competencia do proprio mes do atendimento
- atendimentos `faturado` entram na competencia do mes seguinte
- o fechamento mensal usa `competencia_cobranca`, nao apenas a data do atendimento
- isso permite que exames realizados em um mes componham a cobranca do mes seguinte quando forem faturados

### Fechamento mensal

- `GET /reports/month/{month}` retorna total faturado, total recebido, total pendente e ranking de empresas devedoras da competencia informada
- `GET /reports/company/{company_id}` detalha exames, valores e atendimentos por empresa
- o detalhamento aceita `month` ou `data_inicio` + `data_fim`
- `POST /reports/company/{company_id}/settle` baixa todos os atendimentos pendentes da empresa no periodo informado
- a baixa em lote atualiza `status`, `forma_pagamento` e `data_pagamento`

### Exclusoes e integridade

- empresas e exames com atendimentos vinculados nao podem ser removidos
- nomes de empresa e exame devem ser unicos
- login de usuario deve ser unico

## Fluxo de autenticacao

### Cadastro

`POST /auth/register`

Payload:

```json
{
  "nome": "Nome do usuario",
  "username": "login",
  "password": "senha-segura"
}
```

Resposta:

```json
{
  "access_token": "<token>",
  "token_type": "bearer",
  "expires_in_seconds": 43200,
  "user": {
    "id": 1,
    "nome": "Nome do usuario",
    "username": "login",
    "created_at": "2026-04-05T12:00:00Z"
  }
}
```

### Login

`POST /auth/login`

Payload:

```json
{
  "username": "login",
  "password": "senha-segura"
}
```

### Sessao atual

`GET /auth/me`

Header:

```text
Authorization: Bearer <token>
```

## Rotas principais

### Publicas

- `GET /`
- `GET /health`
- `POST /auth/register`
- `POST /auth/login`

### Protegidas

- `GET /auth/me`
- `GET/POST/PUT/DELETE /companies`
- `GET/POST/PUT/DELETE /exams`
- `GET/POST/PUT/PATCH/DELETE /attendances`
- `GET /reports/dashboard`
- `GET /reports/months`
- `GET /reports/month/{month}`
- `GET /reports/company/{company_id}`
- `POST /reports/company/{company_id}/settle`
- `GET /reports/company/{company_id}/pdf`

## Filtros e contratos importantes

### `GET /attendances`

Query params:

- `empresa_id`
- `status`
- `data_inicio`
- `data_fim`

Esse endpoint filtra pela data real do atendimento.

### `GET /reports/company/{company_id}`

Aceita um destes recortes:

- `month=YYYY-MM`
- `data_inicio=YYYY-MM-DD&data_fim=YYYY-MM-DD`

Esse endpoint filtra pela competencia de cobranca.

### `POST /reports/company/{company_id}/settle`

Payload:

```json
{
  "month": "2026-04",
  "forma_pagamento": "pix"
}
```

Ou:

```json
{
  "data_inicio": "2026-04-01",
  "data_fim": "2026-04-30",
  "forma_pagamento": "pix"
}
```

## Variaveis de ambiente

```env
APP_NAME=MedWork Clinic API
APP_ENV=development
DATABASE_URL=postgresql+psycopg://medwork:medwork@localhost:5432/medwork
CORS_ORIGINS=http://localhost:3000
CLINIC_NAME=Nuemo
PORT=8000
```

## Executar localmente

1. Instale dependencias:

```bash
python -m pip install -r requirements.txt
```

2. Configure o `.env`.

3. Rode as migrations:

```bash
python -m alembic upgrade head
```

4. Suba a API:

```bash
python -m uvicorn app.main:app --reload
```

## Executar com Docker

O container:

- aplica migrations na inicializacao
- sobe o Uvicorn usando a porta definida em `PORT`
- nao injeta dados ficticios automaticamente

## Deploy no Railway

Variaveis minimas:

```env
APP_ENV=production
DATABASE_URL=${{Postgres.DATABASE_URL}}
CORS_ORIGINS=https://seu-front.vercel.app
CLINIC_NAME=Nuemo
PORT=8000
```

## Healthcheck

### `GET /health`

Resposta:

```json
{
  "status": "ok"
}
```

## Integracao com o frontend

- o frontend Next.js usa `/api` localmente e em producao
- a rota `frontend/app/api/[...path]/route.ts` faz o proxy para o backend
- o cookie de sessao `nuemo_session` e convertido em `Authorization: Bearer <token>` antes de chamar a API
- a assinatura dos tokens e derivada automaticamente da `DATABASE_URL`, podendo ser sobrescrita por `AUTH_SECRET_KEY` se voce quiser fixar uma chave propria

## Estado atual do software

Ja implementado no backend:

- autenticacao com cadastro e login
- faturamento por competencia
- data de pagamento
- relatorios mensais
- drill-down por empresa
- baixa em lote
- extrato PDF

Fora do escopo do codigo e ainda dependente de infraestrutura:

- backups automatizados
- politicas de SLA
- monitoramento e observabilidade de producao
