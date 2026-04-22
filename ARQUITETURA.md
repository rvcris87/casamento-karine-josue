# 🏗️ ARQUITETURA DA SOLUÇÃO - DIAGRAMA VISUAL

## 1️⃣ ARQUITETURA GERAL

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          NAVEGADOR DO CONVIDADO                         │
│                         (Frontend - HTML/CSS/JS)                        │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ index.html                                                     │   │
│  │ - Layout do site                                              │   │
│  │ - Modal de presentes (formPresentear)                         │   │
│  │ - Partials: presentes.html                                    │   │
│  └─────────────────────┬──────────────────────────────────────────┘   │
│                        │                                                │
│  ┌────────────────────┴──────────────────────────────────────────┐   │
│  │ static/js/main.js                                             │   │
│  │ - Event listener: click em "Presentear"                       │   │
│  │ - Abre modal com formulário                                   │   │
│  │ - On submit: fetch('/criar_pagamento/<id>')  ← NOVO          │   │
│  │ - Redireciona para window.location.href = init_point         │   │
│  └────────────────────┬──────────────────────────────────────────┘   │
│                       │                                                 │
│  ┌────────────────────┴──────────────────────────────────────────┐   │
│  │ static/css/style.css                                          │   │
│  │ - Estilos do modal                                            │   │
│  │ - Animações de fade-in/fade-out                              │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────┬────────────────────────────────────────────────────────────────┘
         │
         │ HTTP Request/Response
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SERVIDOR FLASK (BACKEND)                          │
│              c:\...casamento-karine-josue\app.py                       │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ app.py                                                         │   │
│  │ - Inicializa Flask app                                        │   │
│  │ - Registra blueprints:                                        │   │
│  │   - main_bp (rotas principais)                                │   │
│  │   - fotos_bp (upload de fotos)                                │   │
│  │   - admin_bp (painel admin)                                   │   │
│  │   - rsvp_bp (confirmação presença)                            │   │
│  │   - pagamentos_bp ← NOVO/ATUALIZADO                           │   │
│  └────────┬─────────────────────────────────────────────────────┘   │
│           │                                                             │
│  ┌────────┴─────────────────────────────────────────────────────┐   │
│  │ routes/pagamentos.py - REESCRITO COMPLETO (650 linhas)       │   │
│  │                                                               │   │
│  │ 📍 POST /criar_pagamento/<presente_id>                       │   │
│  │    ├─ Valida dados (nome, email, telefone)                  │   │
│  │    ├─ Busca presente no BD via db.get_connection()          │   │
│  │    ├─ Verifica se status = 'disponivel'                     │   │
│  │    ├─ Cria preferência no Mercado Pago (SDK)                │   │
│  │    ├─ Salva em BD: pagamentos_mercado_pago (status=pending) │   │
│  │    └─ Retorna JSON: init_point + preferencia_id             │   │
│  │                                                               │   │
│  │ 📍 POST /webhook/mercado_pago                                │   │
│  │    ├─ Recebe notificação do Mercado Pago                    │   │
│  │    ├─ Extrai mercado_pago_id do pagamento                   │   │
│  │    ├─ Consulta detalhes completos no MP via SDK             │   │
│  │    ├─ Se status == 'approved':                              │   │
│  │    │  ├─ Atualiza pagamentos_mercado_pago                   │   │
│  │    │  └─ Atualiza presentes: status = 'indisponivel'        │   │
│  │    ├─ Se status == 'cancelled/refunded':                    │   │
│  │    │  ├─ Atualiza pagamentos_mercado_pago                   │   │
│  │    │  └─ Atualiza presentes: status = 'disponivel'          │   │
│  │    └─ Registra log em webhook_logs para auditoria           │   │
│  │                                                               │   │
│  │ 📍 GET /api/status_pagamento/<presente_id>                  │   │
│  │    └─ Retorna status do presente (para frontend consultar)   │   │
│  │                                                               │   │
│  │ 📍 GET /sucesso_pagamento (redirecionamento MP)              │   │
│  │ 📍 GET /falha_pagamento (redirecionamento MP)                │   │
│  │ 📍 GET /pagamento_pendente (redirecionamento MP)             │   │
│  └────────┬─────────────────────────────────────────────────────┘   │
│           │                                                             │
│  ┌────────┴─────────────────────────────────────────────────────┐   │
│  │ db.py                                                        │   │
│  │ - get_connection()   → Conexão com Supabase                 │   │
│  │ - get_presentes()    → Busca presentes                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Importações (novos):                                         │   │
│  │ - import mercadopago                                         │   │
│  │ - sdk = mercadopago.SDK(ACCESS_TOKEN)                        │   │
│  │ - request, jsonify (Flask)                                   │   │
│  │ - psycopg2 (PostgreSQL driver)                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                         │
└────────┬──────────────────────┬─────────────────┬─────────────────────┘
         │                      │                 │
    HTTP │                      │                 │ Connection
    POST │                      │                 │ Pool
    GET  │                      │                 │
         │                      │                 │
         ▼                      ▼                 ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐
    │  MERCADO PAGO   │  │ SUPABASE        │  │  BANCO DE DADOS  │
    │  (API REST)     │  │ (PostgreSQL)    │  │  (PostgreSQL)    │
    │                 │  │                 │  │                  │
    │ /v1/preferences │  │ Database URL:   │  │ Tabelas:         │
    │ /v1/payments    │  │ pooler.         │  │                  │
    │ /v1/merchant... │  │ supabase.com    │  │ - presentes      │
    │                 │  │                 │  │ - users          │
    │ SDK: Python 3.0 │  │ Connection Pool │  │ - pagamentos_mp  │
    │                 │  │ (5432)          │  │ - webhook_logs   │
    │                 │  │ (5433 tx mode)  │  │ - fotos_convid.  │
    │                 │  │                 │  │ - mensagens      │
    └────────┬────────┘  └────────┬────────┘  └────────┬─────────┘
             │                    │                    │
             │ REST API           │ SQL Queries        │ ACID
             │ Webhooks           │ Transactions       │ Transactions
             │                    │                    │
             └────────────────────┴────────────────────┘
