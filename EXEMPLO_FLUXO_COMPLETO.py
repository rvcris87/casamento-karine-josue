"""
Exemplo de fluxo completo - TESTE MANUAL

Como testar a integração Mercado Pago:
1. Configurar .env com credenciais
2. Executar migrations SQL
3. Rodar aplicação Flask
4. Seguir este fluxo

Todas as credenciais usadas aqui são de TESTE (Mercado Pago fornece)
"""

# ==============================================================================
# PASSO 1: CONVIDADO ACESSA O SITE
# ==============================================================================
"""
Visitante acessa: http://localhost:5000

Navegação:
- Home
- Sobre o casal
- Galeria de fotos
- [Lista de Presentes] ← Clica aqui
"""

# ==============================================================================
# PASSO 2: VÊ LISTA DE PRESENTES E CLICA "PRESENTEAR"
# ==============================================================================
"""
Vê 4 presentes com botões "Presentear":

┌────────────────────────────────────┐
│ 💝 Ajude com o primeiro boleto      │
│ R$ 30,00                           │
│ [Presentear]  ← Clica aqui        │
└────────────────────────────────────┘

Evento no navegador:
- Click trigger: querySelector(".abrir-modal-presente")
- Modal abre com formulário
"""

# ==============================================================================
# PASSO 3: MODAL ABRE - PREENCHE DADOS
# ==============================================================================
"""
Modal que aparece:

┌─────────────────────────────────────┐
│  [X] Lista de Presentes             │
│                                     │
│  💝 Ajude com o primeiro boleto      │
│  R$ 30,00                           │
│                                     │
│  Seu nome: [João Silva]             │
│  Seu e-mail: [joao@email.com]       │
│  Seu telefone: [11987654321]        │
│  Mensagem: [Parabéns aos noivos!] │
│                                     │
│  [Continuar para o pagamento]      │
└─────────────────────────────────────┘

Dados preenchidos:
- Nome: João Silva
- Email: joao@email.com
- Telefone: 11987654321
- Mensagem: Parabéns! (opcional)
"""

# ==============================================================================
# PASSO 4: CLICA "CONTINUAR" - FRONTEND FAZ FETCH
# ==============================================================================
"""
Event listener dispara:
formPresentear.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Coletar dados
    const presenteId = 1;
    const dados = {
        nome_pagador: "João Silva",
        email_pagador: "joao@email.com",
        telefone_pagador: "11987654321",
        mensagem_pagador: "Parabéns!"
    };
    
    // Fazer requisição
    const response = await fetch(`/criar_pagamento/1`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(dados)
    });
    
    const data = await response.json();
    
    // Redirecionar
    if (data.sucesso) {
        window.location.href = data.init_point;
    }
});

Timeline:
00:00 - Usuario clica botão
00:01 - Modal fecha
00:02 - Botão fica "Processando..."
00:50 - Backend responde com init_point
00:51 - Pagina redireciona para Mercado Pago
"""

# ==============================================================================
# PASSO 5: BACKEND PROCESSA
# ==============================================================================
"""
@pagamentos_bp.route("/criar_pagamento/<int:presente_id>", methods=["POST"])
def criar_pagamento(presente_id):
    
    # 1. Validar dados
    dados = request.get_json()
    nome_pagador = "João Silva"
    email_pagador = "joao@email.com"
    telefone_pagador = "11987654321"
    mensagem_pagador = "Parabéns!"
    
    # 2. Buscar presente no BD
    presente = get_presente_by_id(1)
    # Retorna: {
    #     'id': 1,
    #     'titulo': 'Ajude com o primeiro boleto',
    #     'valor_sugerido': 30.00,
    #     'status': 'disponivel'
    # }
    
    # 3. Verificar se está disponível
    if presente['status'] == 'indisponivel':
        return {"sucesso": False, "erro": "Já foi presenteado"}, 400
    
    # 4. Criar preferência no Mercado Pago
    preference = {
        "items": [{
            "title": "Ajude com o primeiro boleto",
            "quantity": 1,
            "unit_price": 30.00
        }],
        "payer": {
            "name": "João Silva",
            "email": "joao@email.com",
            "phone": {"number": "11987654321"}
        },
        "back_urls": {
            "success": "http://localhost:5000/sucesso_pagamento",
            "failure": "http://localhost:5000/falha_pagamento"
        },
        "notification_url": "http://localhost:5000/webhook/mercado_pago",
        "external_reference": "presente_1_joao@email.com"
    }
    
    response = sdk.preference().create(preference)
    # Retorna: {
    #     'id': '12345678-abcd-1234-abcd',
    #     'init_point': 'https://www.mercadopago.com.br/checkout/v1/refresh?pref_id=12345678-abcd'
    # }
    
    # 5. Salvar no banco (status = pending)
    INSERT INTO pagamentos_mercado_pago (
        presente_id, mercado_pago_id, status, valor,
        nome_pagador, email_pagador, telefone_pagador,
        mensagem_pagador, preferencia_id, init_point
    ) VALUES (
        1, 0, 'pending', 30.00,
        'João Silva', 'joao@email.com', '11987654321',
        'Parabéns!', '12345678-abcd-1234-abcd',
        'https://www.mercadopago.com.br/checkout/...'
    )
    # Retorna: pagamento_id = 42
    
    # 6. Retornar resposta
    return {
        "sucesso": True,
        "init_point": "https://www.mercadopago.com.br/checkout/v1/refresh?pref_id=12345678-abcd",
        "preferencia_id": "12345678-abcd-1234-abcd",
        "pagamento_id": 42
    }
"""

