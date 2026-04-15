-- Script para criar as tabelas necessárias no Supabase
-- Execute este script no SQL Editor do Supabase

-- Tabela de configurações do site
CREATE TABLE IF NOT EXISTS site_config (
    id SERIAL PRIMARY KEY,
    nome_noiva VARCHAR(255) NOT NULL,
    nome_noivo VARCHAR(255) NOT NULL,
    data_casamento DATE,
    local_cerimonia VARCHAR(255),
    endereco_cerimonia TEXT,
    local_recepcao VARCHAR(255),
    endereco_recepcao TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de presentes
CREATE TABLE IF NOT EXISTS presentes (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT NOT NULL,
    valor_sugerido DECIMAL(10, 2) NOT NULL,
    imagem VARCHAR(500),
    pix_chave VARCHAR(255),
    pix_tipo VARCHAR(50),
    pix_copia_cola TEXT,
    ordem INTEGER,
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de mensagens (para RSVP)
CREATE TABLE IF NOT EXISTS mensagens (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    mensagem TEXT,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de fotos dos convidados
CREATE TABLE IF NOT EXISTS fotos_convidados (
    id SERIAL PRIMARY KEY,
    nome_convidado VARCHAR(255) NOT NULL,
    legenda TEXT,
    imagem_url VARCHAR(500) NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente', -- 'pendente', 'aprovado', 'rejeitado'
    destaque BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir configuração padrão do site (descomente para preencher)
/*
INSERT INTO site_config (nome_noiva, nome_noivo, data_casamento, local_cerimonia, endereco_cerimonia, local_recepcao, endereco_recepcao)
VALUES (
    'Karine Ribeiro',
    'Josué Alencar',
    '2026-10-10',
    'Hotel Fazenda Portal de Gravatá',
    'BR-232, s/n - Novo Gravatá, Gravatá - PE',
    'Hotel Fazenda Portal de Gravatá',
    'BR-232, s/n - Novo Gravatá, Gravatá - PE'
);
*/

-- Inserir presentes de exemplo (comentado - descomente se desejar)
/*
INSERT INTO presentes (titulo, descricao, valor_sugerido, imagem, pix_chave, pix_tipo, pix_copia_cola, ordem, ativo) VALUES
(
    'Ajude a pagar o primeiro boleto',
    'Casar é lindo... até o primeiro vencimento aparecer 😅',
    30.00,
    'https://images.unsplash.com/photo-1556740749-887f6717d7e4?auto=format&fit=crop&w=800&q=80',
    'karineejosue@email.com',
    'E-mail',
    '00020126580014BR.GOV.BCB.PIX0136karineejosue@email.com520400005303986540530.005802BR5925KARINE E JOSUE6009SAOPAULO62070503***6304ABCD',
    1,
    true
),
(
    'Patrocine nosso ansiolítico',
    'Organizar casamento e vida adulta ao mesmo tempo não é para os fracos 😂',
    20.00,
    'https://images.unsplash.com/photo-1584515933487-779824d29309?auto=format&fit=crop&w=800&q=80',
    '81999999999',
    'Telefone',
    '00020126580014BR.GOV.BCB.PIX011181999999999520400005303986540520.005802BR5925KARINE E JOSUE6009RECIFE62070503***6304EFGH',
    2,
    true
),
(
    'Assuma um boleto do casal',
    'Seja o herói que ajuda a manter a chama do amor e das contas acesas 💙',
    50.00,
    'https://images.unsplash.com/photo-1579621970795-87facc2f976d?auto=format&fit=crop&w=800&q=80',
    'karineejosue@email.com',
    'E-mail',
    '00020126580014BR.GOV.BCB.PIX0136karineejosue@email.com520400005303986540550.005802BR5925KARINE E JOSUE6009GRAVATA62070503***6304IJKL',
    3,
    true
),
(
    'Ajude na primeira compra do mercado',
    'Porque amor é tudo, mas a geladeira também precisa de atenção 🛒',
    100.00,
    'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=800&q=80',
    '81999999999',
    'Telefone',
    '00020126580014BR.GOV.BCB.PIX0111819999999995204000053039865406100.005802BR5925KARINE E JOSUE6009GRAVATA62070503***6304MNOP',
    4,
    true
);
*/
