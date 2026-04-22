# 🚀 Setup Rápido - Mercado Pago no Sistema de Casamento

## ⚡ Passos Rápidos (5 minutos)

### 1. Atualizar dependências
```bash
pip install -r requirements.txt
```

### 2. Executar migração SQL
1. Abra: `migrations/add_mercado_pago_tables.sql`
2. Cole no SQL Editor do Supabase
3. Execute

### 3. Configurar `.env`
```bash
cp .env.example .env
```

Edite `.env` com:
```
MERCADO_PAGO_ACCESS_TOKEN=APP_USR-7108049560326594-042212-ee879f6a87885115519a5fed61ab8c04-3352130635
MERCADO_PAGO_PUBLIC_KEY=APP_USR-583c2032-5036-4f0f-a2f8-c6cef74d0347
BASE_URL=http://localhost:5000
```

### 4. Testar configuração
```bash
python test_mercado_pago_setup.py
```

### 5. Iniciar aplicação
```bash
python app.py
```

---

## 🎯 Como Usar

1. Abra http://localhost:5000
2. Navegue até "Lista de Presentes"
3. Clique "Presentear"
4. Preencha dados (nome, email, telefone)
5. Clique "Continuar para o pagamento"
6. Redireciona para Mercado Pago
7. Escolha PIX ou Cartão
8. **Cartão de teste:** `4111 1111 1111 1111` (exp: 12/25, CVV: 123)
9. Após pagamento, presente fica "Indisponível"

---

## 📁 Arquivos Novos/Modificados

### ✅ Criados:
- `migrations/add_mercado_pago_tables.sql` - Migrations do banco
- `routes/pagamentos.py` - **REESCRITO COMPLETO** com Mercado Pago
- `test_mercado_pago_setup.py` - Script de validação
- `.env.example` - Template de variáveis
- `MERCADO_PAGO_INTEGRATION.md` - Documentação completa
- `QUICK_START.md` - Este arquivo

### 🔄 Modificados:
- `requirements.txt` - +2 dependências (mercado-pago, requests)
- `static/js/main.js` - Atualizado para chamar nova rota (linhas ~228-282)

---

## 🔑 Credenciais de Teste

Use essas credenciais para testes. **EM PRODUÇÃO, use suas próprias!**

```
ACCESS_TOKEN: APP_USR-7108049560326594-042212-ee879f6a87885115519a5fed61ab8c04-3352130635
PUBLIC_KEY: APP_USR-583c2032-5036-4f0f-a2f8-c6cef74d0347
```

---

## 📊 Novo Schema do Banco

Duas tabelas adicionadas:

**pagamentos_mercado_pago**
- Registra cada tentativa de pagamento
- Vincula presente_id com mercado_pago_id
- Rastreia status: pending → approved/cancelled/refunded

**webhook_logs**
- Auditoria completa de notificações
- Ajuda a debugar problemas
- Consulte com: `SELECT * FROM webhook_logs ORDER BY created_at DESC;`

---

## 🧪 Testes

### Teste Local
```bash
# Validar setup
python test_mercado_pago_setup.py

# Deve retornar: 6/6 testes passaram ✓
```

### Teste Manual
1. Acesse http://localhost:5000/presentes
2. Clique "Presentear" em um presente
3. Preencha nome, email, telefone
4. Clique "Continuar para pagamento"
5. Use cartão: **4111 1111 1111 1111**
6. Verifique se presente ficou "indisponível"

### Monitorar Webhook
```sql
-- Ver últimos webhooks
SELECT * FROM webhook_logs ORDER BY created_at DESC LIMIT 10;

-- Ver pagamentos aprovados
SELECT * FROM pagamentos_mercado_pago WHERE status = 'approved';

-- Ver presentes indisponíveis
SELECT * FROM presentes WHERE status = 'indisponivel';
```

---

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| "Presente não encontrado" | Verifique `SETUP_DATABASE.sql` foi executado |
| Erro ao criar pagamento | Verifique credenciais no `.env` |
| Webhook não chega | Use ngrok para testar localmente: `ngrok http 5000` |
| Presente não fica indisponível | Verifique `webhook_logs` para erros |

---

## 📚 Documentação Completa

Para detalhes aprofundados, consulte: `MERCADO_PAGO_INTEGRATION.md`

Inclui:
- Fluxo completo de pagamento
- Configuração detalhada
- Schema de banco de dados
- Todos os endpoints de API
- Integração com webhook
- Troubleshooting avançado
- Checklist de produção

---

## 🔐 Produção

Quando estiver pronto para produção:

1. **Obtenha credenciais reais:**
   - https://www.mercadopago.com.br/developers
   - Vá para "Produção" em vez de "Teste"

2. **Atualize `.env`:**
   ```
   MERCADO_PAGO_ACCESS_TOKEN=APP_USR-xxxxx-PRODUÇÃO
   MERCADO_PAGO_PUBLIC_KEY=APP_USR-xxxxx-PRODUÇÃO
   BASE_URL=https://seu-dominio.com
   ```

3. **Configure Webhook:**
   - Mercado Pago > Webhooks
   - URL: `https://seu-dominio.com/webhook/mercado_pago`
   - Eventos: `payment.created`, `payment.updated`

4. **Teste novamente:**
   - `python test_mercado_pago_setup.py`
   - Teste de pagamento completo

---

## 📞 Suporte Rápido

- **Docs Mercado Pago:** https://www.mercadopago.com.br/developers/pt-BR/docs
- **Status MP:** https://www.mercadopagostatus.com/
- **Detalhes Webhook:** Verifique `webhook_logs` no banco

---

**Última atualização:** 22 de Abril de 2026
**Status:** Production Ready ✓