# ==============================================================================
# PASSO 6: FRONTEND REDIRECIONA PARA MERCADO PAGO
# ==============================================================================
"""
window.location.href = data.init_point
// Redireciona para: https://www.mercadopago.com.br/checkout/v1/...

Usuário vê página de checkout do Mercado Pago com opções:
┌─────────────────────────────────────────────┐
│ Mercado Pago Checkout                       │
├─────────────────────────────────────────────┤
│                                             │
│ R$ 30,00 - Ajude com o primeiro boleto     │
│                                             │
│ Forma de Pagamento:                        │
│ [✓] PIX                                    │
│ [ ] Cartão de Crédito                      │
│ [ ] Cartão de Débito                       │
│                                             │
│ [Pagar com PIX] ou [Pagar com Cartão]      │
└─────────────────────────────────────────────┘
"""

# ==============================================================================
# PASSO 7: USUÁRIO FAZ PAGAMENTO
# ==============================================================================
"""
Opção 1: PIX
- QR Code gerado
- Usuário escaneia com banco
- Transferência PIX
- Confirmação imediata

Opção 2: Cartão
- Número: 4111 1111 1111 1111 (teste)
- Vencimento: 12/25
- CVV: 123
- Clica "Pagar"
- Processamento...
- Aprovado! ✓

Mercado Pago retorna:
{
    "id": 1234567890,
    "status": "approved",
    "preference_id": "12345678-abcd",
    "payment_method": {"type": "credit_card"},
    "transaction_amount": 30.00
}
"""

# ==============================================================================
# PASSO 8: MERCADO PAGO ENVIA WEBHOOK
# ==============================================================================
"""
POST /webhook/mercado_pago
Content-Type: application/x-www-form-urlencoded

type=payment
id=1234567890
topic=payment

Nosso servidor recebe e processa:

@pagamentos_bp.route("/webhook/mercado_pago", methods=["POST"])
def webhook_mercado_pago():
    
    # 1. Extrair ID
    mercado_pago_id = 1234567890
    
    # 2. Consultar detalhes em Mercado Pago
    payment_response = sdk.payment().get(1234567890)
    payment = payment_response['response']
    # {
    #     'id': 1234567890,
    #     'status': 'approved',
    #     'preference_id': '12345678-abcd',
    #     'payment_method': {'type': 'credit_card'}
    # }
    
    # 3. Se aprovado, atualizar BD
    if payment['status'] == 'approved':
        
        # Atualizar pagamento_mercado_pago
        UPDATE pagamentos_mercado_pago
        SET status = 'approved',
            mercado_pago_id = 1234567890,
            metodo_pagamento = 'credit_card'
        WHERE preferencia_id = '12345678-abcd'
        # Retorna: presente_id = 1
        
        # Atualizar presente
        UPDATE presentes
        SET status = 'indisponivel'
        WHERE id = 1
        
    # 4. Registrar log
    INSERT INTO webhook_logs (
        mercado_pago_id, tipo_notificacao, status,
        dados_json, processado
    ) VALUES (
        1234567890, 'payment', 'processado',
        '{...}', true
    )
    
    # 5. Retornar 200 OK
    return {"recebido": True}, 200
"""

# ==============================================================================
# PASSO 9: BANCO DE DADOS ATUALIZADO
# ==============================================================================
"""
Tabela: pagamentos_mercado_pago

id | presente_id | mercado_pago_id | status   | valor | email             | preferencia_id      | init_point
42 | 1           | 1234567890      | approved | 30.00 | joao@email.com   | 12345678-abcd-1234 | https://www...

Tabela: presentes

id | titulo                           | status
1  | Ajude com o primeiro boleto      | indisponivel  ← MUDOU!
2  | Patrocine nosso ansiolítico      | disponivel
3  | Assuma um boleto do casal        | disponivel
4  | Ajude na primeira compra         | disponivel

Tabela: webhook_logs

id | mercado_pago_id | tipo_notificacao | status      | processado
1  | 1234567890      | payment          | processado  | true
"""

