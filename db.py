import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

print("DATABASE_URL:", os.getenv("DATABASE_URL"))

def get_connection():
    """
    Estabelece conexão com o banco de dados PostgreSQL (Supabase).
    
    Returns:
        psycopg2.connection: Conexão com o banco de dados
        
    Raises:
        Exception: Se houver erro na conexão
    """
    if not DATABASE_URL:
        raise Exception("DATABASE_URL não está configurada no arquivo .env")
    
    try:
        connection = psycopg2.connect(
            DATABASE_URL,
            sslmode="require"
        )
        return connection
    except psycopg2.Error as e:
        raise Exception(f"Erro ao conectar ao banco de dados: {str(e)}")


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
    """
    Busca todos os presentes ativos ordenados por ordem.
    
    Returns:
        list: Lista de dicionários com os presentes
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                id,
                titulo,
                descricao,
                valor_sugerido,
                imagem,
                pix_chave,
                pix_tipo,
                pix_copia_cola,
                ordem
            FROM presentes
            WHERE ativo = true
            ORDER BY ordem ASC
        """
        
        presentes = sql_to_dict(cursor, query)
        
        # Renomear campos para nomes do template e formatar valores
        for presente in presentes:
            presente['imagem_url'] = presente.pop('imagem', None)
            presente['chave_pix'] = presente.pop('pix_chave', None)
            presente['tipo_chave_pix'] = presente.pop('pix_tipo', None)
            presente['copia_cola_pix'] = presente.pop('pix_copia_cola', None)
        
        return presentes
        
    except Exception as e:
        print(f"Erro ao buscar presentes: {str(e)}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


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
        print(f"Erro ao inserir RSVP: {str(e)}")
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
            config = {
                "nome_noiva": data[0],
                "nome_noivo": data[1],
                "data_casamento": data[2],
                "local_cerimonia": data[3],
                "endereco_cerimonia": data[4],
                "local_recepcao": data[5],
                "endereco_recepcao": data[6],
            }
            print(f"✅ Config carregada: {config}")
            return config

        print("⚠️  Nenhuma configuração encontrada no banco")
        return None
        
    except Exception as e:
        print(f"❌ Erro ao buscar configurações do site: {str(e)}")
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

        print("SALVANDO FOTO:", nome_convidado, legenda, imagem_url)

        cur.execute("""
            INSERT INTO fotos_convidados (nome_convidado, legenda, imagem_url, status)
            VALUES (%s, %s, %s, 'aprovado')
        """, (nome_convidado, legenda, imagem_url))

        conn.commit()
        print("FOTO SALVA COM SUCESSO")

    except Exception as e:
        print("ERRO REAL DO BANCO:", repr(e))
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
        print(f"❌ Erro ao buscar fotos aprovadas: {str(e)}")
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
        print(f"❌ Erro ao buscar fotos pendentes: {str(e)}")
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
        print(f"❌ Erro ao aprovar foto: {str(e)}")
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
        print(f"❌ Erro ao rejeitar foto: {str(e)}")
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


def salvar_rsvp(nome_convidado, telefone, acompanhantes, confirmacao, observacao):
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
                confirmacao,
                observacao
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            nome_convidado,
            telefone,
            acompanhantes,
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
        SELECT id, nome_convidado, telefone, acompanhantes, confirmacao, observacao, created_at
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
            "confirmacao": r[4],
            "observacao": r[5],
            "created_at": r[6],
        })

    cur.close()
    conn.close()
    return lista
