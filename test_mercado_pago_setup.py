"""
Script de teste para integração com Mercado Pago
Valida:
1. Conexão com banco de dados
2. Tabelas de pagamentos existem
3. Criar preferência no Mercado Pago
4. Logs de webhook
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Adicionar caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar de db.py
from db import get_connection

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_status(message, status='info'):
    """Imprime mensagem com cor"""
    colors = {
        'info': Colors.BLUE,
        'success': Colors.GREEN,
        'error': Colors.RED,
        'warning': Colors.YELLOW
    }
    color = colors.get(status, Colors.BLUE)
    print(f"{color}{'✓' if status == 'success' else '✗' if status == 'error' else '•'} {message}{Colors.END}")

def test_database_connection():
    """Testa conexão com banco de dados"""
    print("\n" + "="*60)
    print("TEST 1: Conexão com Banco de Dados")
    print("="*60)
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Testar query simples
        cur.execute("SELECT 1 as conexao")
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        print_status("Conexão com banco de dados OK", 'success')
        return True
        
    except Exception as e:
        print_status(f"Erro ao conectar com banco: {e}", 'error')
        return False

def test_mercado_pago_tables():
    """Verifica se tabelas de Mercado Pago existem"""
    print("\n" + "="*60)
    print("TEST 2: Tabelas de Mercado Pago")
    print("="*60)
    
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar tabelas
        tables_to_check = [
            'pagamentos_mercado_pago',
            'webhook_logs',
            'presentes'
        ]
        
        for table in tables_to_check:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table,))
            
            exists = cur.fetchone()[0]
            
            if exists:
                print_status(f"Tabela '{table}' existe", 'success')
            else:
                print_status(f"Tabela '{table}' NÃO foi encontrada", 'error')
                print("     Execute: migrations/add_mercado_pago_tables.sql")
        
        return True
        
    except Exception as e:
        print_status(f"Erro ao verificar tabelas: {e}", 'error')
        return False
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_presentes_data():
    """Verifica se há presentes no banco"""
    print("\n" + "="*60)
    print("TEST 3: Dados de Presentes")
    print("="*60)
    
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Contar presentes
        cur.execute("SELECT COUNT(*) as total FROM presentes")
        result = cur.fetchone()
        total_presentes = result['total']
        
        if total_presentes > 0:
            print_status(f"{total_presentes} presentes encontrados", 'success')
            
            # Mostrar detalhes
            cur.execute("""
                SELECT id, titulo, valor_sugerido, status 
                FROM presentes 
                LIMIT 5
            """)
            presentes = cur.fetchall()
            
            for p in presentes:
                print(f"     ID {p['id']}: {p['titulo']} - R$ {p['valor_sugerido']} - {p['status']}")
        else:
            print_status("Nenhum presente encontrado", 'warning')
            print("     Adicione presentes ao banco antes de testar")
        
        return total_presentes > 0
        
    except Exception as e:
        print_status(f"Erro ao consultar presentes: {e}", 'error')
        return False
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_mercado_pago_credentials():
    """Verifica credenciais do Mercado Pago"""
    print("\n" + "="*60)
    print("TEST 4: Credenciais Mercado Pago")
    print("="*60)
    
    token = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
    public_key = os.getenv("MERCADO_PAGO_PUBLIC_KEY")
    base_url = os.getenv("BASE_URL")
    
    if token:
        print_status("ACCESS_TOKEN configurado", 'success')
        print(f"     Token: {token[:20]}... (ocultado)")
    else:
        print_status("ACCESS_TOKEN não configurado", 'error')
    
    if public_key:
        print_status("PUBLIC_KEY configurado", 'success')
        print(f"     Key: {public_key[:20]}... (ocultado)")
    else:
        print_status("PUBLIC_KEY não configurado", 'error')
    
    if base_url:
        print_status("BASE_URL configurado", 'success')
        print(f"     URL: {base_url}")
    else:
        print_status("BASE_URL não configurado", 'warning')
        print("     Usando padrão: http://localhost:5000")
    
    return bool(token and public_key)

def test_webhook_logs_table():
    """Verifica tabela de logs de webhook"""
    print("\n" + "="*60)
    print("TEST 5: Logs de Webhook")
    print("="*60)
    
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Contar logs
        cur.execute("SELECT COUNT(*) as total FROM webhook_logs")
        result = cur.fetchone()
        total_logs = result['total']
        
        print_status(f"Total de logs: {total_logs}", 'success')
        
        if total_logs > 0:
            # Mostrar últimos logs
            cur.execute("""
                SELECT id, mercado_pago_id, status, created_at 
                FROM webhook_logs 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            logs = cur.fetchall()
            
            print("     Últimos logs:")
            for log in logs:
                print(f"       - ID {log['id']}: MP {log['mercado_pago_id']} - {log['status']}")
        
        return True
        
    except Exception as e:
        print_status(f"Erro ao consultar logs: {e}", 'error')
        return False
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def test_pagamentos_mercado_pago_table():
    """Verifica tabela de pagamentos"""
    print("\n" + "="*60)
    print("TEST 6: Pagamentos Mercado Pago")
    print("="*60)
    
    conn = None
    cur = None
    
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Contar pagamentos
        cur.execute("SELECT COUNT(*) as total FROM pagamentos_mercado_pago")
        result = cur.fetchone()
        total_pagamentos = result['total']
        
        print_status(f"Total de pagamentos: {total_pagamentos}", 'success')
        
        # Contar por status
        cur.execute("""
            SELECT status, COUNT(*) as total 
            FROM pagamentos_mercado_pago 
            GROUP BY status
        """)
        status_counts = cur.fetchall()
        
        if status_counts:
            print("     Pagamentos por status:")
            for row in status_counts:
                print(f"       - {row['status']}: {row['total']}")
        
        return True
        
    except Exception as e:
        print_status(f"Erro ao consultar pagamentos: {e}", 'error')
        return False
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def main():
    """Executa todos os testes"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║  🎁 TESTE DE INTEGRAÇÃO MERCADO PAGO - SISTEMA CASAMENTO  ║")
    print("╚" + "="*58 + "╝")
    
    results = {
        'database_connection': test_database_connection(),
        'mercado_pago_tables': test_mercado_pago_tables(),
        'presentes_data': test_presentes_data(),
        'mercado_pago_credentials': test_mercado_pago_credentials(),
        'webhook_logs': test_webhook_logs_table(),
        'pagamentos_mercado_pago': test_pagamentos_mercado_pago_table(),
    }
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = 'success' if result else 'error'
        test_display = test_name.replace('_', ' ').title()
        print_status(f"{test_display}: {'PASSOU' if result else 'FALHOU'}", status)
    
    print("\n" + "="*60)
    print(f"Resultado: {passed}/{total} testes passaram")
    print("="*60 + "\n")
    
    if passed == total:
        print_status("✓ SISTEMA PRONTO PARA USO!", 'success')
        print("\nPróximos passos:")
        print("1. Acesse http://localhost:5000")
        print("2. Navegue até 'Lista de Presentes'")
        print("3. Clique em 'Presentear' para testar o fluxo")
        print("4. Use cartão de teste: 4111 1111 1111 1111\n")
        return 0
    else:
        print_status("✗ RESOLVA OS ERROS ACIMA ANTES DE USAR EM PRODUÇÃO", 'error')
        print("\nDúvidas? Consulte MERCADO_PAGO_INTEGRATION.md\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