# ==============================================================================
# PASSO 10: FRONTEND REFLETE MUDANÇA
# ==============================================================================
"""
Option A: Página recarrega automaticamente
- Usuário é redirecionado para /sucesso_pagamento
- Após 3 segundos, volta para página de presentes
- Presente #1 agora mostra: [Indisponível] (botão desabilitado)

Option B: WebSocket em tempo real
- Conexão WebSocket mantém lista atualizada
- Presente desaparece em tempo real

Option C: Polling
- JavaScript faz fetch a cada 10 segundos
- Se status mudou, recarrega

Resultado visual:

ANTES:
┌────────────────────────────┐
│ 💝 Primeiro boleto         │
│ R$ 30,00                   │
│ [Presentear]               │
└────────────────────────────┘

DEPOIS:
┌────────────────────────────┐
│ 💝 Primeiro boleto         │
│ R$ 30,00                   │
│ [Indisponível] (disabled)  │
│ 🎉 Presenteado por João    │
└────────────────────────────┘
"""

# ==============================================================================
# FLUXO DE ERRO - EXEMPLO
# ==============================================================================
"""
Se algo der errado:

CENÁRIO: Presente já foi presenteado

1. Convidado clica "Presentear" no presente #1
2. Backend busca presente: status = 'indisponivel'
3. Retorna erro:
   {
       "sucesso": false,
       "erro": "Este presente já foi presenteado"
   }
4. Frontend mostra alert: "Este presente já foi presenteado"
5. Modal se fecha
6. Lista continua como está

Log registrado em webhook_logs:
- status: erro_presente_indisponivel
- erro: "Este presente já estava presenteado"
"""

# ==============================================================================
# MONITORAMENTO EM TEMPO REAL
# ==============================================================================
"""
Para acompanhar o fluxo em produção:

# Ver pagamentos
SELECT * FROM pagamentos_mercado_pago 
ORDER BY created_at DESC LIMIT 10;

# Ver webhooks recebidos
SELECT * FROM webhook_logs 
ORDER BY created_at DESC LIMIT 10;

# Ver presentes indisponíveis
SELECT * FROM presentes 
WHERE status = 'indisponivel';

# Ver erro específico
SELECT * FROM webhook_logs 
WHERE erro IS NOT NULL 
ORDER BY created_at DESC;

# Estatísticas
SELECT 
    status, 
    COUNT(*) as total,
    SUM(valor) as valor_total
FROM pagamentos_mercado_pago
GROUP BY status;
"""

# ==============================================================================
# TESTES COM CURL
# ==============================================================================
"""
# Teste 1: Criar pagamento
curl -X POST "http://localhost:5000/criar_pagamento/1" \\
  -H "Content-Type: application/json" \\
  -d '{
    "nome_pagador": "Maria Silva",
    "email_pagador": "maria@email.com",
    "telefone_pagador": "11987654321"
  }'

# Resposta esperada:
{
    "sucesso": true,
    "init_point": "https://www.mercadopago.com.br/checkout/...",
    "preferencia_id": "12345678-abcd",
    "pagamento_id": 43
}

# Teste 2: Verificar status
curl -X GET "http://localhost:5000/api/status_pagamento/1"

# Resposta esperada:
{
    "presente_id": 1,
    "status": "indisponivel"  # Se foi presenteado
}
"""

# ==============================================================================
# RESUMO DO FLUXO
# ==============================================================================
"""
1. Usuário clica "Presentear"
   └─ Modal abre com formulário

2. Preenche nome, email, telefone, mensagem
   └─ Clica "Continuar para pagamento"

3. Frontend faz fetch para /criar_pagamento/1
   └─ Envia dados do formulário

4. Backend:
   ├─ Valida dados
   ├─ Busca presente no BD
   ├─ Verifica se está disponível
   ├─ Cria preferência no Mercado Pago
   ├─ Salva pagamento no BD (status=pending)
   └─ Retorna init_point

5. Frontend redireciona para init_point
   └─ Mercado Pago checkout abre

6. Usuário faz pagamento (PIX/Cartão)
   └─ Mercado Pago processa

7. Mercado Pago envia webhook
   └─ POST /webhook/mercado_pago

8. Backend processa webhook:
   ├─ Consulta detalhes do pagamento no MP
   ├─ Se aprovado:
   │  ├─ Atualiza pagamentos_mercado_pago
   │  └─ Atualiza presente status='indisponivel'
   └─ Registra log em webhook_logs

9. Frontend detecta mudança
   └─ Presente desaparece da lista

10. Convidado vê "Obrigado!" ou "Presente já foi presenteado"
    └─ Fluxo completo ✓
"""