```

---

## 2️⃣ FLUXO DE PAGAMENTO (DETALHADO)

```
┌──────────────────────────────────────────────────────────────────────┐
│                      CONVIDADO CLICA "PRESENTEAR"                    │
│                                                                      │
│  Evento no Browser:                                                 │
│  .abrir-modal-presente (click event)                                │
│  └─> Modal abre com id=1, nome="Ajude com boleto", valor="30.00"   │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  CONVIDADO PREENCHE FORMULÁRIO                       │
│                                                                      │
│  Form fields:                                                       │
│  - nome_pagador: "João Silva"                                       │
│  - email_pagador: "joao@email.com"                                  │
│  - telefone_pagador: "11987654321"                                  │
│  - mensagem_pagador: "Parabéns!" (opcional)                         │
│                                                                      │
│  Clica: "Continuar para pagamento"                                  │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│              FRONTEND: FETCH (/criar_pagamento/1)                    │
│                                                                      │
│  JavaScript:                                                        │
│  fetch('/criar_pagamento/1', {                                      │
│    method: 'POST',                                                  │
│    headers: {'Content-Type': 'application/json'},                   │
│    body: JSON.stringify({                                           │
│      nome_pagador: "João Silva",                                    │
│      email_pagador: "joao@email.com",                               │
│      telefone_pagador: "11987654321",                               │
│      mensagem_pagador: "Parabéns!"                                  │
│    })                                                               │
│  })                                                                 │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
        HTTP POST │ (JSON Body)
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│        BACKEND: @pagamentos_bp.route("/criar_pagamento/1")           │
│                                                                      │
│  1. Validações:                                                     │
│     ✓ nome_pagador presente                                         │
│     ✓ email_pagador válido (contém @)                              │
│     ✓ telefone_pagador preenchido                                  │
│     └─> Se falhar, retorna 400 com erro                            │
│                                                                      │
│  2. Buscar presente no BD:                                          │
│     SELECT * FROM presentes WHERE id = 1                           │
│     └─> Retorna: {id:1, titulo:"...", valor:30.00, status:"..."}  │
│                                                                      │
│  3. Verificar disponibilidade:                                      │
│     if presente['status'] != 'disponivel':                          │
│         return error 400 "Já foi presenteado"                       │
│                                                                      │
│  4. Criar preferência no Mercado Pago:                              │
│     preference = {                                                  │
│       items: [{                                                     │
│         title: "Ajude com primeiro boleto",                         │
│         quantity: 1,                                                │
│         unit_price: 30.00                                           │
│       }],                                                           │
│       payer: {                                                      │
│         name: "João Silva",                                         │
│         email: "joao@email.com",                                    │
│         phone: {number: "11987654321"}                              │
│       },                                                            │
│       back_urls: {                                                  │
│         success: "http://localhost:5000/sucesso_pagamento",         │
│         failure: "http://localhost:5000/falha_pagamento"            │
│       },                                                            │
│       notification_url: "http://localhost:5000/webhook/mercado_pago"│
│     }                                                               │
│                                                                      │
│     response = sdk.preference().create(preference)                  │
│     ├─ Conecta ao API do Mercado Pago via HTTPS                    │
│     ├─ Envia preference como JSON                                   │
│     └─ Recebe: {id: "12345-abcd", init_point: "https://..."}       │
│                                                                      │
│  5. Salvar pagamento no BD (status=pending):                        │
│     INSERT INTO pagamentos_mercado_pago (                           │
│       presente_id, mercado_pago_id, status, valor,                 │
│       nome_pagador, email_pagador, telefone_pagador,               │
│       mensagem_pagador, preferencia_id, init_point                 │
│     ) VALUES (                                                      │
│       1, 0, 'pending', 30.00,                                       │
│       'João Silva', 'joao@email.com', '11987654321',               │
│       'Parabéns!', '12345-abcd',                                   │
│       'https://www.mercadopago.com.br/checkout/...'                │
│     ) RETURNING id                                                  │
│     └─> Retorna: pagamento_id = 42                                 │
│                                                                      │
│  6. Retornar resposta:                                              │
│     return {                                                        │
│       "sucesso": true,                                              │
│       "init_point": "https://www.mercadopago.com.br/checkout/...", │
│       "preferencia_id": "12345-abcd",                               │
│       "pagamento_id": 42                                            │
│     }                                                               │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
        HTTP 200 │ (JSON Response)
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│           FRONTEND: REDIRECIONA PARA MERCADO PAGO                    │
│                                                                      │
│  JavaScript:                                                        │
│  window.location.href = data.init_point                             │
│                                                                      │
│  Navegador:                                                         │
│  GET https://www.mercadopago.com.br/checkout/...                   │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│           MERCADO PAGO: EXIBE CHECKOUT                               │
│                                                                      │
│  Opções:                                                            │
│  ┌─────────────────────────────────────────┐                        │
│  │ R$ 30,00 - Ajude com primeiro boleto    │                        │
│  │                                         │                        │
│  │ Forma de Pagamento:                    │                        │
│  │ [✓] PIX                                │                        │
│  │ [ ] Cartão de Crédito                  │                        │
│  │ [ ] Cartão de Débito                   │                        │
│  │                                         │                        │
│  │ [Pagar com PIX] [Pagar com Cartão]     │                        │
│  └─────────────────────────────────────────┘                        │
│                                                                      │
│  Convidado escolhe uma opção e clica em "Pagar"                     │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
     ┌───────────┴───────────┐
     │                       │
     ▼                       ▼
  ┌─────────┐          ┌──────────┐
  │   PIX   │          │ CARTÃO   │
  │  QR CODE│          │ 4111...  │
  │ Escaneia│          │ Exp 12/25│
  │ Banco   │          │ CVV 123  │
  │         │          │          │
  └────┬────┘          └─────┬────┘
       │                     │
       ▼                     ▼
