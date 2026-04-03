# MedWork Clinic API

API REST para gestao de clinica de medicina do trabalho, com cadastros, lancamentos de atendimentos, controle financeiro e relatorios operacionais.

## Base URL

Local:

```text
http://localhost:8000
```

Documentacao automatica:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic

## Como rodar

1. Instale as dependencias:

```bash
python -m pip install -r requirements.txt
```

2. Crie o `.env` com base no `.env.example`.

3. Rode as migrations:

```bash
python -m alembic upgrade head
```

4. Popule dados iniciais opcionais:

```bash
python -m app.seed
```

5. Suba a API:

```bash
python -m uvicorn app.main:app --reload
```

## Variaveis de ambiente

Exemplo de `.env`:

```env
APP_NAME=MedWork Clinic API
APP_ENV=development
DATABASE_URL=postgresql+psycopg://medwork:medwork@localhost:5432/medwork
CORS_ORIGINS=http://localhost:3000
```

## Regras de negocio

- O status do atendimento e calculado automaticamente pela forma de pagamento.
- `forma_pagamento = faturado` gera `status = pendente`.
- `forma_pagamento = dinheiro` ou `pix` gera `status = pago`.
- Ao marcar um atendimento como pago em `PATCH /attendances/{id}/pay`, a API sempre grava `status = pago`.
- Se o payload de pagamento vier com `forma_pagamento = faturado`, a API ajusta automaticamente para `pix`.
- Ao criar ou atualizar um atendimento sem `valor`, a API usa o valor padrao do exame selecionado.
- Empresas e exames nao podem ser duplicados pelo nome.
- Empresas e exames com atendimentos vinculados nao podem ser excluidos.

## Healthcheck

### `GET /`

Retorna metadados basicos da API.

Resposta:

```json
{
  "message": "MedWork Clinic API",
  "docs": "/docs"
}
```

### `GET /health`

Resposta:

```json
{
  "status": "ok"
}
```

## Empresas

### `GET /companies`

Lista todas as empresas.

Resposta `200 OK`:

```json
[
  {
    "id": 1,
    "nome": "Metalurgica Horizonte",
    "tipo": "empresa"
  }
]
```

### `GET /companies/{company_id}`

Busca uma empresa por id.

Resposta `200 OK`:

```json
{
  "id": 1,
  "nome": "Metalurgica Horizonte",
  "tipo": "empresa"
}
```

### `POST /companies`

Cria uma empresa.

Payload:

```json
{
  "nome": "Metalurgica Horizonte",
  "tipo": "empresa"
}
```

Resposta `201 Created`:

```json
{
  "id": 1,
  "nome": "Metalurgica Horizonte",
  "tipo": "empresa"
}
```

### `PUT /companies/{company_id}`

Atualiza uma empresa.

Payload:

```json
{
  "nome": "Metalurgica Horizonte LTDA",
  "tipo": "empresa"
}
```

Resposta `200 OK`:

```json
{
  "id": 1,
  "nome": "Metalurgica Horizonte LTDA",
  "tipo": "empresa"
}
```

### `DELETE /companies/{company_id}`

Exclui uma empresa.

Resposta `204 No Content`

Erros comuns:

- `404`: empresa nao encontrada
- `409`: ja existe empresa com mesmo nome ou ha atendimentos vinculados

## Exames

### `GET /exams`

Lista todos os exames.

Resposta `200 OK`:

```json
[
  {
    "id": 1,
    "nome": "Audiometria",
    "valor": 45.0
  }
]
```

### `GET /exams/{exam_id}`

Busca um exame por id.

### `POST /exams`

Cria um exame.

Payload:

```json
{
  "nome": "Audiometria",
  "valor": 45.0
}
```

Resposta `201 Created`:

```json
{
  "id": 1,
  "nome": "Audiometria",
  "valor": 45.0
}
```

### `PUT /exams/{exam_id}`

Atualiza um exame.

Payload:

```json
{
  "nome": "Audiometria Ocupacional",
  "valor": 55.0
}
```

### `DELETE /exams/{exam_id}`

Exclui um exame.

Resposta `204 No Content`

Erros comuns:

- `404`: exame nao encontrado
- `409`: ja existe exame com mesmo nome ou ha atendimentos vinculados

## Atendimentos

### `GET /attendances`

Lista atendimentos, com filtros opcionais.

Query params:

- `empresa_id`: inteiro
- `status`: `pago` ou `pendente`
- `data_inicio`: `YYYY-MM-DD`
- `data_fim`: `YYYY-MM-DD`

Exemplo:

```text
GET /attendances?empresa_id=1&status=pendente&data_inicio=2026-03-01&data_fim=2026-03-31
```

Resposta `200 OK`:

```json
[
  {
    "id": 1,
    "data": "2026-03-31T13:20:00Z",
    "nome_paciente": "Carlos Silva",
    "empresa_id": 1,
    "empresa_nome": "Metalurgica Horizonte",
    "exame_id": 2,
    "exame_nome": "Audiometria",
    "valor": 45.0,
    "forma_pagamento": "faturado",
    "status": "pendente"
  }
]
```

