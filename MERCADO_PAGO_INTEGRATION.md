# 🎁 Integração Mercado Pago - Guia Completo

## 📋 Sumário
1. [Visão Geral](#visão-geral)
2. [Setup Inicial](#setup-inicial)
3. [Configuração do Mercado Pago](#configuração-do-mercado-pago)
4. [Estrutura de Banco de Dados](#estrutura-de-banco-de-dados)
5. [API Endpoints](#api-endpoints)
6. [Webhook Integration](#webhook-integration)
7. [Frontend Integration](#frontend-integration)
8. [Produção](#produção)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

Esta integração permite que os convidados presenteiem pela lista de presentes usando Mercado Pago (PIX, cartão de crédito, débito).

### Fluxo de Pagamento:

```
1. Convidado clica "Presentear"
   ↓
2. Modal abre com formulário (nome, email, telefone, mensagem)
   ↓
3. Clica "Continuar para pagamento"
   ↓
4. Frontend faz POST para /criar_pagamento/<presente_id>
   ↓
5. Backend cria preferência no Mercado Pago
   ↓
6. Backend retorna init_point (link de pagamento)
   ↓
7. Frontend redireciona para Mercado Pago
   ↓
8. Convidado realiza o pagamento (PIX/Cartão)
   ↓
9. Mercado Pago envia webhook com notificação de pagamento
   ↓
10. Backend atualiza status do presente para "indisponivel"
    ↓
11. Presente some da lista no frontend
```

---

## 🚀 Setup Inicial

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Executar Migrations de Banco de Dados

Execute o SQL em seu editor Supabase:

```sql
-- Abra: migrations/add_mercado_pago_tables.sql
-- Cole no SQL Editor do Supabase e execute
```

Isso criará as tabelas:
- `pagamentos_mercado_pago` - Registra cada transação
- `webhook_logs` - Auditoria de webhooks

### 3. Configurar Variáveis de Ambiente

Copie o arquivo `.env.example`:

```bash
cp .env.example .env
```

Edite `.env` com suas credenciais (ver próxima seção).

---

## 🔑 Configuração do Mercado Pago

### 1. Criar Conta Mercado Pago

1. Acesse: https://www.mercadopago.com.br
2. Crie uma conta (ou use existente)
3. Acesse: https://www.mercadopago.com.br/developers/pt-BR/docs

### 2. Obter Credenciais de Teste

1. Vá para: Dashboard > Configurações > Tokens
2. Copie o **Access Token** (tipo `APP_USR-...`)
3. Copie a **Public Key** (tipo `APP_USR-...`)

### 3. Adicionar ao .env

```env
MERCADO_PAGO_ACCESS_TOKEN=APP_USR-7108049560326594-042212-ee879f6a87885115519a5fed61ab8c04-3352130635
MERCADO_PAGO_PUBLIC_KEY=APP_USR-583c2032-5036-4f0f-a2f8-c6cef74d0347
BASE_URL=http://localhost:5000
```

### 4. Configurar Webhook

1. Vá para: Dashboard > Configurações > Webhooks
2. URL do webhook: `https://seu-dominio.com/webhook/mercado_pago`
3. Selecione eventos:
   - `payment.created`
   - `payment.updated`

---

## 📊 Estrutura de Banco de Dados

### Tabela: presentes

```sql
CREATE TABLE presentes (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255),           -- Nome do presente
    descricao TEXT,                -- Descrição
    valor_sugerido DECIMAL(10,2),  -- Valor em R$
    imagem VARCHAR(500),           -- URL da imagem
    status VARCHAR(50),            -- 'disponivel' ou 'indisponivel'
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Tabela: pagamentos_mercado_pago

```sql
CREATE TABLE pagamentos_mercado_pago (
    id SERIAL PRIMARY KEY,
    presente_id INTEGER REFERENCES presentes(id),
    mercado_pago_id BIGINT UNIQUE,    -- ID do pagamento no MP
    status VARCHAR(50),                -- pending, approved, cancelled, refunded
    valor DECIMAL(10, 2),              -- Valor pago
    nome_pagador VARCHAR(255),         -- Quem pagou
    email_pagador VARCHAR(255),        -- Email de quem pagou
    telefone_pagador VARCHAR(20),      -- Telefone
    mensagem_pagador TEXT,             -- Mensagem opcional
    metodo_pagamento VARCHAR(50),      -- credit_card, debit_card, pix
    preferencia_id VARCHAR(255) UNIQUE,-- ID da preferência no MP
    init_point VARCHAR(500),           -- Link de pagamento
    payment_date TIMESTAMP,            -- Quando foi pago
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Tabela: webhook_logs

```sql
CREATE TABLE webhook_logs (
    id SERIAL PRIMARY KEY,
    mercado_pago_id BIGINT,
    tipo_notificacao VARCHAR(50),  -- payment, plan, subscription
    status VARCHAR(50),            -- recebido, processado, erro_update_presente
    dados_json JSONB,              -- Dados completos do webhook
    processado BOOLEAN,            -- Se foi processado com sucesso
    erro VARCHAR(500),             -- Mensagem de erro se houver
    created_at TIMESTAMP
);
```

---

## 🔌 API Endpoints

### POST /criar_pagamento/<presente_id>

Cria uma preferência de pagamento no Mercado Pago.

**Request:**
```json
POST /criar_pagamento/1 HTTP/1.1
Content-Type: application/json

{
    "nome_pagador": "João Silva",
    "email_pagador": "joao@email.com",
    "telefone_pagador": "11987654321",
    "mensagem_pagador": "Parabéns aos noivos! 💙"
}
```

**Response (Sucesso):**
```json
{
    "sucesso": true,
    "init_point": "https://www.mercadopago.com.br/checkout/v1/refresh?pref_id=12345678-abcd",
    "preferencia_id": "12345678-abcd",
    "pagamento_id": 42
}
```

**Response (Erro):**
```json
{
    "sucesso": false,
    "erro": "Email válido é obrigatório"
}
```

**Status Codes:**
- `200` - Sucesso
- `400` - Dados inválidos
- `404` - Presente não encontrado
- `500` - Erro interno

---

### POST /webhook/mercado_pago

Recebe notificações de pagamento do Mercado Pago.

**Como funciona:**
1. Mercado Pago envia `POST` quando há alteração no pagamento
2. Sistema consulta detalhes completos do pagamento no MP
3. Atualiza status no banco de dados
4. Se status for `approved`, marca presente como `indisponivel`
5. Se status for `cancelled/refunded`, marca como `disponivel` novamente

**Dados Recebidos:**
```
type=payment
id=1234567890
topic=payment
(enviado como form data)
```

---

### GET /api/status_pagamento/<presente_id>

Consulta status de um presente (se foi presenteado ou não).

**Request:**
```
GET /api/status_pagamento/1
```

**Response:**
```json
{
    "presente_id": 1,
    "status": "disponivel"  // ou "indisponivel"
}
```

---

## 🔔 Webhook Integration

### Teste do Webhook em Desenvolvimento

Use ngrok para expor localhost:

```bash
# 1. Instale ngrok
# https://ngrok.com/download

# 2. Crie um túnel
ngrok http 5000

# 3. Configure na URL do .env
BASE_URL=https://seu-ngrok-url.ngrok.io

# 4. Registre o webhook no Mercado Pago
# https://seu-ngrok-url.ngrok.io/webhook/mercado_pago
```

### Monitorar Webhooks

Veja logs de webhooks na tabela `webhook_logs`:

```sql
SELECT * FROM webhook_logs 
ORDER BY created_at DESC 
LIMIT 20;
```

Campos importantes:
- `status`: recebido, processado, erro_*
- `dados_json`: Dados completos da notificação
- `erro`: Mensagem se algo deu errado

---

## 🎨 Frontend Integration

### Modal do Presentes

O modal está em `templates/index.html`:

```html
<div class="modal-presente" id="modalPresente">
    <form id="formPresentear">
        <input type="hidden" id="modalPresenteId">
        <input type="text" id="nome_pagador" required>
        <input type="email" id="email_pagador" required>
        <input type="tel" id="telefone_pagador" required>
        <textarea id="mensagem_pagador"></textarea>
        <button type="submit">Continuar para o pagamento</button>
    </form>
</div>
```

### JavaScript Handler

Arquivo: `static/js/main.js`

O script:
1. Aguarda clique em "Presentear"
2. Abre modal com formulário
3. Ao submit, faz fetch para `/criar_pagamento/<presente_id>`
4. Redireciona para `init_point` do Mercado Pago
5. Mercado Pago exibe checkout (PIX/Cartão)

```javascript
// Extrair do main.js - linhas ~228-282
formPresentear.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const response = await fetch(`/criar_pagamento/${presenteId}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({...dados})
    });
    
    const data = await response.json();
    if (data.sucesso) {
        window.location.href = data.init_point;  // Redireciona para MP
    }
});
```

---

## 📦 Produção

### 1. Mudar para Credenciais de Produção

No Mercado Pago:
1. Dashboard > Configurações > Tokens
2. Mude de "Credenciais de teste" para "Credenciais de produção"
3. Copie novos tokens

Atualize `.env`:
```env
MERCADO_PAGO_ACCESS_TOKEN=APP_USR-xxxxx-produção
MERCADO_PAGO_PUBLIC_KEY=APP_USR-xxxxx-produção
BASE_URL=https://casamento-karine-josue.com
```

### 2. Configurar Webhook em Produção

1. Dashboard Mercado Pago > Webhooks
2. URL: `https://casamento-karine-josue.com/webhook/mercado_pago`
3. Eventos: `payment.created`, `payment.updated`

### 3. Teste Completo

1. Acesse seu site em produção
2. Clique em "Presentear"
3. Use cartão de teste MP:
   - Número: 4111 1111 1111 1111
   - Vencimento: 12/25
   - CVV: 123
4. Verifique se presente ficou indisponível

### 4. Monitoramento

Acompanhe:
- Logs de webhook: `SELECT * FROM webhook_logs`
- Pagamentos: `SELECT * FROM pagamentos_mercado_pago`
- Dashboard Mercado Pago: https://www.mercadopago.com.br

---

## 🔧 Troubleshooting

### Problema: "Presente não encontrado"

**Causa:** ID do presente inválido ou presente não existe no banco

**Solução:**
```sql
-- Verifique se presentes existem
SELECT id, titulo, status FROM presentes;

-- Adicione presentes se necessário
INSERT INTO presentes 
(titulo, descricao, valor_sugerido, status) 
VALUES 
('Nome do Presente', 'Descrição', 100.00, 'disponivel');
```

---

### Problema: "Erro ao processar pagamento"

**Causa:** Credenciais do Mercado Pago inválidas

**Solução:**
1. Verifique `.env`:
   ```bash
   cat .env | grep MERCADO_PAGO
   ```
2. Copie novos tokens do dashboard MP
3. Reinicie a aplicação

---

### Problema: Webhook não chega

**Causa:** URL não está acessível ou webhook não configurado

**Solução:**
1. Teste com ngrok em desenvolvimento:
   ```bash
   ngrok http 5000
   # Use URL do ngrok em .env
   ```
2. Verifique logs de webhook:
   ```sql
   SELECT * FROM webhook_logs ORDER BY created_at DESC;
   ```
3. No dashboard MP, vá para "Notificações entregues" para ver status

---

### Problema: Presente não fica indisponível após pagamento

**Causa:** Webhook não processou ou erro no UPDATE

**Solução:**
1. Verifique tabela de logs:
   ```sql
   SELECT * FROM webhook_logs 
   WHERE erro IS NOT NULL 
   ORDER BY created_at DESC;
   ```
2. Verifique pagamentos:
   ```sql
   SELECT * FROM pagamentos_mercado_pago 
   WHERE status = 'approved';
   ```
3. Veja logs da aplicação:
   ```bash
   tail -f gunicorn.log  # em produção
   ```

---

### Problema: Erro "payment not found" no webhook

**Causa:** Mercado Pago envia notificação antes de confirmar pagamento

**Solução:** Sistema tenta novamente. Verifique depois de alguns minutos.

---

## 📞 Suporte

Para problemas com Mercado Pago:
- Docs: https://www.mercadopago.com.br/developers
- Status: https://www.mercadopagostatus.com/
- Email: desarrolladores@mercadopago.com

---

## ✅ Checklist de Produção

- [ ] Credenciais de produção configuradas em `.env`
- [ ] Webhook configurado no dashboard MP
- [ ] Base de dados migrada (`add_mercado_pago_tables.sql`)
- [ ] `BASE_URL` apontando para domínio correto
- [ ] HTTPS configurado no servidor
- [ ] Testes de pagamento realizados
- [ ] Logs de webhook monitorados
- [ ] Backup do banco de dados realizado
- [ ] Equipe informada sobre novo sistema de pagamentos

---

**Última atualização:** 22 de Abril de 2026
**Versão:** 1.0.0 - Production Ready