┌─────────────────────────────────────┐
│ Mercado Pago Processa Pagamento     │
├─────────────────────────────────────┤
│ - Conecta com banco/instituição     │
│ - Valida dados                      │
│ - Processa transação                │
│ - Retorna resultado                 │
│   └─> approved / cancelled / pending│
└────────────┬────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────────────────────────────┐
│      MERCADO PAGO ENVIA WEBHOOK (POST /webhook/mercado_pago)         │
│                                                                      │
│  Request:                                                           │
│  POST /webhook/mercado_pago HTTP/1.1                                │
│  Content-Type: application/x-www-form-urlencoded                    │
│  Host: localhost:5000                                               │
│                                                                      │
│  type=payment&id=1234567890&topic=payment                           │
│                                                                      │
│  (Mercado Pago envia notificação cada vez que o status muda)        │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│         BACKEND: @pagamentos_bp.route("/webhook/mercado_pago")       │
│                                                                      │
│  1. Extrair ID:                                                     │
│     mercado_pago_id = 1234567890                                    │
│     tipo_notificacao = "payment"                                    │
│                                                                      │
│  2. Consultar detalhes no Mercado Pago:                             │
│     payment = sdk.payment().get(1234567890)                         │
│     ├─ HTTPS para API do Mercado Pago                              │
│     └─ Retorna detalhes completos do pagamento                      │
│                                                                      │
│  3. Extrair informações:                                            │
│     status = payment['status']  # "approved" ou outro               │
│     preferencia_id = payment['preference_id']  # "12345-abcd"       │
│     metodo = payment['payment_method']['type']  # "credit_card"     │
│                                                                      │
│  4. Atualizar banco de dados:                                       │
│     UPDATE pagamentos_mercado_pago                                  │
│     SET status = 'approved',  # "approved", "cancelled", etc        │
│         mercado_pago_id = 1234567890,                               │
│         metodo_pagamento = 'credit_card'                            │
│     WHERE preferencia_id = '12345-abcd'                             │
│     RETURNING presente_id  # Retorna 1                              │
│                                                                      │
│  5. Se status == 'approved':                                        │
│     UPDATE presentes                                                │
│     SET status = 'indisponivel'                                     │
│     WHERE id = 1                                                    │
│                                                                      │
│     (Presente #1 agora está marcado como indisponível!)             │
│                                                                      │
│  6. Registrar log para auditoria:                                   │
│     INSERT INTO webhook_logs (                                      │
│       mercado_pago_id, tipo_notificacao, status,                    │
│       dados_json, processado, erro                                  │
│     ) VALUES (                                                      │
│       1234567890, 'payment', 'processado',                          │
│       '{...full json...}', true, null                               │
│     )                                                               │
│                                                                      │
│  7. Retornar 200 OK ao Mercado Pago:                                │
│     return {"recebido": true}, 200                                  │
│                                                                      │
│     (Importante: sempre retornar 200, mesmo em erro)                │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│          BANCO DE DADOS ATUALIZADO                                   │
│                                                                      │
│  Tabela: pagamentos_mercado_pago                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ id  │ presente_id │ mercado_pago_id │ status   │ valor      │   │
│  ├─────┼─────────────┼─────────────────┼──────────┼────────────┤   │
│  │ 42  │ 1           │ 1234567890      │ approved │ 30.00      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Tabela: presentes                                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ id  │ titulo                    │ valor │ status         │   │
│  ├─────┼───────────────────────────┼───────┼────────────────┤   │
│  │ 1   │ Ajude com primeiro boleto │ 30.00 │ indisponivel ✓ │   │
│  │ 2   │ Patrocine ansiolítico     │ 20.00 │ disponivel     │   │
│  │ 3   │ Assuma um boleto          │ 50.00 │ disponivel     │   │
│  │ 4   │ Compras de mercado        │ 100.00│ disponivel     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Tabela: webhook_logs                                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ id │ mercado_pago_id │ status      │ processado │ erro      │   │
│  ├────┼─────────────────┼─────────────┼────────────┼───────────┤   │
│  │ 1  │ 1234567890      │ processado  │ true       │ null      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└────────────────┬─────────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│          FRONTEND DETECTA MUDANÇA (3 opções)                         │
│                                                                      │
│  Opção A: Redirecionamento automático                               │
│  └─> MP redireciona para /sucesso_pagamento                         │
│      └─> Após 3s, volta para homepage com lista atualizada          │
│                                                                      │
│  Opção B: Polling (opcional)                                        │
│  └─> JavaScript faz GET /api/status_pagamento/1 a cada 10s          │
│      └─> Se mudou para 'indisponivel', refrescar lista              │
│                                                                      │
│  Opção C: WebSocket (futuro)                                        │
│  └─> Conexão persistente para atualizações em tempo real            │
│                                                                      │
│  Resultado visível:                                                 │
│                                                                      │
│  ANTES:                             DEPOIS:                         │
│  ┌──────────────────────────┐       ┌──────────────────────────┐   │
│  │ 💝 Primeiro boleto       │       │ 💝 Primeiro boleto       │   │
│  │ R$ 30,00                 │       │ R$ 30,00                 │   │
│  │ [Presentear]             │       │ [Indisponível]           │   │
│  │                          │       │ 🎉 Presenteado!          │   │
│  └──────────────────────────┘       └──────────────────────────┘   │
│                                                                      │
│  ✓ Fluxo completo!                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3️⃣ ESTRUTURA DE PASTAS

```
casamento-karine-josue/
│
├── 📄 app.py                              ← Flask app principal
├── 📄 db.py                               ← Conexão com banco
├── 📄 requirements.txt                    ← Dependências (Python)
│
├── 📁 routes/
│   ├── 📄 main.py                         ← Rotas principais
│   ├── 📄 admin.py                        ← Admin panel
│   ├── 📄 rsvp.py                         ← RSVP/Confirmação
│   ├── 📄 fotos.py                        ← Upload de fotos
│   ├── 📄 mensagens.py                    ← Mensagens
│   └── 📄 pagamentos.py                   ← 🆕 NOVO: Mercado Pago ⭐
│
├── 📁 migrations/
│   └── 📄 add_mercado_pago_tables.sql     ← 🆕 SQL migrations
│
├── 📁 templates/
│   ├── 📄 base.html                       ← Base template
│   ├── 📄 index.html                      ← Home (com modal presentes)
│   ├── 📄 admin_*.html                    ← Admin pages
│   └── 📁 partials/
│       ├── presentes.html                 ← Lista de presentes
│       ├── hero.html
│       ├── historia.html
│       ├── galeria.html
│       └── ...
│
├── 📁 static/
│   ├── 📁 css/
│   │   └── style.css
│   │
│   ├── 📁 js/
│   │   └── main.js                        ← 🔄 MODIFICADO: novo fetch
│   │
│   ├── 📁 img/
│   │   └── presentes/
│   │
│   └── 📁 uploads/
│       └── convidados/                    ← Fotos dos convidados
│
├── 📄 test_mercado_pago_setup.py          ← 🆕 Script validação
├── 📄 test_api.sh                         ← 🆕 Exemplos cURL
├── 📄 .env.example                        ← 🆕 Template .env
│
├── 📄 SETUP_DATABASE.sql                  ← SQL inicial (já usado)
├── 📄 Procfile                            ← Deploy Render/Heroku
│
└── 📄 DOCUMENTAÇÃO NOVA:
    ├── README_MERCADO_PAGO.md             ← 🆕 Readme principal
    ├── QUICK_START.md                     ← 🆕 Guia 5 min
    ├── MERCADO_PAGO_INTEGRATION.md        ← 🆕 Documentação completa
    ├── RESUMO_IMPLEMENTACAO.md            ← 🆕 Resumo técnico
    ├── EXEMPLO_FLUXO_COMPLETO.py          ← 🆕 Exemplos passo-a-passo
    └── ARQUITETURA.md                     ← 🆕 Este arquivo
```

---

## 4️⃣ STACK TECNOLÓGICO

```
┌────────────────────────────────────────────────────────────────┐
│                   FRONTEND (Cliente)                           │
├────────────────────────────────────────────────────────────────┤
│ • HTML5 - Markup                                               │
│ • CSS3 - Estilos + Animações                                   │
│ • JavaScript (Vanilla) - Interatividade                        │
│   └─ Não usa jQuery, React, Vue (mantém simples)              │
│ • Jinja2 Templates (via Flask)                                 │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                    BACKEND (Servidor)                          │
├────────────────────────────────────────────────────────────────┤
│ • Python 3.x                                                   │
│ • Flask 3.1.0 - Web framework                                  │
│ • psycopg2-binary - PostgreSQL driver                          │
│ • python-dotenv - Variáveis de ambiente                        │
│ • mercado-pago 3.0.0 - SDK Mercado Pago ⭐ NOVO              │
│ • requests - HTTP library (dependência MP)                     │
│ • gunicorn - Production WSGI server                            │
│ • Werkzeug - WSGI utilities                                    │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                   BANCO DE DADOS                               │
├────────────────────────────────────────────────────────────────┤
│ • PostgreSQL 12+ (via Supabase)                                │
│ • psycopg2 (driver Python)                                     │
│ • Connection Pooling (Supabase pooler)                         │
│ • ACID Transactions                                            │
│ • Índices para otimização                                      │
│ • Triggers para updated_at automaticamente                     │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                TERCEIROS / INTEGRAÇÕES                         │
├────────────────────────────────────────────────────────────────┤
│ • Mercado Pago (Checkout Pro)                                  │
│   └─ API REST v1                                               │
│   └─ Webhooks para notificações                                │
│   └─ Múltiplas formas de pagamento (PIX, Cartão)              │
│                                                                │
│ • Supabase (Backend as a Service)                              │
│   └─ PostgreSQL gerenciado                                     │
│   └─ Connection pooler                                         │
│   └─ Auth (para futuro)                                        │
│                                                                │
│ • Render / Heroku (Deploy)                                     │
│   └─ Git integration                                           │
│   └─ Environment variables                                     │
│   └─ SSL/HTTPS automático                                      │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│               DESENVOLVIMENTO / TESTES                         │
├────────────────────────────────────────────────────────────────┤
│ • Python unittest (testes de validação)                        │
│ • cURL / Postman (testes API)                                  │
│ • ngrok (tunneling para webhook local)                         │
│ • Git / GitHub (controle de versão)                            │
│ • VS Code (editor)                                             │
└────────────────────────────────────────────────────────────────┘
```

---

## 5️⃣ SEGURANÇA - FLUXO

```
┌─────────────────────────────────────────────────────────────┐
│              VALIDAÇÃO DE ENTRADA (Frontend)                 │
│                                                             │
│ 1. Email tem @?                                            │
│ 2. Nome não vazio?                                         │
│ 3. Telefone preenchido?                                    │
│ 4. Mensagem < 500 chars?                                  │
│                                                             │
│ └─> Se falhar: Não envia request, mostra erro local       │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│           VALIDAÇÃO DE ENTRADA (Backend)                    │
│                                                             │
│ 1. Dados JSON válido?                                      │
│ 2. Email é válido?                                         │
│ 3. Nome não vazio?                                         │
│ 4. Telefone presente?                                      │
│                                                             │
│ └─> Se falhar: Retorna 400 com descrição de erro          │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          VERIFICAÇÃO DE NEGÓCIO                             │
│                                                             │
│ 1. Presente existe?                                         │
│ 2. Presente ainda está disponível?                          │
│    └─ SELECT status FROM presentes WHERE id=?              │
│    └─ if status != 'disponivel': ERRO                      │
│                                                             │
│ └─> Evita venda dupla / presente fantasma                 │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          INTEGRAÇÃO COM MERCADO PAGO (Segura)              │
│                                                             │
│ 1. Conecta via HTTPS apenas                                │
│ 2. Usa SDK oficial (não faz requisições brutas)           │
│ 3. Envia ACCESS_TOKEN de forma segura                      │
│ 4. Valida resposta antes de usar                           │
│ 5. Não expõe dados sensíveis em logs                       │
│                                                             │
│ └─> PCI-DSS compliance via Mercado Pago                   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              TRANSAÇÕES ATÔMICAS NO BANCO                    │
│                                                             │
│ 1. INSERT pagamentos_mercado_pago                           │
│ 2. COMMIT (sucesso) ou ROLLBACK (erro)                     │
│ └─> Garante consistência: ou tudo entra ou nada           │
│                                                             │
│ 3. UPDATE presentes com webhook                            │
│    └─ Usa UNIQUE constraint para evitar duplicatas         │
│    └─ Índice garante apenas 1 pagamento/presente          │
│                                                             │
│ └─> ACID transactions = zero chance de inconsistência     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│            WEBHOOK LOGGING / AUDITORIA                       │
│                                                             │
│ 1. TODOS os webhooks registrados em webhook_logs           │
│ 2. Dados completos em JSON para análise                    │
│ 3. Erros capturados com stacktrace                         │
│ 4. Timestamp automático para rastreabilidade               │
│                                                             │
│ └─> Qualquer anomalia pode ser investigada                │
└─────────────────────────────────────────────────────────────┘
```

---

**FIM DO DIAGRAMA**

Todos os códigos mencionados estão na pasta do projeto. Consulte os arquivos específicos para mais detalhes!