### `GET /attendances/{attendance_id}`

Busca um atendimento por id.

### `POST /attendances`

Cria um atendimento.

Payload:

```json
{
  "nome_paciente": "Carlos Silva",
  "empresa_id": 1,
  "exame_id": 2,
  "valor": 45.0,
  "forma_pagamento": "faturado"
}
```

Resposta `201 Created`:

```json
{
  "id": 1,
  "data": "2026-03-31T13:20:00Z",
  "nome_paciente": "Carlos Silva",
  "empresa_id": 1,
  "empresa_nome": "Metalurgica Horizonte",
  "exame_id": 2,
  "exame_nome": "Audiometria",
  "valor": 45.0,
  "forma_pagamento": "faturado",
  "status": "pendente"
}
```

### `PUT /attendances/{attendance_id}`

Atualiza um atendimento.

Payload:

```json
{
  "nome_paciente": "Carlos Silva",
  "empresa_id": 1,
  "exame_id": 2,
  "valor": 60.0,
  "forma_pagamento": "pix"
}
```

Resposta `200 OK`:

```json
{
  "id": 1,
  "data": "2026-03-31T13:20:00Z",
  "nome_paciente": "Carlos Silva",
  "empresa_id": 1,
  "empresa_nome": "Metalurgica Horizonte",
  "exame_id": 2,
  "exame_nome": "Audiometria",
  "valor": 60.0,
  "forma_pagamento": "pix",
  "status": "pago"
}
```

### `PATCH /attendances/{attendance_id}/pay`

Marca um atendimento como pago.

Payload:

```json
{
  "forma_pagamento": "pix"
}
```

Resposta `200 OK`:

```json
{
  "id": 1,
  "data": "2026-03-31T13:20:00Z",
  "nome_paciente": "Carlos Silva",
  "empresa_id": 1,
  "empresa_nome": "Metalurgica Horizonte",
  "exame_id": 2,
  "exame_nome": "Audiometria",
  "valor": 60.0,
  "forma_pagamento": "pix",
  "status": "pago"
}
```

### `DELETE /attendances/{attendance_id}`

Exclui um atendimento.

Resposta `204 No Content`

Erros comuns:

- `404`: atendimento nao encontrado
- `422`: payload invalido

## Relatorios

### `GET /reports/dashboard`

Resumo financeiro do mes atual.

Resposta `200 OK`:

```json
{
  "mes_referencia": "2026-03",
  "total_faturado": 1200.0,
  "total_recebido": 800.0,
  "total_pendente": 400.0
}
```

### `GET /reports/months`

Lista os meses com movimentacao.

Resposta `200 OK`:

```json
{
  "meses": ["2026-03", "2026-02", "2026-01"]
}
```

### `GET /reports/month/{month}`

Retorna o fechamento mensal.

Formato do parametro `month`: `YYYY-MM`

Exemplo:

```text
GET /reports/month/2026-03
```

Resposta `200 OK`:

```json
{
  "mes": "2026-03",
  "total_faturado": 1200.0,
  "total_recebido": 800.0,
  "total_pendente": 400.0,
  "empresas_devedoras": [
    {
      "empresa_id": 1,
      "empresa_nome": "Metalurgica Horizonte",
      "total_pendente": 250.0,
      "quantidade_atendimentos": 3
    }
  ]
}
```

Erros comuns:

- `400`: mes invalido. Use `YYYY-MM`

### `GET /reports/company/{company_id}`

Detalhamento financeiro e operacional por empresa.

Resposta `200 OK`:

```json
{
  "empresa": {
    "id": 1,
    "nome": "Metalurgica Horizonte",
    "tipo": "empresa"
  },
  "total_exames": 8,
  "valor_total": 980.0,
  "exames_por_tipo": [
    {
      "exame_id": 2,
      "exame_nome": "Audiometria",
      "quantidade": 4,
      "valor_total": 220.0
    }
  ],
  "atendimentos": [
    {
      "id": 1,
      "data": "2026-03-31T13:20:00Z",
      "nome_paciente": "Carlos Silva",
      "empresa_id": 1,
      "empresa_nome": "Metalurgica Horizonte",
      "exame_id": 2,
      "exame_nome": "Audiometria",
      "valor": 60.0,
      "forma_pagamento": "pix",
      "status": "pago"
    }
  ]
}
```

## Codigos de status mais comuns

- `200 OK`: leitura ou atualizacao bem-sucedida
- `201 Created`: recurso criado
- `204 No Content`: recurso excluido
- `400 Bad Request`: parametro invalido
- `404 Not Found`: recurso nao encontrado
- `409 Conflict`: nome duplicado ou exclusao bloqueada por vinculos
- `422 Unprocessable Entity`: erro de validacao do payload

## Enumeracoes aceitas

### `tipo`

- `empresa`
- `pessoa_fisica`

### `forma_pagamento`

- `dinheiro`
- `pix`
- `faturado`

### `status`

- `pago`
- `pendente`
