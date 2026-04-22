#!/bin/bash

# 🎁 Exemplos de Requisições cURL
# Para testar a integração Mercado Pago
# 
# Uso: bash test_api.sh

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# URL base (altere para https://seu-dominio.com em produção)
BASE_URL="http://localhost:5000"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  🎁 TESTE DE API - INTEGRAÇÃO MERCADO PAGO${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# ============================================================================
# TEST 1: Criar Pagamento (simulando clique em "Presentear")
# ============================================================================
echo -e "\n${YELLOW}TEST 1: Criar Pagamento${NC}"
echo -e "${BLUE}POST /criar_pagamento/1${NC}"
echo -e "Simulando: convidado clicou em 'Presentear' de um presente\n"

curl -X POST "$BASE_URL/criar_pagamento/1" \
  -H "Content-Type: application/json" \
  -d '{
    "nome_pagador": "João Silva",
    "email_pagador": "joao@example.com",
    "telefone_pagador": "11987654321",
    "mensagem_pagador": "Parabéns aos noivos! 💙"
  }' \
  -w "\n\n📊 Status HTTP: %{http_code}\n"

# ============================================================================
# TEST 2: Verificar Status de um Presente
# ============================================================================
echo -e "\n${YELLOW}TEST 2: Verificar Status de Presente${NC}"
echo -e "${BLUE}GET /api/status_pagamento/1${NC}"
echo -e "Verificando se presente 1 foi presenteado\n"

curl -X GET "$BASE_URL/api/status_pagamento/1" \
  -H "Content-Type: application/json" \
  -w "\n\n📊 Status HTTP: %{http_code}\n"

# ============================================================================
# TEST 3: Listar Todos os Presentes
# ============================================================================
echo -e "\n${YELLOW}TEST 3: Listar Presentes${NC}"
echo -e "${BLUE}GET /presentes (via página principal)${NC}"
echo -e "Este endpoint não existe, mas presentes são carregados na página principal\n"

# ============================================================================
# TEST 4: Simular Webhook (Mercado Pago envia notificação)
# ============================================================================
echo -e "\n${YELLOW}TEST 4: Simular Webhook (Opcional)${NC}"
echo -e "${BLUE}POST /webhook/mercado_pago${NC}"
echo -e "AVISO: Este é um exemplo. Não execute sem IDs reais!\n"

echo -e "${RED}# Para testar webhook com dados reais:${NC}"
echo -e "${RED}# 1. Use ngrok: ngrok http 5000${NC}"
echo -e "${RED}# 2. Configure webhook no Mercado Pago${NC}"
echo -e "${RED}# 3. Faça um pagamento de teste${NC}"
echo -e "${RED}# 4. Mercado Pago enviará notificação automaticamente${NC}\n"

# ============================================================================
# EXEMPLOS ADICIONAIS
# ============================================================================
echo -e "\n${YELLOW}EXEMPLOS ADICIONAIS:${NC}\n"

echo -e "${BLUE}1. Teste com dados inválidos (falta email):${NC}"
curl -X POST "$BASE_URL/criar_pagamento/1" \
  -H "Content-Type: application/json" \
  -d '{
    "nome_pagador": "Maria Silva",
    "email_pagador": "",
    "telefone_pagador": "11987654321"
  }' \
  -w "\n\n"

echo -e "\n${BLUE}2. Teste com presente inexistente (ID 999999):${NC}"
curl -X POST "$BASE_URL/criar_pagamento/999999" \
  -H "Content-Type: application/json" \
  -d '{
    "nome_pagador": "Pedro Santos",
    "email_pagador": "pedro@example.com",
    "telefone_pagador": "11987654321"
  }' \
  -w "\n\n"

# ============================================================================
# DICAS DE USO
# ============================================================================
echo -e "\n${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}DICAS:${NC}"
echo -e "${GREEN}1. Para testar em produção, altere BASE_URL${NC}"
echo -e "${GREEN}2. Verifique os logs: tail -f application.log${NC}"
echo -e "${GREEN}3. Consulte banco de dados:${NC}"
echo -e "${GREEN}   SELECT * FROM pagamentos_mercado_pago ORDER BY created_at DESC;${NC}"
echo -e "${GREEN}4. Monitorar webhooks:${NC}"
echo -e "${GREEN}   SELECT * FROM webhook_logs ORDER BY created_at DESC;${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}\n"

# ============================================================================
# CARTÕES DE TESTE
# ============================================================================
echo -e "${YELLOW}CARTÕES DE TESTE (Modo Teste Mercado Pago):${NC}\n"

echo -e "${BLUE}Cartão com PIX:${NC}"
echo "  Número: 4111 1111 1111 1111"
echo "  Vencimento: 12/25"
echo "  CVV: 123"
echo "  Resultado: Será redirecionado para escolher PIX ou Cartão\n"

echo -e "${BLUE}Cartão Débito (Sucesso):${NC}"
echo "  Número: 5555 5555 5555 4444"
echo "  Vencimento: 12/25"
echo "  CVV: 123"
echo "  Resultado: Pagamento Aprovado ✓\n"

echo -e "${BLUE}Cartão Crédito (Pendente):${NC}"
echo "  Número: 4111 1111 1111 1113"
echo "  Vencimento: 12/25"
echo "  CVV: 123"
echo "  Resultado: Pagamento Pendente (aguardando processamento)\n"

echo -e "${BLUE}Cartão (Rejeitado):${NC}"
echo "  Número: 4111 1111 1111 1114"
echo "  Vencimento: 12/25"
echo "  CVV: 123"
echo "  Resultado: Pagamento Recusado ✗\n"

# ============================================================================
echo -e "${GREEN}✓ Script de teste concluído!${NC}\n"
