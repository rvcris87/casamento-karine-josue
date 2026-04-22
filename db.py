import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    try:
        parsed = urlparse(DATABASE_URL)
        logger.info(f"DATABASE_URL carregada. Host: {parsed.hostname}, Porta: {parsed.port}")
    except Exception:
        logger.info("DATABASE_URL carregada (não foi possível parsear o host).")
else:
    logger.error("DATABASE_URL não encontrada! Configure a variável de ambiente no Render.")


def get_connection():
    """
    Estabelece conexão com o banco de dados PostgreSQL (Supabase pooler).

    IMPORTANTE: Use sempre a URL do POOLER do Supabase (não a conexão direta).
    Pooler session mode:  postgresql://postgres.xxx:senha@aws-x.pooler.supabase.com:5432/postgres
    Pooler transaction:   postgresql://postgres.xxx:senha@aws-x.pooler.supabase.com:6543/postgres

    Returns:
        psycopg2.connection: Conexão com o banco de dados

    Raises:
        Exception: Se houver erro na conexão
    """
    if not DATABASE_URL:
        raise Exception("DATABASE_URL não está configurada. Configure no painel do Render.")

    # Garante sslmode=require na URL sem conflito com kwargs
    db_url = DATABASE_URL
    if "sslmode=" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"

    try:
        connection = psycopg2.connect(db_url, connect_timeout=10)
        return connection
    except psycopg2.OperationalError as e:
        logger.exception(f"Falha de conexão com o banco. Verifique se DATABASE_URL usa o POOLER do Supabase (pooler.supabase.com), não a conexão direta (db.xxx.supabase.co). Erro: {e}")
        raise
    except psycopg2.Error as e:
        logger.exception(f"Erro psycopg2 ao conectar: {e}")
        raise




def sql_to_dict(cursor, query, params=None):
    """
    Executa uma query SQL e retorna os resultados como lista de dicionários.
    
    Args:
        cursor: Cursor RealDictCursor do psycopg2
        query: String com a query SQL
        params: Tupla com os parâmetros da query (opcional)
        
    Returns:
        list: Lista de dicionários com os resultados
    """
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        results = cursor.fetchall()
        return [dict(row) for row in results] if results else []
    except psycopg2.Error as e:
        raise Exception(f"Erro ao executar query: {str(e)}")


