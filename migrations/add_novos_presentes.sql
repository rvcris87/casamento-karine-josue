-- Migration: Adicionar novos presentes a lista
-- Data: 2026-04-25
-- Descricao: Insere presentes simbolicos mantendo os itens existentes

WITH novos_presentes (nome, slug, imagem, valor, status, destaque, ordem_relativa) AS (
    VALUES
        ('Eu sou ricaaa! Ajude o casal a realizar sonhos 😂', 'eu-sou-rica-ajude-o-casal', 'sou-rica.jpg', 1040.70, 'disponivel', false, 1),
        ('Ajude a pagar o condomínio 🏢😂', 'ajude-a-pagar-o-condominio', 'pagar-condominio.jpg', 320.34, 'disponivel', false, 2),
        ('Adote os boletos dos primeiros meses juntos 😂💸', 'adote-os-boletos', 'boletos.jpg', 892.29, 'disponivel', false, 3),
        ('Aluguel de carro para a lua de mel 🚗✨', 'aluguel-carro-lua-de-mel', 'carro-lua-mel.jpg', 1859.41, 'disponivel', false, 4),
        ('Patrocine a lua de mel dos noivos 💛✈️', 'patrocine-lua-de-mel', 'lua-de-mel.jpg', 12623.64, 'disponivel', false, 5),
        ('Vale passeio de balão 🎈✨', 'vale-passeio-de-balao', 'vale-balao.jpg', 473.28, 'disponivel', false, 6),
        ('Vale passeio de barco 🚤💙', 'vale-passeio-de-barco', 'vale-barco.jpg', 348.64, 'disponivel', false, 7),
        ('Vale sessão de massagem para o casal 💆‍♂️💆‍♀️', 'vale-sessao-de-massagem-casal', 'vale-massagem.jpg', 430.48, 'disponivel', false, 8)
),
ordem_atual AS (
    SELECT COALESCE(MAX(ordem), 0) AS ultima_ordem
    FROM presentes
)
INSERT INTO presentes (nome, slug, imagem, valor, status, destaque, ordem)
SELECT
    n.nome,
    n.slug,
    n.imagem,
    n.valor,
    n.status,
    n.destaque,
    o.ultima_ordem + n.ordem_relativa
FROM novos_presentes n
CROSS JOIN ordem_atual o
WHERE NOT EXISTS (
    SELECT 1
    FROM presentes p
    WHERE p.slug = n.slug
       OR p.nome = n.nome
);
