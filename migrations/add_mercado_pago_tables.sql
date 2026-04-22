-- Migration: Adicionar tabelas para integração com Mercado Pago
-- Data: 2026-04-22
-- Descrição: Cria tabelas para rastrear pagamentos via Mercado Pago

-- Tabela de pagamentos via Mercado Pago
CREATE TABLE IF NOT EXISTS pagamentos_mercado_pago (
    id SERIAL PRIMARY KEY,
    presente_id INTEGER NOT NULL REFERENCES presentes(id) ON DELETE CASCADE,
    mercado_pago_id BIGINT UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, approved, cancelled, refunded
    valor DECIMAL(10, 2) NOT NULL,
    nome_pagador VARCHAR(255),
    email_pagador VARCHAR(255),
    telefone_pagador VARCHAR(20),
    mensagem_pagador TEXT,
    metodo_pagamento VARCHAR(50), -- credit_card, debit_card, pix, etc
    preferencia_id VARCHAR(255) UNIQUE,
    init_point VARCHAR(500),
    payment_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela para rastrear notificações de webhook
CREATE TABLE IF NOT EXISTS webhook_logs (
    id SERIAL PRIMARY KEY,
    mercado_pago_id BIGINT,
    tipo_notificacao VARCHAR(50), -- payment, plan, subscription, etc
    status VARCHAR(50),
    dados_json JSONB,
    processado BOOLEAN DEFAULT false,
    erro VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_pagamentos_mp_presente_id ON pagamentos_mercado_pago(presente_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_mp_mercado_pago_id ON pagamentos_mercado_pago(mercado_pago_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_mp_status ON pagamentos_mercado_pago(status);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_mercado_pago_id ON webhook_logs(mercado_pago_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created_at ON webhook_logs(created_at DESC);

-- Adicionar coluna 'status' à tabela presentes se não existir
ALTER TABLE presentes 
ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'disponivel';

-- Criar função para atualizar a coluna updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Criar trigger para pagamentos_mercado_pago
DROP TRIGGER IF EXISTS update_pagamentos_mp_updated_at ON pagamentos_mercado_pago;
CREATE TRIGGER update_pagamentos_mp_updated_at BEFORE UPDATE ON pagamentos_mercado_pago
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Criar trigger para webhook_logs
DROP TRIGGER IF EXISTS update_webhook_logs_updated_at ON webhook_logs;
CREATE TRIGGER update_webhook_logs_updated_at BEFORE UPDATE ON webhook_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Permitir que apenas um pagamento aprovado exista por presente
CREATE UNIQUE INDEX IF NOT EXISTS idx_pagamentos_mp_presente_aprovado 
ON pagamentos_mercado_pago(presente_id) 
WHERE status = 'approved';