def get_presentes():
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, nome, slug, imagem, valor, status, destaque, ordem
            FROM presentes
            ORDER BY destaque DESC, ordem ASC, id ASC
        """)

        dados = cur.fetchall()

        presentes = []
        for p in dados:
            presentes.append({
                "id": p[0],
                "nome": p[1],
                "slug": p[2],
                "imagem": p[3],
                "valor": float(p[4]) if p[4] is not None else 0,
                "status": p[5],
                "destaque": p[6],
                "ordem": p[7],
            })

        return presentes

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def formatar_valor_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def insert_rsvp(nome, email, mensagem):
    """
    Insere um RSVP e mensagem no banco de dados.
    Preparado para futuras implementações.
    
    Args:
        nome: Nome do convidado
        email: Email do convidado
        mensagem: Mensagem de congratulações
        
    Returns:
        bool: True se inserido com sucesso, False caso contrário
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        query = """
            INSERT INTO mensagens (nome, email, mensagem, data_criacao)
            VALUES (%s, %s, %s, NOW())
        """
        
        cursor.execute(query, (nome, email, mensagem))
        connection.commit()
        
        return True
        
    except Exception as e:
        logger.exception(f"Erro ao inserir RSVP: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_site_config():
    """
    Busca as configurações do site (dados do casal, locais, datas).
    
    Returns:
        dict: Dicionário com as configurações do site ou None se não houver
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        query = """
            SELECT nome_noiva, nome_noivo, data_casamento,
                   local_cerimonia, endereco_cerimonia,
                   local_recepcao, endereco_recepcao
            FROM site_config
            LIMIT 1
        """
        
        cursor.execute(query)
        data = cursor.fetchone()

        if data:
            evento = {
                "nome_noiva": data[0],
                "nome_noivo": data[1],
                "data_casamento": data[2],
                "local_cerimonia": data[3],
                "endereco_cerimonia": data[4],
                "local_recepcao": data[5],
                "endereco_recepcao": data[6],
            }
            logger.info(f"✅ Evento carregado: {evento}")
            return evento

        logger.warning("⚠️  Nenhuma configuração de evento encontrada no banco")
        return None
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar configurações do evento: {str(e)}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def salvar_foto_convidado(nome_convidado, legenda, imagem_url):
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO fotos_convidados (nome_convidado, legenda, imagem_url, status)
            VALUES (%s, %s, %s, 'aprovado')
        """, (nome_convidado, legenda, imagem_url))

        conn.commit()

    except Exception as e:
        logger.exception(f"Erro ao salvar foto do convidado: {e}")
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_fotos_aprovadas():
    """
    Busca todas as fotos aprovadas dos convidados ordenadas por destaque e data.
    
    Returns:
        list: Lista de dicionários com as fotos aprovadas
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id, nome_convidado, legenda, imagem_url, destaque, created_at
            FROM fotos_convidados
            WHERE status = 'aprovado'
            ORDER BY destaque DESC, created_at DESC
        """
        
        cursor.execute(query)
        fotos = cursor.fetchall()
        
        return [dict(foto) for foto in fotos] if fotos else []
        
    except Exception as e:
        logger.exception(f"Erro ao buscar fotos aprovadas: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_fotos_pendentes():
    """
    Busca todas as fotos pendentes de aprovação (para admin).
    
    Returns:
        list: Lista de dicionários com as fotos pendentes
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT id, nome_convidado, legenda, imagem_url, created_at
            FROM fotos_convidados
            WHERE status = 'pendente'
            ORDER BY created_at ASC
        """
        
        cursor.execute(query)
        fotos = cursor.fetchall()
        
        return [dict(foto) for foto in fotos] if fotos else []
        
    except Exception as e:
        logger.exception(f"Erro ao buscar fotos pendentes: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def aprovar_foto(foto_id):
    """
    Aprova uma foto e muda seu status para 'aprovado'.
    
    Args:
        foto_id: ID da foto a aprovar
        
    Returns:
        bool: True se aprovado com sucesso, False caso contrário
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        query = """
            UPDATE fotos_convidados
            SET status = 'aprovado', updated_at = NOW()
            WHERE id = %s
        """
        
        cursor.execute(query, (foto_id,))
        connection.commit()
        
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.exception(f"Erro ao aprovar foto: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def rejeitar_foto(foto_id):
    """
    Rejeita uma foto e muda seu status para 'rejeitado'.
    
    Args:
        foto_id: ID da foto a rejeitar
        
    Returns:
        bool: True se rejeitado com sucesso, False caso contrário
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor()
        
        query = """
            UPDATE fotos_convidados
            SET status = 'rejeitado', updated_at = NOW()
            WHERE id = %s
        """
        
        cursor.execute(query, (foto_id,))
        connection.commit()
        
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.exception(f"Erro ao rejeitar foto: {e}")
        if connection:
            connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_todas_fotos():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nome_convidado, legenda, imagem_url, status, destaque, created_at
        FROM fotos_convidados
        ORDER BY created_at DESC
    """)

    dados = cur.fetchall()

    fotos = []
    for f in dados:
        fotos.append({
            "id": f[0],
            "nome_convidado": f[1],
            "legenda": f[2],
            "imagem_url": f[3],
            "status": f[4],
            "destaque": f[5],
            "created_at": f[6],
        })

    cur.close()
    conn.close()
    return fotos


def atualizar_status_foto(foto_id, novo_status):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE fotos_convidados
        SET status = %s
        WHERE id = %s
    """, (novo_status, foto_id))

    conn.commit()
    cur.close()
    conn.close()


def alternar_destaque_foto(foto_id, destaque):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE fotos_convidados
        SET destaque = %s
        WHERE id = %s
    """, (destaque, foto_id))

    conn.commit()
    cur.close()
    conn.close()


def excluir_foto(foto_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM fotos_convidados
        WHERE id = %s
    """, (foto_id,))

    conn.commit()
    cur.close()
    conn.close()


def salvar_rsvp(nome_convidado, telefone, acompanhantes, quantidade_criancas, confirmacao, observacao):
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO rsvp (
                nome_convidado,
                telefone,
                acompanhantes,
                quantidade_criancas,
                confirmacao,
                observacao
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            nome_convidado,
            telefone,
            acompanhantes,
            quantidade_criancas,
            confirmacao,
            observacao
        ))

        conn.commit()

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_todos_rsvp():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nome_convidado, telefone, acompanhantes, quantidade_criancas, confirmacao, observacao, created_at
        FROM rsvp
        ORDER BY created_at DESC
    """)

    dados = cur.fetchall()

    lista = []
    for r in dados:
        lista.append({
            "id": r[0],
            "nome_convidado": r[1],
            "telefone": r[2],
            "acompanhantes": r[3],
            "quantidade_criancas": r[4],
            "confirmacao": r[5],
            "observacao": r[6],
            "created_at": r[7],
        })

    cur.close()
    conn.close()
    return lista
